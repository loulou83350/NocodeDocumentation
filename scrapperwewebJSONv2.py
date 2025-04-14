import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from collections import deque
import re
import json
import os

# Configuration
DEV_BASE_URL = "https://developer.weweb.io"
DOCS_BASE_URL = "https://docs.weweb.io"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
OUTPUT_DIR = "weweb_docs_json"
JSON_FILE = "documentation.json"
REQUEST_DELAY = 1.2  # Délai entre les requêtes

def sanitize_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def get_all_urls(base_url):
    visited = set()
    queue = deque([base_url])

    while queue:
        url = queue.popleft()
        if url in visited:
            continue

        try:
            print(f"🔍 Exploration de: {url}")
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            visited.add(url)

            for a in soup.find_all('a', href=True):
                href = a['href']
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    continue

                absolute_url = urljoin(base_url, href)
                if absolute_url.startswith(base_url):
                    clean_url = absolute_url.split('#')[0].rstrip('/')
                    if clean_url not in visited and clean_url not in queue:
                        queue.append(clean_url)

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"⚠️ Erreur avec {url}: {str(e)}")
            continue

    return sorted(visited)

def scrape_page(url):
    try:
        print(f"⏳ Scraping de {url}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extraction du titre h1
        h1_tag = soup.find('h1')
        title = h1_tag.get_text(strip=True) if h1_tag else "Sans titre"
        
        # Extraction du contenu principal
        main_content = soup.find(['main', 'article', 'div.content'])  # Adaptez ce sélecteur
        content_text = sanitize_text(main_content.get_text()) if main_content else ""

        return {
            "h1": title,
            "url": url,
            "content": content_text
        }

    except Exception as e:
        print(f"❌ Erreur de scraping: {str(e)}")
        return None

def main():
    print("🚀 Démarrage du scraping WeWeb")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n🔍 Exploration des sites...")
    dev_urls = get_all_urls(DEV_BASE_URL)
    docs_urls = get_all_urls(DOCS_BASE_URL)

    all_data = []
    total = len(dev_urls) + len(docs_urls)
    start_time = time.time()

    for idx, url in enumerate(dev_urls + docs_urls, 1):
        print(f"\n📄 Traitement {idx}/{total}: {url}")
        page_data = scrape_page(url)
        if page_data:
            all_data.append(page_data)
            print(f"✅ {page_data['h1'][:50]}... traité")
        time.sleep(REQUEST_DELAY)

    # Sauvegarde du JSON
    output_path = os.path.join(OUTPUT_DIR, JSON_FILE)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Terminé en {time.time() - start_time:.2f} secondes")
    print(f"📂 Fichier JSON généré : {os.path.abspath(output_path)}")

if __name__ == "__main__":
    main()