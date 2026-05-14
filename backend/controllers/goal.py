import os
import re
from urllib.parse import urlparse
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from google import genai
from models.goal import Goal
from models.report import Report
from models.scraped import ScrapedSite
from orchestrator.engine import run
from security.rate_limiter import limiter
from security.execution_guard import check
from tools.parser import scrape, scrape_js, extract
from utils.stream import notify

router = APIRouter()

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

async def get_page(url: str) -> str:
    cached = await ScrapedSite.get_or_none(url=url)
    if cached:
        return cached.content
    content = await scrape(url)
    print("httpx content length:", len(content))
    if len(content) < 200:
        print("using scrape_js")
        content = await scrape_js(url)
    domain = urlparse(url).netloc
    await ScrapedSite.create(url=url, domain=domain, content=content)
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
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
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
            res = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            result = res.text.strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        goal = await make_report(url, result)
        return {"goal_id": str(goal.id), "status": "done"}

    try:
        await check(body.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    goal = await Goal.create(text=body.text)
    bg.add_task(run, str(goal.id))
    return {"goal_id": str(goal.id), "status": goal.status}

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
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"From this webpage content, answer the following query: {body.query}. "
                f"Be specific and concise. Content: {page[:8000]}"
            ),
        )
        result = res.text.strip()
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
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = (
        "Generate a full structured report with Summary, Key Findings, and Recommendations "
        f"based on this webpage content: {text[:8000]}"
    )
    res = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return {"report": res.text.strip()}

@router.post("/extract-url")
async def extract_url(body: ExtractIn):
    try:
        result = await extract(body.url, body.query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"extract failed: {str(e)}")
    return {"data": result}
