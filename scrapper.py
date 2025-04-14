import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import time
from collections import deque
import re
from datetime import datetime

# Configuration
DEV_BASE_URL = "https://developer.weweb.io"
DOCS_BASE_URL = "https://docs.weweb.io"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def sanitize_firebase_key(key):
    """Nettoie les clés pour les rendre compatibles avec Firebase"""
    key = str(key)
    # Remplace les caractères interdits par _
    key = re.sub(r'[\.\$#\[\]\/]', '_', key)
    # Supprime les espaces en début/fin et limite la longueur
    return key.strip()[:768]  # Limite de Firebase

def get_all_urls(base_url):
    """Explore récursivement toutes les URLs du site"""
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
            
            # Détection des liens
            for a in soup.find_all('a', href=True):
                href = a['href']
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                    continue
                    
                absolute_url = urljoin(base_url, href)
                if absolute_url.startswith(base_url):
                    clean_url = absolute_url.split('#')[0].rstrip('/')
                    if clean_url not in visited and clean_url not in queue:
                        queue.append(clean_url)
            
            time.sleep(0.8)
            
        except Exception as e:
            print(f"⚠️ Erreur avec {url}: {str(e)}")
            continue
            
    return sorted(visited)

def process_for_firebase(data):
    """Transforme les données pour Firebase"""
    if isinstance(data, dict):
        return {sanitize_firebase_key(k): process_for_firebase(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [process_for_firebase(item) for item in data]
    return data

def scrape_page(url):
    """Scrape une page et retourne des données Firebase-compatibles"""
    try:
        print(f"⏳ Scraping de {url}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_data = {
            'url': url,
            'title': sanitize_firebase_key(soup.title.get_text().strip() if soup.title else url.split('/')[-1]),
            'sections': {},
            'metadata': {
                'scraped_at': datetime.utcnow().isoformat(),
                'source_url': url
            }
        }
        
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
            section_id = heading.get('id')
            if not section_id:
                continue
                
            section = {
                'title': sanitize_firebase_key(heading.get_text().strip()),
                'content': [],
                'code_snippets': [],
                'images': [],
                'tips': []
            }
            
            next_node = heading.next_sibling
            while next_node and next_node.name not in ['h1', 'h2', 'h3', 'h4', 'h5']:
                if next_node.name:
                    # Traitement du contenu
                    if next_node.name in ['p', 'ul', 'ol']:
                        section['content'].append(next_node.get_text(' ', strip=True))
                    
                    # Images
                    for img in next_node.find_all('img'):
                        src = img.get('src') or img.get('data-src')
                        if src:
                            if not src.startswith(('http://', 'https://')):
                                src = urljoin(url, src)
                            if src not in section['images']:
                                section['images'].append(src)
                    
                    # Code snippets
                    for pre in next_node.find_all('pre'):
                        code = pre.find('code')
                        if code:
                            lang = 'unknown'
                            for cls in code.get('class', []):
                                if cls.startswith('language-'):
                                    lang = cls.replace('language-', '')
                                    break
                            snippet = {
                                'code': code.get_text().strip(),
                                'language': lang
                            }
                            if snippet not in section['code_snippets']:
                                section['code_snippets'].append(snippet)
                
                next_node = next_node.next_sibling
            
            # Formatage final
            section['content'] = '\n'.join(section['content']).strip()
            page_data['sections'][sanitize_firebase_key(section_id)] = section
        
        return process_for_firebase(page_data)
    
    except Exception as e:
        print(f"❌ Erreur lors du scraping de {url}: {str(e)}")
        return None

def main():
    print("🚀 Début du scraping pour Firebase")
    
    # Récupération des URLs
    print("\n🔍 Exploration des URLs...")
    dev_urls = get_all_urls(DEV_BASE_URL)
    docs_urls = get_all_urls(DOCS_BASE_URL)
    
    # Scraping
    print("\n⏳ Extraction du contenu...")
    firebase_data = {
        'metadata': {
            'created_at': datetime.utcnow().isoformat(),
            'total_pages': len(dev_urls) + len(docs_urls)
        },
        'pages': {}
    }
    
    for i, url in enumerate(dev_urls + docs_urls, 1):
        if page_data := scrape_page(url):
            page_key = sanitize_firebase_key(page_data['url'])
            firebase_data['pages'][page_key] = page_data
        print(f"📊 Progression: {i}/{len(dev_urls)+len(docs_urls)}", end='\r')
        time.sleep(1)
    
    # Sauvegarde
    output_file = "weweb_firebase_ready.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(firebase_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fichier prêt pour Firebase: {output_file}")
    print("💡 Importez-le via: Firebase Console → Realtime Database → ⏷ → Importer JSON")

if __name__ == "__main__":
    main()