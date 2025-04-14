import asyncio
import csv
from playwright.async_api import async_playwright
import os

BASE_URL = "https://docs.n8n.io"
OUTPUT_DIR = "n8n_notion_csv"
CSV_FILE = "n8n_docs.csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def scrape_docs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(BASE_URL)
        await page.wait_for_selector("nav a")
        
        links = await page.eval_on_selector_all("nav a", "elements => elements.map(e => e.href)")
        links = list(set([link for link in links if link.startswith(BASE_URL)]))
        
        with open(os.path.join(OUTPUT_DIR, CSV_FILE), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'URL', 'Content'])  # En-têtes Notion
            
            for link in links:
                try:
                    await page.goto(link)
                    await page.wait_for_selector("main")
                    
                    # Extraction des données
                    title = await page.title()
                    title = title.replace(" | n8n Docs", "").strip()
                    
                    content_selector = await page.query_selector('main .md-content__inner') or await page.query_selector('main article')
                    content = await content_selector.inner_text() if content_selector else ""
                    content = ' '.join(content.split()).strip()
                    
                    # Écriture dans le CSV
                    writer.writerow([title, link, content])
                    print(f"✅ {title[:50]}... ajouté au CSV")

                except Exception as e:
                    print(f"❌ Erreur sur {link}: {str(e)}")
        
        await browser.close()

asyncio.run(scrape_docs())