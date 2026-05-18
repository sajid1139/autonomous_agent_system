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
from tools.parser import (scrape, scrape_with_section_data, extract, scrape_section_images, scrape_full_screenshot,
                         get_section_data, get_page_images, get_contact_info, get_section_with_description,
                         get_social_links, get_navigation, get_mobile_screenshot, get_all_sections,
                         get_table_data, scrape_js, get_section_images)
from utils.stream import notify

router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
url_re = re.compile(r"https?://[^\s]+")

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

async def get_page(url: str, wants_images: bool = False) -> dict:
    cached = await get_cached(url)
    if cached:
        print("cache hit:", url)
        imgs = []
        if wants_images:
            try:
                sections = await get_all_sections(url)
                imgs = [s["image"] for s in sections]
                print("playwright captured:", len(imgs), "images")
            except Exception as e:
                print("playwright error:", str(e))
        return {"content": cached.content, "images": imgs}
    
    content = ""
    try:
        content = await scrape(url)
        print("httpx content length:", len(content))
    except Exception as e:
        print("httpx error:", str(e))
    
    imgs = []
    if wants_images:
        try:
            sections = await get_all_sections(url)
            imgs = [s["image"] for s in sections]
            print("playwright captured:", len(imgs), "images")
        except Exception as e:
            print("playwright error:", str(e))
    
    if not content or len(content) < 200:
        print("httpx empty, trying scrape_js")
        try:
            res = await scrape_js(url)
            content = res.get("text", "")
            print("scrape_js content length:", len(content))
        except Exception as e:
            print("scrape_js error:", str(e))
    
    if not content or len(content) < 200:
        print("scrape_js empty, trying tavily")
        try:
            tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
            tv_res = await asyncio.to_thread(lambda: tv.search(query=url, max_results=5))
            content = "\n".join([r.get("content", "") for r in tv_res.get("results", [])])
            print("tavily content length:", len(content))
        except Exception as e:
            print("tavily error:", str(e))
            content = ""
    
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
    wants_images = any(w in body.text.lower() for w in ["image", "images", "screenshot", "photo", "picture"])
    section_keywords = ["services", "team", "about", "portfolio", "contact", "hero", "banner", "gallery"]
    specific_section = next((w for w in section_keywords if w in body.text.lower()), None)
    
    url = resolve_url(body.text)
    if url:
        raw_in_text = url_re.search(body.text)
        if raw_in_text:
            url = raw_in_text.group(0).strip()
            rest = body.text[raw_in_text.end():].strip()
        else:
            url = url.strip().rstrip("/") + "/"
            m = _bare.search(body.text)
            bare = m.group(1) if m else None
            rest = body.text.replace(bare, "").strip() if bare else ""
        print("extracted url:", url)
        print("extracted rest:", rest)
        
        filler_words = {"generate", "report", "of", "the", "a", "an", "for", "from", "on", "create", "make", "tell", "me", "image", "images", "screenshot", "photo", "picture", "give"}
        rest_words = [w for w in rest.lower().split() if w not in filler_words]
        if len(rest_words) < 3:
            rest = ""
        
        imgs = []
        descs = []
        if wants_images:
            try:
                if specific_section:
                    sections = await get_section_images(url, specific_section)
                else:
                    sections = await get_all_sections(url)
                imgs = [s["image"] for s in sections]
                descs = [s["description"] for s in sections]
                
                site = await ScrapedSite.get_or_none(url=url)
                if site:
                    site.images = json.dumps(imgs)
                    await site.save()
                
                print("MSG SAVED images count:", len(imgs))
                print("MSG IMAGES:", imgs)
            except Exception as e:
                print("images error:", str(e))
                import traceback
                traceback.print_exc()

        try:
            pg = await get_page(url, wants_images=False)
            page = pg["content"]
            if rest:
                prompt = (
                    f"From this webpage content, extract only the information related to: {rest}. "
                    f"Be specific and concise. Content: {page[:8000]} "
                    "Do not include any image tags, image placeholders, or markdown image syntax in your response."
                )
            else:
                prompt = (
                    "Generate a full structured report with Summary, Key Findings, "
                    f"and Recommendations based on this webpage content: {page[:8000]} "
                    "Do not include any image tags, image placeholders, or markdown image syntax in your response."
                )
            result = await call_llm(prompt)
        except Exception as e:
            print("400 error:", str(e))
            raise HTTPException(status_code=400, detail=str(e))
        
        goal = await make_report(url, result)
        msg = await Message.create(goal_id=goal.id, role="assistant", content=result, images=imgs, descriptions=descs)
        print("MSG SAVED - id:", msg.id, "images count:", len(msg.images or []))
        
        return {"goal_id": str(goal.id), "status": "done", "images": imgs, "descriptions": descs}

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
        url = body.url.strip()
        pg = await get_page(url, wants_images=False)
        prompt = (
            f"From this webpage content, answer the following query: {body.query}. "
            f"Be specific and concise. Content: {pg['content'][:8000]}"
        )
        result = await call_llm(prompt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    goal = await make_report(url, result)
    return {"goal_id": str(goal.id), "status": "done"}

@router.post("/analyze-url")
async def analyze_url(body: UrlIn):
    try:
        url = body.url.strip()
        pg = await get_page(url, wants_images=False)
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
        url = body.url.strip()
        result = await extract(url, body.query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"extract failed: {str(e)}")
    return {"data": result}

@router.post("/goals/{id}/chat")
async def chat_goal(id: str, body: dict = Body(...), bg: BackgroundTasks = None):
    query = body.get("query", "")
    ctx_url = body.get("ctx_url", None)
    if ctx_url:
        ctx_url = ctx_url.strip()
    goal = await Goal.get_or_none(id=id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    site_url = goal.text if goal.text.startswith('http') else 'none'
    print("site_url:", site_url)
    intent_prompt = f"""Site URL: {site_url}
User query: {query}
Respond in JSON only, no explanation:
{{"wants_images": true/false,"wants_description": true/false,"wants_report": true/false,"wants_table": true/false,"wants_contact": true/false,"wants_social": true/false,"wants_mobile": true/false,"wants_navigation": true/false,"specific_section": "exact section name mentioned or null","target_url": "full url if mentioned in query or null","answer_from_report": true/false}}

IMPORTANT: answer_from_report should ONLY be true if user is asking about the report text, never true for image requests"""

    try:
        intent_res = await call_llm(intent_prompt)
        if intent_res.startswith("```json"):
            intent_res = intent_res.replace("```json", "").replace("```", "").strip()
        intent = json.loads(intent_res)
        print("intent result:", intent)
    except Exception as e:
        print("intent analysis error:", str(e))
        intent = {"needs_scrape": False, "answer_from_report": True}

    if intent.get("answer_from_report"):
        report = await Report.get_or_none(goal_id=id)
        if report:
            history = await Message.filter(goal_id=id).order_by("created")
            hist_text = "\n".join([f"{m.role}: {m.content}" for m in history])
            prompt = (
                f"Based on this report:\n{report.content}\n\n"
                f"Conversation so far:\n{hist_text}\n\n"
                f"Answer this query: {query}"
                "Do not include any image tags, image placeholders, or markdown image syntax in your response."
            )
            answer = await call_llm(prompt)
            await Message.create(goal_id=goal.id, role="user", content=query, descriptions=[])
            await Message.create(goal_id=goal.id, role="assistant", content=answer, descriptions=[])
            return {"response": answer, "used_search": False, "goal_id": str(goal.id)}

    active_url = intent.get("target_url") or site_url
    print("active_url:", active_url)
    print("routing - wants_images:", intent.get("wants_images"))
    print("routing - specific_section:", intent.get("specific_section"))
    if active_url == 'none':
        bg.add_task(run, str(goal.id))
        await Message.create(goal_id=goal.id, role="user", content=query, descriptions=[])
        await Message.create(goal_id=goal.id, role="assistant", content="Researching... check back shortly.", descriptions=[])
        return {"response": "Researching... check back shortly.", "used_search": False, "goal_id": str(goal.id)}

    response_text = ""
    all_images = []
    all_descriptions = []
    contact_data = None
    social_data = None
    navigation_data = None

    try:
        specific_section = intent.get("specific_section")
        
        if specific_section:
            print(f"Getting specific section: {specific_section}")
            try:
                section_imgs = await get_section_images(active_url, specific_section)
                print("sections returned:", len(section_imgs), section_imgs)
                if section_imgs:
                    for img_data in section_imgs:
                        all_images.append(img_data["image"])
                        all_descriptions.append(img_data["description"])
                    response_text = f"Found {len(section_imgs)} images in '{specific_section}' section"
                    site = await ScrapedSite.get_or_none(url=active_url)
                    if site:
                        site.images = json.dumps(all_images)
                        await site.save()
                    else:
                        domain = urlparse(active_url).netloc
                        await ScrapedSite.create(url=active_url, domain=domain, content="", images=json.dumps(all_images))
                else:
                    response_text = f"No images found in '{specific_section}' section"
            except Exception as e:
                print(f"Error getting specific section: {str(e)}")
                import traceback
                traceback.print_exc()
                response_text = f"Error retrieving section '{specific_section}': {str(e)}"
        
        elif intent.get("wants_images"):
            print("Getting key sections from page")
            try:
                sections = await get_all_sections(active_url)
                print("sections returned:", len(sections), sections)
                if sections:
                    for section in sections[:4]:
                        all_images.append(section["image"])
                        all_descriptions.append(section["description"])
                    response_text = f"Found {len(sections[:4])} images from the page"
                    site = await ScrapedSite.get_or_none(url=active_url)
                    if site:
                        site.images = json.dumps(all_images)
                        await site.save()
                    else:
                        domain = urlparse(active_url).netloc
                        await ScrapedSite.create(url=active_url, domain=domain, content="", images=json.dumps(all_images))
                else:
                    response_text = "No images found on the page"
            except Exception as e:
                print(f"Error getting key sections: {str(e)}")
                import traceback
                traceback.print_exc()
                response_text = f"Error retrieving page sections: {str(e)}"
        
        if intent.get("wants_contact"):
            try:
                contact_data = await get_contact_info(active_url)
                if not response_text:
                    response_text = "Contact information retrieved"
            except Exception as e:
                print(f"Error getting contact info: {str(e)}")
        
        if intent.get("wants_social"):
            try:
                social_data = await get_social_links(active_url)
                if not response_text:
                    response_text = "Social media links retrieved"
            except Exception as e:
                print(f"Error getting social links: {str(e)}")
        
        if intent.get("wants_navigation"):
            try:
                navigation_data = await get_navigation(active_url)
                if not response_text:
                    response_text = "Navigation menu retrieved"
            except Exception as e:
                print(f"Error getting navigation: {str(e)}")
        
        if intent.get("wants_mobile"):
            try:
                mobile_screenshot = await get_mobile_screenshot(active_url)
                if mobile_screenshot:
                    all_images.append(mobile_screenshot)
                    all_descriptions.append("Mobile view screenshot")
                    if not response_text:
                        response_text = "Mobile view captured"
            except Exception as e:
                print(f"Error getting mobile screenshot: {str(e)}")
        
        if intent.get("wants_table"):
            try:
                table_result = await get_table_data(active_url, specific_section)
                if table_result["image"]:
                    all_images.append(table_result["image"])
                    all_descriptions.append("Table data")
                if table_result["data"] and not response_text:
                    response_text = table_result["data"][:500]
            except Exception as e:
                print(f"Error getting table data: {str(e)}")
        
        if intent.get("wants_report") and not specific_section:
            try:
                scrape_result = await scrape_with_section_data(active_url)
                content = scrape_result.get("text", "")
                if content:
                    prompt = (
                        f"Generate a structured report based on this content: {content[:8000]} "
                        "Do not include any image tags, image placeholders, or markdown image syntax in your response."
                    )
                    response_text = await call_llm(prompt)
            except Exception as e:
                print(f"Error generating report: {str(e)}")
        
        if not response_text:
            response_text = "Information retrieved successfully"
        
        print("saving to message - images:", all_images, "desc:", all_descriptions)
        await Message.create(goal_id=goal.id, role="user", content=query, descriptions=[])
        await Message.create(goal_id=goal.id, role="assistant", content=response_text, images=all_images, descriptions=all_descriptions)
        
        result = {
            "response": response_text,
            "images": all_images,
            "descriptions": all_descriptions,
            "used_search": False,
            "goal_id": str(goal.id)
        }
        
        if contact_data:
            result["contact"] = contact_data
        if social_data:
            result["social"] = social_data
        if navigation_data:
            result["navigation"] = navigation_data
        
        print("returning result:", result)
        return result
        
    except Exception as e:
        print("scraping error:", str(e))
        import traceback
        traceback.print_exc()
        error_msg = f"Error occurred: {str(e)}"
        await Message.create(goal_id=goal.id, role="user", content=query, descriptions=[])
        await Message.create(goal_id=goal.id, role="assistant", content=error_msg, descriptions=[])
        return {
            "response": error_msg,
            "images": [],
            "descriptions": [],
            "used_search": False,
            "goal_id": str(goal.id)
        }

@router.get("/goals/{id}/messages")
async def get_messages(id: str):
    msgs = await Message.filter(goal_id=id).order_by("created")
    for m in msgs:
        print("MSG ID:", m.id, "role:", m.role, "images:", m.images)
    return [{"id": str(m.id), "role": m.role, "content": m.content, "images": m.images or [], "descriptions": m.descriptions or [], "created": str(m.created)} for m in msgs]

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