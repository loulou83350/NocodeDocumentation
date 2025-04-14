import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import time
from collections import deque

DEV_BASE_URL = "https://developer.weweb.io"
DOCS_BASE_URL = "https://docs.weweb.io"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_all_urls(base_url):
    """Explore récursivement toutes les URLs du site en suivant les menus"""
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
            
            # Détection des liens dans les menus et contenus principaux
            menu_selectors = [
                'nav a[href]',
                '.navbar a[href]', 
                '.sidebar a[href]',
                '.menu a[href]',
                '.dropdown a[href]',
                'a.menu-item[href]',
                'main a[href]',
                'article a[href]',
                '.content a[href]'
            ]
            
            for selector in menu_selectors:
                for a in soup.select(selector):
                    href = a.get('href', '')
                    if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                        continue
                        
                    absolute_url = urljoin(base_url, href)
                    if absolute_url.startswith(base_url):
                        clean_url = absolute_url.split('#')[0].rstrip('/')
                        if clean_url not in visited and clean_url not in queue:
                            queue.append(clean_url)
            
            time.sleep(0.8)  # Respect du serveur
            
        except Exception as e:
            print(f"⚠️ Erreur avec {url}: {str(e)}")
            continue
            
    return sorted(visited)

def detect_language(element):
    """Détecte le langage d'un snippet de code"""
    language_classes = [
        'language-js', 'language-javascript',
        'language-html', 'language-css',
        'language-sql', 'language-json',
        'language-python', 'language-php'
    ]
    
    classes = element.get('class', [])
    for cls in classes:
        if cls in language_classes:
            return cls.replace('language-', '')
    
    return 'unknown'

def clean_code_content(code):
    """Nettoie le contenu du code"""
    return code.strip().replace('\r\n', '\n').replace('\r', '\n')

def extract_code_snippets(element):
    """Extrait tous les snippets de code avec leur langage"""
    snippets = []
    
    # Balises <pre><code>
    for pre in element.find_all('pre'):
        code = pre.find('code')
        if code:
            snippets.append({
                'code': clean_code_content(code.text),
                'language': detect_language(code)
            })
    
    # Divs avec classes de code
    code_divs = element.find_all('div', class_=lambda x: x and any(
        c in ['code-block', 'shiki', 'highlight', 'prism-code'] or 
        c.startswith('language-') for c in x.split()
    ))
    
    for div in code_divs:
        snippets.append({
            'code': clean_code_content(div.text),
            'language': detect_language(div)
        })
    
    return snippets

def extract_images(element, base_url):
    """Extrait toutes les images d'un élément"""
    images = set()
    
    for img in element.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
        if src:
            if not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
            images.add(src)
    
    return list(images)

def scrape_page(url):
    """Scrape une page complète avec ses sections"""
    try:
        print(f"⏳ Scraping de {url}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_data = {
            'url': url,
            'title': soup.title.get_text().strip() if soup.title else url.split('/')[-1],
            'sections': {}
        }
        
        # Détection de toutes les sections avec ancres
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
            section_id = heading.get('id')
            if not section_id:
                continue
                
            section = {
                'title': heading.get_text().strip(),
                'content': [],
                'code_snippets': [],
                'images': [],
                'tips': []
            }
            
            # Parcours du contenu jusqu'au prochain titre
            next_node = heading.next_sibling
            while next_node and next_node.name not in ['h1', 'h2', 'h3', 'h4', 'h5']:
                if isinstance(next_node, str):
                    text = next_node.strip()
                    if text:
                        section['content'].append(text)
                elif next_node.name:
                    # Contenu textuel
                    if next_node.name in ['p', 'ul', 'ol', 'blockquote']:
                        section['content'].append(next_node.get_text(' ', strip=True))
                    
                    # Images
                    section['images'].extend(extract_images(next_node, url))
                    
                    # Tips/notes
                    if next_node.name == 'div' and any('tip' in c.lower() for c in next_node.get('class', [])):
                        section['tips'].append(next_node.get_text(' ', strip=True))
                    
                    # Code snippets
                    section['code_snippets'].extend(extract_code_snippets(next_node))
                
                next_node = next_node.next_sibling
            
            # Nettoyage final
            section['content'] = '\n'.join(section['content']).strip()
            section['images'] = list(set(section['images']))  # Supprime doublons
            
            # Suppression des snippets en double
            seen_snippets = set()
            unique_snippets = []
            for snippet in section['code_snippets']:
                snippet_key = (snippet['code'], snippet['language'])
                if snippet_key not in seen_snippets:
                    seen_snippets.add(snippet_key)
                    unique_snippets.append(snippet)
            section['code_snippets'] = unique_snippets
            
            page_data['sections'][f"{url}#{section_id}"] = section
        
        return page_data
    
    except Exception as e:
        print(f"❌ Erreur lors du scraping de {url}: {str(e)}")
        return None

def main():
    print("🚀 Début du scraping complet WeWeb")
    print("⏳ Cette opération peut prendre plusieurs minutes...")
    
    # Récupération des URLs
    print("\n🔍 Exploration des URLs...")
    dev_urls = get_all_urls(DEV_BASE_URL)
    docs_urls = get_all_urls(DOCS_BASE_URL)
    
    print(f"\n🔗 {len(dev_urls)} URLs développeur trouvées")
    print(f"📄 {len(docs_urls)} URLs documentation trouvées")
    
    # Scraping des pages
    print("\n⏳ Extraction du contenu...")
    all_data = []
    
    for i, url in enumerate(dev_urls + docs_urls, 1):
        if page_data := scrape_page(url):
            all_data.append(page_data)
        print(f"📊 Progression: {i}/{len(dev_urls)+len(docs_urls)} pages traitées", end='\r')
        time.sleep(1)  # Pause de politesse
    
    # Sauvegarde
    output_file = "weweb_documentation_complete.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Données sauvegardées dans {output_file}")
    print(f"📂 Total: {len(all_data)} pages avec {sum(len(p['sections']) for p in all_data)} sections")

if __name__ == "__main__":
    main()