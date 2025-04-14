import asyncio
import json
from playwright.async_api import async_playwright
import os

BASE_URL = "https://docs.n8n.io"
OUTPUT_DIR = "n8n_docs_simple"
JSON_FILE = "documentation.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def scrape_and_format_docs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(BASE_URL)

        await page.wait_for_selector("nav a")

        links = await page.eval_on_selector_all("nav a", "elements => elements.map(e => e.href)")
        links = list(set([link for link in links if link.startswith(BASE_URL)]))

        print(f"🔗 {len(links)} liens trouvés dans le menu")

        documentation = []

        for link in links:
            try:
                await page.goto(link)
                await page.wait_for_selector("main")
                
                content = await page.query_selector('main .md-content__inner') or await page.query_selector('main article')
                
                # Extraction du titre h1
                h1_element = await content.query_selector('h1')
                title = await h1_element.inner_text() if h1_element else "Sans titre"
                title = title.strip()
                
                # Extraction de tout le texte brut
                full_text = await content.inner_text() if content else ""
                full_text = " ".join(full_text.split()).strip()  # Nettoyage des espaces

                documentation.append({
                    "h1": title,
                    "url": link,
                    "content": full_text
                })

                print(f"✅ {title[:50]}... traité")

            except Exception as e:
                print(f"❌ Erreur sur {link}: {str(e)}")

        # Sauvegarde du JSON
        output_path = os.path.join(OUTPUT_DIR, JSON_FILE)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(documentation, f, ensure_ascii=False, indent=2)
            
        print(f"\n🎉 Fichier JSON généré : {output_path}")

        await browser.close()

asyncio.run(scrape_and_format_docs())