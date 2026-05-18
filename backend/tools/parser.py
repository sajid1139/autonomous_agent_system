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
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as c:
            res = await c.get(url)
            res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "head"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return "\n".join(lines)
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        if hasattr(e, 'response') and e.response.status_code == 403:
            print("httpx got 403, falling back to playwright")
        else:
            print(f"httpx failed: {str(e)}, falling back to playwright")
        result = await scrape_js(url)
        return result.get("text", "") if isinstance(result, dict) else str(result)

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _sync_scrape_with_section_data(url, section=None, wants_images=True, wants_description=False):
    print("scrape_with_section_data started")
    try:
        from playwright.sync_api import sync_playwright
        os.makedirs("static/screenshots", exist_ok=True)
        domain = urlparse(url).netloc.replace(".", "_")
        ts = int(time.time())

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(3000)

            seen = set()
            chunks = []
            for line in extract_text(pg.inner_html("body")).splitlines():
                l = line.strip()
                if l and l not in seen:
                    seen.add(l)
                    chunks.append(l)

            result = "\n".join(chunks)
            print("scrape_with_section_data content length:", len(result))
            
            section_data = {}
            if section:
                section_data = _sync_get_section_data_with_page(pg, url, section, wants_images, wants_description)
            elif wants_images:
                images = []
                img_descriptions = []
                try:
                    body = pg.query_selector("body")
                    if body:
                        header_nav_footer = pg.query_selector_all("header, nav, footer")
                        excluded_imgs = set()
                        for element in header_nav_footer:
                            for img in element.query_selector_all("img"):
                                excluded_imgs.add(img)
                        
                        imgs = body.query_selector_all("img")
                        print("imgs found:", len(imgs))
                        
                        for n, img in enumerate(imgs):
                            if img in excluded_imgs:
                                continue
                            try:
                                box = img.bounding_box()
                                print("img box:", box)
                                if not box or box["width"] <= 100 or box["height"] <= 100:
                                    continue
                                img.scroll_into_view_if_needed()
                                pg.wait_for_timeout(800)
                                ts = int(time.time() * 1000)
                                p = f"static/screenshots/{ts}_img_{n}.png"
                                pg.screenshot(path=p, clip={"x": max(0, box["x"]), "y": max(0, box["y"]), "width": box["width"], "height": box["height"]})
                                alt = img.get_attribute("alt") or f"Image {n+1}"
                                images.append("/" + p)
                                img_descriptions.append(alt)
                            except Exception as e:
                                print(f"img {n} error:", e)
                                continue
                except Exception as e:
                    print("img capture error:", e)
                section_data = {"images": images, "description": "", "img_descriptions": img_descriptions}

            browser.close()

        return {"text": result, **section_data}
    except Exception as e:
        print("scrape_with_section_data error:", str(e))
        return {"text": "", "images": [], "description": "", "img_descriptions": []}


def _sync_scrape(url):
    print("scrape_js started")
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(3000)
            pg.wait_for_timeout(5000)

            seen = set()
            chunks = []
            for line in extract_text(pg.inner_html("body")).splitlines():
                l = line.strip()
                if l and l not in seen:
                    seen.add(l)
                    chunks.append(l)

            result = "\n".join(chunks)
            print("scrape_js content length:", len(result))

            browser.close()

        return {"text": result}
    except Exception as e:
        print("scrape_js error:", str(e))
        import traceback
        traceback.print_exc()
        return {"text": ""}

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
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
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
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
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


async def scrape_with_section_data(url: str, section: str = None, wants_images: bool = True, wants_description: bool = False) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_scrape_with_section_data, url, section, wants_images, wants_description)


