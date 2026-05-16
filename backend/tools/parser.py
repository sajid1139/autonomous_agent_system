import os
import asyncio
import time
import httpx
from urllib.parse import urljoin, urlparse
from pypdf import PdfReader
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        os.makedirs("static/screenshots", exist_ok=True)
        domain = urlparse(url).netloc.replace(".", "_")
        ts = int(time.time())

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(800)

            ss_path = f"static/screenshots/{domain}_{ts}.png"
            pg.screenshot(path=ss_path, full_page=True)
            print("page screenshot saved:", ss_path)

            img_paths = []
            img_els = pg.query_selector_all("img")
            for i, el in enumerate(img_els):
                if len(img_paths) >= 10:
                    break
                try:
                    box = el.bounding_box()
                    if not box or box["width"] <= 50 or box["height"] <= 50:
                        continue
                    p_out = f"static/screenshots/{domain}_img_{i}_{ts}.png"
                    el.screenshot(path=p_out)
                    img_paths.append(p_out)
                except Exception:
                    pass
            print("element screenshots captured:", len(img_paths))

            seen = set()
            chunks = []
            for line in extract_text(pg.inner_html("body")).splitlines():
                l = line.strip()
                if l and l not in seen:
                    seen.add(l)
                    chunks.append(l)

            browser.close()

        result = "\n".join(chunks)
        print("scrape_js content length:", len(result))
        return {"text": result, "screenshot": ss_path, "images": img_paths}
    except Exception as e:
        print("scrape_js error:", str(e))
        return {"text": "", "screenshot": "", "images": []}

def _sync_scrape_section(url, section):
    print("scrape_section started:", section)
    try:
        from playwright.sync_api import sync_playwright
        os.makedirs("static/screenshots", exist_ok=True)
        domain = urlparse(url).netloc.replace(".", "_")
        ts = int(time.time())

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(800)

            kw = section.lower()
            candidates = [
                f"section:has-text('{section}')",
                f"div:has-text('{section}')",
                f"[class*='{kw}']",
                f"[id*='{kw}']",
                f"#{kw}",
                f".{kw}",
            ]
            container = None
            for sel in candidates:
                try:
                    el = pg.query_selector(sel)
                    if el and el.is_visible():
                        container = el
                        break
                except Exception:
                    pass

            img_paths = []
            if container:
                img_els = container.query_selector_all("img")
                for i, el in enumerate(img_els):
                    if len(img_paths) >= 10:
                        break
                    try:
                        box = el.bounding_box()
                        if not box or box["width"] <= 50 or box["height"] <= 50:
                            continue
                        p_out = f"static/screenshots/{domain}_img_{i}_{ts}.png"
                        el.screenshot(path=p_out)
                        img_paths.append(p_out)
                    except Exception:
                        pass
            else:
                print("section not found, falling back to full page images")
                img_els = pg.query_selector_all("img")
                for i, el in enumerate(img_els):
                    if len(img_paths) >= 10:
                        break
                    try:
                        box = el.bounding_box()
                        if not box or box["width"] <= 50 or box["height"] <= 50:
                            continue
                        p_out = f"static/screenshots/{domain}_img_{i}_{ts}.png"
                        el.screenshot(path=p_out)
                        img_paths.append(p_out)
                    except Exception:
                        pass

            browser.close()

        print("section images captured:", len(img_paths))
        return {"images": img_paths}
    except Exception as e:
        print("scrape_section error:", str(e))
        return {"images": []}


async def scrape_section_images(url: str, section: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_scrape_section, url, section)


def _sync_scrape_page_images(url):
    print("scrape_page_images started")
    try:
        from playwright.sync_api import sync_playwright
        os.makedirs("static/screenshots", exist_ok=True)
        domain = urlparse(url).netloc.replace(".", "_")
        ts = int(time.time())

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(800)

            ss_path = f"static/screenshots/{domain}_{ts}.png"
            pg.screenshot(path=ss_path, full_page=True)
            print("full page screenshot:", ss_path)

            browser.close()

        return {"screenshot": ss_path}
    except Exception as e:
        print("scrape_page_images error:", str(e))
        return {"screenshot": ""}


async def scrape_full_screenshot(url: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_scrape_page_images, url)


async def scrape_js(url: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_scrape, url)


async def extract(url: str, query: str) -> str:
    text = await scrape(url)
    prompt = (
        f"From this webpage content, extract only the information related to: {query}. "
        f"Be specific and concise. Content: {text[:8000]}"
    )
    res = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
    )
    return res.choices[0].message.content.strip()
