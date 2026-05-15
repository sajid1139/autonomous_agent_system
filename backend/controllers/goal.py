import os
import re
import json
import asyncio
from urllib.parse import urlparse
from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Request
from pydantic import BaseModel
from openai import OpenAI
from models.goal import Goal
from models.report import Report
from models.message import Message
from models.scraped import ScrapedSite
from orchestrator.engine import run
from security.rate_limiter import limiter
from security.execution_guard import check
from tavily import TavilyClient
from tools.parser import scrape, scrape_js, extract
from utils.stream import notify

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
url_re = re.compile(r"https?://\S+")

class GoalIn(BaseModel):
    text: str

class UrlIn(BaseModel):
    url: str

class ExtractIn(BaseModel):
    url: str
    query: str

class QueryCtxIn(BaseModel):
    url: str
    query: str

async def call_llm(prompt: str) -> str:
    res = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
    )
    return res.choices[0].message.content.strip()

async def get_page(url: str) -> str:
    cached = await ScrapedSite.get_or_none(url=url)
    if cached:
        return cached.content
    content = await scrape(url)
    print("httpx content length:", len(content))
    if len(content) < 200:
        print("using scrape_js")
        res = await scrape_js(url)
        imgs = res.get("images", []) if isinstance(res, dict) else []
        content = res["text"] if isinstance(res, dict) else res
    else:
        imgs = []
    if not content or len(content) < 200:
        print("scrape_js empty, falling back to tavily")
        try:
            tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
            tv_res = await asyncio.to_thread(lambda: tv.search(query=url, max_results=5))
            content = "\n".join([r.get("content", "") for r in tv_res.get("results", [])])
            print("tavily fallback content length:", len(content))
        except Exception as e:
            print("tavily fallback error:", str(e))
            content = ""
        imgs = []
    domain = urlparse(url).netloc
    await ScrapedSite.create(url=url, domain=domain, content=content, images=json.dumps(imgs))
    return content

async def make_report(url: str, result: str):
    goal = await Goal.create(text=url, status="done")
    await Report.create(goal=goal, content=result)
    await notify(str(goal.id), "workflow complete")
    return goal

@router.post("/goals")
@limiter.limit("200/minute")
async def create_goal(request: Request, body: GoalIn, bg: BackgroundTasks):
    match = url_re.search(body.text)
    if match:
        url = match.group(0)
        rest = body.text.replace(url, "").strip()
        try:
            page = await get_page(url)
            if rest:
                prompt = (
                    f"From this webpage content, extract only the information related to: {rest}. "
                    f"Be specific and concise. Content: {page[:8000]}"
                )
            else:
                prompt = (
                    "Generate a full structured report with Summary, Key Findings, "
                    f"and Recommendations based on this webpage content: {page[:8000]}"
                )
            result = await call_llm(prompt)
        except Exception as e:
            print("400 error:", str(e))
            raise HTTPException(status_code=400, detail=str(e))
        goal = await make_report(url, result)
        return {"goal_id": str(goal.id), "status": "done"}

    print("guard check for:", body.text)
    try:
        await check(body.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    goal = await Goal.create(text=body.text)
    bg.add_task(run, str(goal.id))
    return {"goal_id": str(goal.id), "status": goal.status}

@router.get("/goals")
async def list_goals():
    goals = await Goal.all().order_by("-created").limit(50)
    return [{"id": str(g.id), "text": g.text, "status": g.status, "created": str(g.created)} for g in goals]

@router.get("/goals/{id}")
async def get_goal(id: str):
    goal = await Goal.get_or_none(id=id)
    if not goal:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": str(goal.id), "text": goal.text, "status": goal.status, "created": goal.created}

@router.post("/query-context")
async def query_context(body: QueryCtxIn):
    try:
        page = await get_page(body.url)
        prompt = (
            f"From this webpage content, answer the following query: {body.query}. "
            f"Be specific and concise. Content: {page[:8000]}"
        )
        result = await call_llm(prompt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    goal = await make_report(body.url, result)
    return {"goal_id": str(goal.id), "status": "done"}

@router.post("/analyze-url")
async def analyze_url(body: UrlIn):
    try:
        text = await get_page(body.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"scrape failed: {str(e)}")
    prompt = (
        "Generate a full structured report with Summary, Key Findings, and Recommendations "
        f"based on this webpage content: {text[:8000]}"
    )
    result = await call_llm(prompt)
    return {"report": result}

@router.post("/extract-url")
async def extract_url(body: ExtractIn):
    try:
        result = await extract(body.url, body.query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"extract failed: {str(e)}")
    return {"data": result}

@router.post("/goals/{id}/chat")
async def chat_goal(id: str, body: dict = Body(...)):
    query = body.get("query", "")
    goal = await Goal.get_or_none(id=id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    report = await Report.get_or_none(goal_id=id)
    history = await Message.all().filter(goal_id=id).order_by("created")
    hist_text = "\n".join([f"{m.role}: {m.content}" for m in history])

    if report:
        prompt = (
            f"Based on this report:\n{report.content}\n\n"
            f"Conversation so far:\n{hist_text}\n\n"
            f"Can you answer this query: {query}\n"
            "If the answer is clearly in the report, answer from it and start response with [FROM_REPORT].\n"
            "If not found, respond with exactly: [NEEDS_SEARCH]"
        )
        raw = await call_llm(prompt)

        if raw.startswith("[FROM_REPORT]"):
            answer = raw.replace("[FROM_REPORT]", "", 1).strip()
            await Message.create(goal_id=id, role="user", content=query)
            await Message.create(goal_id=id, role="assistant", content=answer)
            return {"response": answer, "used_search": False}

    new_goal = await Goal.create(text=query)
    await run(str(new_goal.id))
    new_report = await Report.get_or_none(goal_id=str(new_goal.id))
    answer = new_report.content if new_report else "Agent pipeline completed but no report was generated."

    await Message.create(goal_id=id, role="user", content=query)
    await Message.create(goal_id=id, role="assistant", content=answer)
    return {"response": answer, "used_search": True, "goal_id": str(goal.id)}

@router.get("/goals/{id}/messages")
async def get_messages(id: str):
    msgs = await Message.all().filter(goal_id=id).order_by("created")
    return [{"id": str(m.id), "role": m.role, "content": m.content, "created": str(m.created)} for m in msgs]

@router.get("/goals/{id}/images")
async def get_images(id: str):
    goal = await Goal.get_or_none(id=id)
    if not goal:
        raise HTTPException(status_code=404, detail="not found")
    site = await ScrapedSite.get_or_none(url=goal.text)
    if not site:
        return {"images": []}
    try:
        imgs = json.loads(site.images)
    except Exception:
        imgs = []
    return {"images": imgs}
