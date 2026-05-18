#!/usr/bin/env python3

import os
import asyncio
import json

from dotenv import load_dotenv

load_dotenv()
from openai import OpenAI
from tools.parser import section_screenshot, section_screenshot_async, scrape_js

client = OpenAI()

async def test_intent_analysis():
    print("=== Testing Intent Analysis ===")
    
    site_url = "https://example.com"
    query = "Show me the hero section"
    
    intent_prompt = f"""Site URL: {site_url}
User query: {query}
Respond in JSON only:
{{"needs_scrape": true/false,"target_url": "full url to scrape or null","target_section": "css selector or keyword like 'services', 'hero', 'pricing' or null","answer_from_report": true/false}}"""

    try:
        res = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": intent_prompt}],
                timeout=30
            )
        )
        intent_res = res.choices[0].message.content.strip()
        print("Intent analysis result:", intent_res)
        
        # Clean up markdown formatting if present
        if intent_res.startswith("```json"):
            intent_res = intent_res.replace("```json", "").replace("```", "").strip()
        
        intent = json.loads(intent_res)
        print("Parsed intent:", intent)
        return intent
    except Exception as e:
        print("Intent analysis error:", str(e))
        return {"needs_scrape": False, "answer_from_report": True}

async def test_scraping():
    print("\n=== Testing Scraping ===")
    
    try:
        result = await scrape_js("https://example.com")
        print("Scrape result keys:", result.keys() if isinstance(result, dict) else "Not a dict")
        print("Content length:", len(result.get("text", "")) if isinstance(result, dict) else 0)
        return result
    except Exception as e:
        print("Scraping error:", str(e))
        return None

async def test_section_screenshot():
    print("\n=== Testing Section Screenshot ===")
    
    try:
        result = await section_screenshot_async("https://example.com", "hero")
        print("Screenshot result type:", type(result))
        print("Screenshot length:", len(result) if result else 0)
        print("Is base64?", result.startswith("iVBOR") if result else False)
        return result
    except Exception as e:
        print("Section screenshot error:", str(e))
        return None

async def test_complete_flow():
    print("\n=== Testing Complete Flow ===")
    
    intent = await test_intent_analysis()
    
    if intent.get("needs_scrape"):
        target_url = intent.get("target_url") or "https://example.com"
        target_section = intent.get("target_section")
        
        scrape_result = await test_scraping()
        
        images = []
        if target_section:
            b64_img = await test_section_screenshot()
            if b64_img:
                images.append(f"data:image/png;base64,{b64_img}")
        
        print("Final result:")
        print("- Content available:", bool(scrape_result and scrape_result.get("text")))
        print("- Images generated:", len(images))
        print("- Image format correct:", all(img.startswith("data:image/") for img in images))
        
        return {
            "content": scrape_result.get("text", "") if scrape_result else "",
            "images": images
        }
    
    return {"content": "", "images": []}

if __name__ == "__main__":
    asyncio.run(test_complete_flow())