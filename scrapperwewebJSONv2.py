import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from collections import deque
import re
import csv
import os

# Configuration
DEV_BASE_URL = "https://developer.weweb.io"
DOCS_BASE_URL = "https://docs.weweb.io"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
OUTPUT_DIR = "weweb_notion_csv"
CSV_FILE = "weweb_docs.csv"
REQUEST_DELAY = 1.2

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

        # Extraction des données
        h1_tag = soup.find('h1')
        title = h1_tag.get_text(strip=True) if h1_tag else "Sans titre"
        
        main_content = soup.find(['main', 'article', 'div.content'])
        content = sanitize_text(main_content.get_text()) if main_content else ""

        return (title, url, content)

    except Exception as e:
        print(f"❌ Erreur de scraping: {str(e)}")
        return None

def main():
    print("🚀 Démarrage du scraping WeWeb")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n🔍 Exploration des sites...")
    dev_urls = get_all_urls(DEV_BASE_URL)
    docs_urls = get_all_urls(DOCS_BASE_URL)

    with open(os.path.join(OUTPUT_DIR, CSV_FILE), 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'URL', 'Content'])  # En-têtes Notion

        total = len(dev_urls) + len(docs_urls)
        start_time = time.time()

        for idx, url in enumerate(dev_urls + docs_urls, 1):
            print(f"\n📄 Traitement {idx}/{total}: {url}")
            page_data = scrape_page(url)
            
            if page_data:
                writer.writerow(page_data)
                print(f"✅ {page_data[0][:50]}... ajouté au CSV")
            
            time.sleep(REQUEST_DELAY)

    print(f"\n✅ Terminé en {time.time() - start_time:.2f} secondes")
    print(f"📂 Fichier CSV généré : {os.path.abspath(os.path.join(OUTPUT_DIR, CSV_FILE))}")

if __name__ == "__main__":
    main()