async def section_screenshot_async(url, section_keyword):
    print("section_screenshot_async started:", section_keyword)
    try:
        from playwright.async_api import async_playwright
        import base64
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            pg = await browser.new_page()
            await pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            await pg.wait_for_timeout(3000)

            kw = section_keyword.lower()
            candidates = [
                f"[class*='{kw}']",
                f"[id*='{kw}']",
                f"section:has-text('{section_keyword}')",
                f"div:has-text('{section_keyword}')",
                f"header:has-text('{section_keyword}')",
                f"main:has-text('{section_keyword}')",
                f"#{kw}",
                f".{kw}",
                f"[data-testid*='{kw}']",
                f"[aria-label*='{section_keyword}']",
            ]
            
            element = None
            for sel in candidates:
                try:
                    el = await pg.query_selector(sel)
                    if el and await el.is_visible():
                        element = el
                        break
                except Exception:
                    pass

            if element:
                await element.scroll_into_view_if_needed()
                await pg.wait_for_timeout(1000)
                screenshot_bytes = await element.screenshot()
            else:
                screenshot_bytes = await pg.screenshot()

            await browser.close()
            
            b64_img = base64.b64encode(screenshot_bytes).decode('utf-8')
            return b64_img
    except Exception as e:
        print("section_screenshot_async error:", str(e))
        return None


def section_screenshot(url, section_keyword):
    print("section_screenshot started:", section_keyword)
    try:
        from playwright.sync_api import sync_playwright
        import base64
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)

            kw = section_keyword.lower()
            candidates = [
                f"[class*='{kw}']",
                f"[id*='{kw}']",
                f"section:has-text('{section_keyword}')",
                f"div:has-text('{section_keyword}')",
                f"header:has-text('{section_keyword}')",
                f"main:has-text('{section_keyword}')",
                f"#{kw}",
                f".{kw}",
                f"[data-testid*='{kw}']",
                f"[aria-label*='{section_keyword}']",
            ]
            
            element = None
            for sel in candidates:
                try:
                    el = pg.query_selector(sel)
                    if el and el.is_visible():
                        element = el
                        break
                except Exception:
                    pass

            if element:
                element.scroll_into_view_if_needed()
                pg.wait_for_timeout(1000)
                screenshot_bytes = element.screenshot()
            else:
                screenshot_bytes = pg.screenshot()

            browser.close()
            
            b64_img = base64.b64encode(screenshot_bytes).decode('utf-8')
            return b64_img
    except Exception as e:
        print("section_screenshot error:", str(e))
        return None

def _sync_get_section_with_description(url, section_keyword):
    try:
        from playwright.sync_api import sync_playwright
        import base64
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)

            kw = section_keyword.lower()
            candidates = [
                f"[class*='{kw}']",
                f"[id*='{kw}']",
                "section",
                "article"
            ]
            
            element = None
            for sel in candidates:
                try:
                    el = pg.query_selector(sel)
                    if el and el.is_visible():
                        element = el
                        break
                except Exception:
                    pass

            if element:
                element.scroll_into_view_if_needed()
                pg.wait_for_timeout(1000)
                screenshot_bytes = element.screenshot()
                b64_img = base64.b64encode(screenshot_bytes).decode('utf-8')
                desc_text = element.inner_text()
                browser.close()
                return {"image": f"data:image/png;base64,{b64_img}", "description": desc_text[:300]}
            
            browser.close()
            return None
    except Exception as e:
        print("get_section_with_description error:", str(e))
        return None


async def get_section_with_description(url, section_keyword):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_section_with_description, url, section_keyword)


