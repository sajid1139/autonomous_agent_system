import os
import asyncio
import httpx
from pypdf import PdfReader
from bs4 import BeautifulSoup
from google import genai

async def run(path: str) -> str:
    ext = os.path.splitext(path)[-1].lower()
    if ext == ".pdf":
        reader = PdfReader(path)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

async def scrape(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as c:
        res = await c.get(url)
        res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "head"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)

def _sync_scrape(url):
    print("scrape_js started")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            chunks = []
            seen = set()

            def add(t):
                for line in t.splitlines():
                    l = line.strip()
                    if l and l not in seen:
                        seen.add(l)
                        chunks.append(l)

            add(extract_text(page.inner_html("body")))
            els = page.query_selector_all(
                "button, [role='button'], [onclick], [class*='gear'], "
                "[class*='settings'], [class*='custom'], [class*='toggle'], "
                "[class*='icon'], svg, [class*='btn']"
            )[:30]
            for el in els:
                try:
                    if el.is_visible():
                        el.click(timeout=3000)
                        page.wait_for_timeout(1500)
                        page.evaluate("window.scrollBy(0, 300)")
                        add(extract_text(page.inner_html("body")))
                except Exception:
                    pass
            browser.close()
        result = "\n".join(chunks)
        print("scrape_js content length:", len(result))
        print("scrape_js preview:", "\n".join(chunks[:20]))
        return result
    except Exception as e:
        print("scrape_js error:", str(e))
        return ""

async def scrape_js(url: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_scrape, url)

async def extract(url: str, query: str) -> str:
    text = await scrape(url)
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = (
        f"From this webpage content, extract only the information related to: {query}. "
        f"Be specific and concise. Content: {text[:8000]}"
    )
    res = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return res.text.strip()
