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
from tools.parser import scrape, scrape_js, extract, scrape_section_images, scrape_full_screenshot
from utils.stream import notify

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
url_re = re.compile(r"https?://\S+")

tlds = {
    "com","org","net","io","co","pk","uk","edu","gov","ai","dev","app","tech",
    "info","biz","us","ca","au","in","de","fr","jp","cn","ru","br","mx","es",
    "it","nl","se","no","fi","dk","pl","pt","ro","hu","cz","sk","bg","hr","si",
    "ee","lv","lt","ua","by","kz","uz","ge","am","az","ng","za","ke","gh","et",
    "tz","eg","ma","dz","tn","ly","sd","so","ye","iq","sy","lb","jo","ps","ae",
    "sa","kw","qa","bh","om","ir","af","bd","lk","np","mm","th","vn","ph","id",
    "my","sg","hk","tw","kr","nz","ar","cl","pe","ve","ec","bo","py","uy",
}

_bare = re.compile(
    r"(?:^|\s)((?:[\w-]+\.)+(" + "|".join(re.escape(t) for t in tlds) + r")(?:/\S*)?)",
    re.IGNORECASE,
)

def resolve_url(txt: str) -> str | None:
    t = txt.strip()
    if url_re.match(t):
        return t
    m = url_re.search(t)
    if m:
        return m.group(0)
    m = _bare.search(t)
    if m:
        return "https://" + m.group(1)
    return None

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
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
    )
    return res.choices[0].message.content.strip()

async def get_cached(url: str) -> ScrapedSite | None:
    return await ScrapedSite.filter(url=url).first()

async def get_page(url: str) -> dict:
    cached = await get_cached(url)
    if cached:
        print("cache hit:", url)
        try:
            imgs = json.loads(cached.images or "[]")
        except Exception:
            imgs = []
        return {"content": cached.content, "images": imgs}
    content = await scrape(url)
    print("httpx content length:", len(content))
    if len(content) < 200:
        print("using scrape_js")
        res = await scrape_js(url)
        ss = res.get("screenshot", "") if isinstance(res, dict) else ""
        el_imgs = res.get("images", []) if isinstance(res, dict) else []
        imgs = []
        if ss:
            imgs.append(f"/static/screenshots/{os.path.basename(ss)}")
        for p in el_imgs:
            imgs.append(f"/static/screenshots/{os.path.basename(p)}")
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
    return {"content": content, "images": imgs}

async def make_report(url: str, result: str):
    goal = await Goal.create(text=url, status="done")
    await Report.create(goal=goal, content=result)
    await notify(str(goal.id), "workflow complete")
    return goal

@router.post("/goals")
@limiter.limit("200/minute")
async def create_goal(request: Request, body: GoalIn, bg: BackgroundTasks):
    url = resolve_url(body.text)
    if url:
        raw_in_text = url_re.search(body.text)
        if raw_in_text:
            rest = body.text.replace(raw_in_text.group(0), "").strip()
        else:
            m = _bare.search(body.text)
            bare = m.group(1) if m else None
            rest = body.text.replace(bare, "").strip() if bare else ""
        try:
            pg = await get_page(url)
            page = pg["content"]
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
    site = await ScrapedSite.get_or_none(url=goal.text)
    url = site.url if site else None
    return {"id": str(goal.id), "text": goal.text, "status": goal.status, "created": goal.created, "url": url}