def _sync_get_all_sections(url):
    from playwright.sync_api import sync_playwright
    import os, time
    os.makedirs("static/screenshots", exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            imgs = page.query_selector_all("img")
            print("total imgs found:", len(imgs))
            idx = 0
            for img in imgs:
                if idx >= 6:
                    break
                try:
                    bb = img.bounding_box()
                    if not bb or bb['height'] < 50 or bb['width'] < 50:
                        continue
                    img.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    ss_name = f"{int(time.time())}_{idx}.png"
                    fpath = f"static/screenshots/{ss_name}"
                    img.screenshot(path=fpath)
                    alt = img.get_attribute("alt") or ""
                    surrounding = img.evaluate("el => el.closest('section,div,article')?.innerText?.slice(0,200)") or ""
                    src = img.get_attribute("src") or ""
                    src_name = src.split("/")[-1].split(".")[0].replace("-", " ").replace("_", " ")
                    desc = alt if alt else surrounding[:150].strip() if surrounding.strip() else src_name
                    print("DESC DEBUG - alt:", repr(alt), "src_name:", repr(src_name), "desc:", repr(desc))
                    results.append({
                        "image": f"http://localhost:8000/static/screenshots/{ss_name}",
                        "description": desc
                    })
                    print("captured img:", idx, "desc:", desc[:50])
                    idx += 1
                except Exception as e:
                    print("img error:", str(e))
                    continue
        except Exception as e:
            print("page error:", str(e))
        finally:
            browser.close()
    print("total captured:", len(results))
    return results


    from playwright.sync_api import sync_playwright
    import os, time
    os.makedirs("static/screenshots", exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            imgs = page.query_selector_all("img")
            print("total imgs found:", len(imgs))
            idx = 0
            for img in imgs:
                if idx >= 6:
                    break
                try:
                    bb = img.bounding_box()
                    if not bb or bb['height'] < 50 or bb['width'] < 50:
                        continue
                    img.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    fname = f"{int(time.time())}_{idx}.png"
                    fpath = f"static/screenshots/{fname}"
                    img.screenshot(path=fpath)
                    alt = img.get_attribute("alt") or ""
                    surrounding = img.evaluate("el => el.closest('section,div,article')?.innerText?.slice(0,200)") or ""
                    src = img.get_attribute("src") or ""
                    fname = src.split("/")[-1].split(".")[0].replace("-", " ").replace("_", " ")
                    desc = alt if alt else surrounding[:150] if surrounding.strip() else fname
                    print("DESC DEBUG - alt:", repr(alt), "surrounding:", repr(surrounding[:30]), "src:", repr(src), "fname:", repr(fname), "desc:", repr(desc))
                    results.append({
                        "image": f"http://localhost:8000/static/screenshots/{fname}",
                        "description": desc
                    })
                    print("captured img:", idx, "desc:", desc[:50])
                    idx += 1
                except Exception as e:
                    print("img error:", str(e))
                    continue
        except Exception as e:
            print("page error:", str(e))
        finally:
            browser.close()
    print("total captured:", len(results))
    return results


def _sync_get_section_images(url, section_name):
    from playwright.sync_api import sync_playwright
    import os, time
    os.makedirs("static/screenshots", exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            els = page.query_selector_all("section, div, article")
            matched = []
            for el in els:
                try:
                    txt = el.inner_text().lower()
                    if section_name.lower() in txt:
                        matched.append(el)
                except Exception:
                    continue
            print("matched sections:", len(matched))
            idx = 0
            for el in matched:
                imgs = el.query_selector_all("img")
                for img in imgs:
                    if idx >= 6:
                        break
                    try:
                        bb = img.bounding_box()
                        if not bb or bb['height'] < 50 or bb['width'] < 50:
                            continue
                        img.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        ss_name = f"{int(time.time())}_{idx}.png"
                        fpath = f"static/screenshots/{ss_name}"
                        img.screenshot(path=fpath)
                        alt = img.get_attribute("alt") or ""
                        title = img.get_attribute("title") or ""
                        surrounding = img.evaluate("el => el.closest('section,div,article')?.innerText?.slice(0,200)") or ""
                        src = img.get_attribute("src") or ""
                        src_name = src.split("/")[-1].split(".")[0].replace("-", " ").replace("_", " ")
                        desc = alt if alt else title if title else surrounding[:150].strip() if surrounding.strip() else src_name
                        print("DESC DEBUG - alt:", repr(alt), "src_name:", repr(src_name), "desc:", repr(desc))
                        results.append({
                            "image": f"http://localhost:8000/static/screenshots/{ss_name}",
                            "description": desc
                        })
                        print("captured section img:", idx, "desc:", desc[:50])
                        idx += 1
                    except Exception as e:
                        print("section img error:", str(e))
                        continue
                if idx >= 6:
                    break
        except Exception as e:
            print("section page error:", str(e))
        finally:
            browser.close()
    print("total section imgs captured:", len(results))
    return results
    
    from playwright.sync_api import sync_playwright
    import os, time
    os.makedirs("static/screenshots", exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            els = page.query_selector_all("section, div, article")
            matched = []
            for el in els:
                try:
                    txt = el.inner_text().lower()
                    if section_name.lower() in txt:
                        matched.append(el)
                except Exception:
                    continue
            print("matched sections:", len(matched))
            idx = 0
            for el in matched:
                imgs = el.query_selector_all("img")
                for img in imgs:
                    if idx >= 6:
                        break
                    try:
                        bb = img.bounding_box()
                        if not bb or bb['height'] < 50 or bb['width'] < 50:
                            continue
                        img.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        fname = f"{int(time.time())}_{idx}.png"
                        fpath = f"static/screenshots/{fname}"
                        img.screenshot(path=fpath)
                        alt = img.get_attribute("alt") or ""
                        title = img.get_attribute("title") or ""
                        surrounding = img.evaluate("el => el.closest('section,div,article')?.innerText?.slice(0,200)") or ""
                        src = img.get_attribute("src") or ""
                        fname = src.split("/")[-1].split(".")[0].replace("-", " ").replace("_", " ")
                        desc = alt if alt else title if title else surrounding[:150] if surrounding.strip() else fname
                        print("DESC DEBUG - alt:", repr(alt), "surrounding:", repr(surrounding[:30]), "src:", repr(src), "fname:", repr(fname), "desc:", repr(desc))
                        results.append({
                            "image": f"http://localhost:8000/static/screenshots/{fname}",
                            "description": desc
                        })
                        print("captured section img:", idx, "desc:", desc[:50])
                        idx += 1
                    except Exception as e:
                        print("section img error:", str(e))
                        continue
                if idx >= 6:
                    break
        except Exception as e:
            print("section page error:", str(e))
        finally:
            browser.close()
    print("total section imgs captured:", len(results))
    return results


def _sync_get_page_images(url):
    try:
        from playwright.sync_api import sync_playwright
        import base64
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)
            
            pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            pg.wait_for_timeout(2000)
            
            images = []
            img_elements = pg.query_selector_all("img")
            
            for i, img in enumerate(img_elements):
                if len(images) >= 6:
                    break
                try:
                    if img.is_visible():
                        src = img.get_attribute("src")
                        if src and src.startswith("http"):
                            alt_text = img.get_attribute("alt") or f"Image {i+1}"
                            screenshot_bytes = img.screenshot()
                            b64_img = base64.b64encode(screenshot_bytes).decode('utf-8')
                            images.append({
                                "image": f"data:image/png;base64,{b64_img}",
                                "description": alt_text
                            })
                except Exception:
                    pass
            
            browser.close()
            return images
    except Exception as e:
        print("get_page_images error:", str(e))
        return []


def _sync_get_section_data_with_page(pg, url, section, wants_images, wants_description):
    try:
        import time
        
        os.makedirs("static/screenshots", exist_ok=True)
        
        element = None
        
        try:
            element = pg.query_selector(f"[class*='{section}'], [id*='{section}']")
            if element and element.is_visible():
                pass
            else:
                element = None
        except Exception:
            element = None
        
        if not element:
            try:
                headings = pg.query_selector_all("h1, h2, h3, h4, h5, h6")
                for h in headings:
                    if section.lower() in h.inner_text().lower():
                        element = h.query_selector("xpath=..") or h
                        break
            except Exception:
                pass
        
        images = []
        description = ""
        img_descriptions = []
        
        if wants_images:
            ts = int(time.time())
            
            if element:
                try:
                    element.scroll_into_view_if_needed()
                    pg.wait_for_timeout(1000)
                    filename = f"{ts}_{section}.png"
                    filepath = f"static/screenshots/{filename}"
                    element.screenshot(path=filepath)
                    images.append(f"/static/screenshots/{filename}")
                except Exception:
                    pass
                
                try:
                    imgs = element.query_selector_all("img")
                    print("imgs found:", len(imgs))
                    paths = []
                    for n, img in enumerate(imgs):
                        try:
                            box = img.bounding_box()
                            print(f"img {n} box:", box)
                            if not box or box["width"] < 50 or box["height"] < 50:
                                continue
                            img.scroll_into_view_if_needed()
                            pg.wait_for_timeout(800)
                            ts = int(time.time() * 1000)
                            p = f"static/screenshots/{ts}_img_{n}.png"
                            pg.screenshot(path=p, clip={"x": max(0, box["x"]), "y": max(0, box["y"]), "width": box["width"], "height": box["height"]})
                            alt = img.get_attribute("alt") or f"Image {n+1}"
                            paths.append("/" + p)
                            img_descriptions.append(alt)
                            print(f"img {n} captured: {p}")
                        except Exception as e:
                            print(f"img {n} error:", e)
                            continue
                    images.extend(paths)
                except Exception:
                    pass
            else:
                try:
                    filename = f"{ts}_{section}.png"
                    filepath = f"static/screenshots/{filename}"
                    pg.screenshot(path=filepath)
                    images.append(f"/static/screenshots/{filename}")
                except Exception:
                    pass
                
                try:
                    imgs = pg.query_selector_all("img")
                    print("imgs found:", len(imgs))
                    paths = []
                    for n, img in enumerate(imgs):
                        try:
                            box = img.bounding_box()
                            print(f"img {n} box:", box)
                            if not box or box["width"] < 50 or box["height"] < 50:
                                continue
                            img.scroll_into_view_if_needed()
                            pg.wait_for_timeout(800)
                            ts = int(time.time() * 1000)
                            p = f"static/screenshots/{ts}_img_{n}.png"
                            pg.screenshot(path=p, clip={"x": max(0, box["x"]), "y": max(0, box["y"]), "width": box["width"], "height": box["height"]})
                            alt = img.get_attribute("alt") or f"Image {n+1}"
                            paths.append("/" + p)
                            img_descriptions.append(alt)
                            print(f"img {n} captured: {p}")
                        except Exception as e:
                            print(f"img {n} error:", e)
                            continue
                    images.extend(paths)
                except Exception:
                    pass
        
        if wants_description and element:
            try:
                description = element.inner_text()[:500]
            except Exception:
                pass
        
        return {"images": images, "description": description, "img_descriptions": img_descriptions}
    except Exception as e:
        print("get_section_data_with_page error:", str(e))
        return {"images": [], "description": "", "img_descriptions": []}


def _sync_get_section_data(url, section, wants_images, wants_description):
    try:
        from playwright.sync_api import sync_playwright
        import time
        
        os.makedirs("static/screenshots", exist_ok=True)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)
            
            element = None
            
            try:
                element = pg.query_selector(f"[class*='{section}'], [id*='{section}']")
                if element and element.is_visible():
                    pass
                else:
                    element = None
            except Exception:
                element = None
            
            if not element:
                try:
                    headings = pg.query_selector_all("h1, h2, h3, h4, h5, h6")
                    for h in headings:
                        if section.lower() in h.inner_text().lower():
                            element = h.query_selector("xpath=..") or h
                            break
                except Exception:
                    pass
            
            images = []
            description = ""
            img_descriptions = []
            
            if wants_images:
                ts = int(time.time())
                
                if element:
                    try:
                        element.scroll_into_view_if_needed()
                        pg.wait_for_timeout(1000)
                        filename = f"{ts}_{section}.png"
                        filepath = f"static/screenshots/{filename}"
                        element.screenshot(path=filepath)
                        images.append(f"/static/screenshots/{filename}")
                    except Exception:
                        pass
                    
                    try:
                        imgs = element.query_selector_all("img")
                        print("imgs found:", len(imgs))
                        paths = []
                        for n, img in enumerate(imgs):
                            try:
                                box = img.bounding_box()
                                print(f"img {n} box:", box)
                                if not box or box["width"] < 50 or box["height"] < 50:
                                    continue
                                img.scroll_into_view_if_needed()
                                pg.wait_for_timeout(800)
                                ts = int(time.time() * 1000)
                                p = f"static/screenshots/{ts}_img_{n}.png"
                                pg.screenshot(path=p, clip={"x": max(0, box["x"]), "y": max(0, box["y"]), "width": box["width"], "height": box["height"]})
                                alt = img.get_attribute("alt") or f"Image {n+1}"
                                paths.append("/" + p)
                                img_descriptions.append(alt)
                                print(f"img {n} captured: {p}")
                            except Exception as e:
                                print(f"img {n} error:", e)
                                continue
                        images.extend(paths)
                    except Exception:
                        pass
                else:
                    try:
                        filename = f"{ts}_{section}.png"
                        filepath = f"static/screenshots/{filename}"
                        pg.screenshot(path=filepath)
                        images.append(f"/static/screenshots/{filename}")
                    except Exception:
                        pass
                    
                    try:
                        imgs = pg.query_selector_all("img")
                        print("imgs found:", len(imgs))
                        paths = []
                        for n, img in enumerate(imgs):
                            try:
                                box = img.bounding_box()
                                print(f"img {n} box:", box)
                                if not box or box["width"] < 50 or box["height"] < 50:
                                    continue
                                img.scroll_into_view_if_needed()
                                pg.wait_for_timeout(800)
                                ts = int(time.time() * 1000)
                                p = f"static/screenshots/{ts}_img_{n}.png"
                                pg.screenshot(path=p, clip={"x": max(0, box["x"]), "y": max(0, box["y"]), "width": box["width"], "height": box["height"]})
                                alt = img.get_attribute("alt") or f"Image {n+1}"
                                paths.append("/" + p)
                                img_descriptions.append(alt)
                                print(f"img {n} captured: {p}")
                            except Exception as e:
                                print(f"img {n} error:", e)
                                continue
                        images.extend(paths)
                    except Exception:
                        pass
            
            if wants_description and element:
                try:
                    description = element.inner_text()[:500]
                except Exception:
                    pass
            
            browser.close()
            return {"images": images, "description": description, "img_descriptions": img_descriptions}
    except Exception as e:
        print("get_section_data error:", str(e))
        return {"images": [], "description": "", "img_descriptions": []}

def _sync_get_page_images_new(url):
    try:
        from playwright.sync_api import sync_playwright
        import time
        
        os.makedirs("static/screenshots", exist_ok=True)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.set_default_timeout(10000)
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)
            
            images = []
            ts = int(time.time())
            
            for i in range(3):
                filename = f"{ts}_page_{i}.png"
                filepath = f"static/screenshots/{filename}"
                try:
                    pg.screenshot(path=filepath)
                    images.append({"image": f"/static/screenshots/{filename}", "description": ""})
                except Exception:
                    pass
                
                if i < 2:
                    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    pg.wait_for_timeout(1000)
            
            browser.close()
            return images
    except Exception as e:
        print("get_page_images error:", str(e))
        return []

def _sync_get_contact_info(url):
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            email = ""
            phone = ""
            address = ""
            
            try:
                mailto_links = pg.query_selector_all("a[href^='mailto:']")
                if mailto_links:
                    email = mailto_links[0].get_attribute("href").replace("mailto:", "")
            except Exception:
                pass
            
            try:
                tel_links = pg.query_selector_all("a[href^='tel:']")
                if tel_links:
                    phone = tel_links[0].get_attribute("href").replace("tel:", "")
            except Exception:
                pass
            
            try:
                footer = pg.query_selector("footer")
                if footer:
                    address = footer.inner_text()[:200]
            except Exception:
                pass
            
            browser.close()
            return {"email": email, "phone": phone, "address": address}
    except Exception as e:
        print("get_contact_info error:", str(e))
        return {"email": "", "phone": "", "address": ""}

def _sync_get_social_links(url):
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            social_links = []
            platforms = ["facebook", "twitter", "instagram", "linkedin", "youtube", "tiktok"]
            
            for platform in platforms:
                try:
                    links = pg.query_selector_all(f"a[href*='{platform}']")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and platform in href:
                            social_links.append({"platform": platform, "url": href})
                            break
                except Exception:
                    pass
            
            browser.close()
            return social_links
    except Exception as e:
        print("get_social_links error:", str(e))
        return []

def _sync_get_navigation(url):
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            nav_links = []
            
            try:
                nav = pg.query_selector("nav")
                if nav:
                    links = nav.query_selector_all("a")
                    for link in links:
                        label = link.inner_text().strip()
                        href = link.get_attribute("href")
                        if label and href:
                            nav_links.append({"label": label, "url": href})
            except Exception:
                pass
            
            browser.close()
            return nav_links
    except Exception as e:
        print("get_navigation error:", str(e))
        return []

def _sync_get_mobile_screenshot(url):
    try:
        from playwright.sync_api import sync_playwright
        import time
        
        os.makedirs("static/screenshots", exist_ok=True)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page(viewport={"width": 390, "height": 844})
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)
            
            ts = int(time.time())
            filename = f"{ts}_mobile.png"
            filepath = f"static/screenshots/{filename}"
            
            pg.screenshot(path=filepath, full_page=True)
            
            browser.close()
            return f"/static/screenshots/{filename}"
    except Exception as e:
        print("get_mobile_screenshot error:", str(e))
        return ""