@router.post("/query-context")
async def query_context(body: QueryCtxIn):
    try:
        pg = await get_page(body.url)
        prompt = (
            f"From this webpage content, answer the following query: {body.query}. "
            f"Be specific and concise. Content: {pg['content'][:8000]}"
        )
        result = await call_llm(prompt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    goal = await make_report(body.url, result)
    return {"goal_id": str(goal.id), "status": "done"}

@router.post("/analyze-url")
async def analyze_url(body: UrlIn):
    try:
        pg = await get_page(body.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"scrape failed: {str(e)}")
    prompt = (
        "Generate a full structured report with Summary, Key Findings, and Recommendations "
        f"based on this webpage content: {pg['content'][:8000]}"
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
async def chat_goal(id: str, body: dict = Body(...), bg: BackgroundTasks = None):
    query = body.get("query", "")
    ctx_url = body.get("ctx_url", None)
    goal = await Goal.get_or_none(id=id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    url_in_query = resolve_url(query)
    target_url = url_in_query or ctx_url

    if target_url:
        cached = await get_cached(target_url)
        if cached:
            print("chat cache hit:", target_url)
            try:
                pg_imgs = json.loads(cached.images or "[]")
            except Exception:
                pg_imgs = []
            pg_content = cached.content
        else:
            print("chat scraping fresh:", target_url)
            pg = await get_page(target_url)
            pg_content = pg["content"]
            pg_imgs = pg["images"]
        rest = query.replace(url_in_query, "").strip() if url_in_query else query
        if rest:
            prompt = (
                f"From this webpage content, extract only the information related to: {rest}. "
                f"Be specific and concise. Content: {pg_content[:8000]}"
            )
        else:
            prompt = (
                "Generate a full structured report with Summary, Key Findings, "
                f"and Recommendations based on this webpage content: {pg_content[:8000]}"
            )
        img_kw = {"image","images","screenshot","visual","show","capture","dikhao","picture"}
        want_imgs = any(w in query.lower() for w in img_kw)

        section_kw = ["hero","header","banner","footer","about","features","pricing","gallery","team","contact","services","testimonial","portfolio"]
        section = next((w for w in section_kw if w in query.lower()), None)

        if want_imgs and section:
            sec_prompt = (
                f"Extract only the {section} section content from this page. "
                f"Be concise and specific. Content: {pg_content[:8000]}"
            )
            sec_res, sec_text = await asyncio.gather(
                scrape_section_images(target_url, section),
                call_llm(sec_prompt),
            )
            fresh_imgs = [f"/static/screenshots/{os.path.basename(p)}" for p in sec_res.get("images", [])]
            await Message.create(goal_id=goal.id, role="user", content=query)
            await Message.create(goal_id=goal.id, role="assistant", content=sec_text)
            return {"response": sec_text, "used_search": False, "images": fresh_imgs, "images_first": True}

        if want_imgs and not section:
            ss_res = await scrape_full_screenshot(target_url)
            ss = ss_res.get("screenshot", "")
            fresh_imgs = [f"/static/screenshots/{os.path.basename(ss)}"] if ss else []
            answer = await call_llm(prompt)
            await Message.create(goal_id=goal.id, role="user", content=query)
            await Message.create(goal_id=goal.id, role="assistant", content=answer)
            return {"response": answer, "used_search": False, "images": fresh_imgs}

        answer = await call_llm(prompt)
        await Message.create(goal_id=goal.id, role="user", content=query)
        await Message.create(goal_id=goal.id, role="assistant", content=answer)
        return {"response": answer, "used_search": False, "images": pg_imgs}

    report = await Report.get_or_none(goal_id=id)
    history = await Message.filter(goal_id=id).order_by("created")
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
            await Message.create(goal_id=goal.id, role="user", content=query)
            await Message.create(goal_id=goal.id, role="assistant", content=answer)
            return {"response": answer, "used_search": False}

    new_goal = await Goal.create(text=query)
    bg.add_task(run, str(new_goal.id))
    await Message.create(goal_id=goal.id, role="user", content=query)
    await Message.create(goal_id=goal.id, role="assistant", content="Researching... check back shortly.")
    return {"response": "Researching... check back shortly.", "used_search": True, "goal_id": str(new_goal.id)}

@router.get("/goals/{id}/messages")
async def get_messages(id: str):
    msgs = await Message.filter(goal_id=id).order_by("created")
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