def _sync_get_table_data(url, section):
    try:
        from playwright.sync_api import sync_playwright
        import time
        
        os.makedirs("static/screenshots", exist_ok=True)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9"
            })
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(3000)
            
            table = None
            
            if section:
                try:
                    table = pg.query_selector(f"[class*='{section}'] table, [id*='{section}'] table")
                except Exception:
                    pass
            
            if not table:
                try:
                    table = pg.query_selector("table")
                except Exception:
                    pass
            
            if not table:
                try:
                    table = pg.query_selector("[class*='pricing'], [class*='table']")
                except Exception:
                    pass
            
            image = ""
            data = ""
            
            if table:
                try:
                    ts = int(time.time())
                    filename = f"{ts}_table.png"
                    filepath = f"static/screenshots/{filename}"
                    table.screenshot(path=filepath)
                    image = f"/static/screenshots/{filename}"
                    data = table.inner_text()
                except Exception:
                    pass
            
            browser.close()
            return {"image": image, "data": data}
    except Exception as e:
        print("get_table_data error:", str(e))
        return {"image": "", "data": ""}

async def get_section_data(url, section, wants_images, wants_description):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_section_data, url, section, wants_images, wants_description)

async def get_page_images(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_page_images_new, url)

async def get_contact_info(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_contact_info, url)

async def get_social_links(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_social_links, url)

async def get_navigation(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_navigation, url)

async def get_mobile_screenshot(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_mobile_screenshot, url)

async def get_table_data(url, section):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_table_data, url, section)

async def get_all_sections(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_all_sections, url)

async def get_section_images(url, section_name):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_section_images, url, section_name)


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
