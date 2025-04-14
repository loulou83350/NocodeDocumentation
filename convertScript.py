import json
import csv
import uuid

# Charger le JSON
with open('weweb_firebase_ready.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Fonction pour nettoyer le texte
def clean_text(text):
    return text.replace('\n', ' ').replace('\r', ' ').strip() if text else ''

# Générer les CSV
with open('pages.csv', 'w', newline='', encoding='utf-8') as pages_file, \
     open('sections.csv', 'w', newline='', encoding='utf-8') as sections_file, \
     open('code_snippets.csv', 'w', newline='', encoding='utf-8') as code_snippets_file, \
     open('images.csv', 'w', newline='', encoding='utf-8') as images_file, \
     open('tips.csv', 'w', newline='', encoding='utf-8') as tips_file:

    # Configurer les writers CSV
    writers = {
        'pages': csv.DictWriter(pages_file, fieldnames=['id', 'url', 'title', 'created_at', 'scraped_at', 'source_url']),
        'sections': csv.DictWriter(sections_file, fieldnames=['id', 'page_id', 'section_id', 'title', 'content', 'order']),
        'code_snippets': csv.DictWriter(code_snippets_file, fieldnames=['id', 'section_id', 'code', 'language', 'order']),
        'images': csv.DictWriter(images_file, fieldnames=['id', 'section_id', 'url', 'alt_text', 'order']),
        'tips': csv.DictWriter(tips_file, fieldnames=['id', 'section_id', 'content', 'order'])
    }

    # Écrire les en-têtes
    for writer in writers.values():
        writer.writeheader()

    # Traiter chaque page
    for page_key, page_data in data['pages'].items():
        page_id = str(uuid.uuid5(uuid.NAMESPACE_URL, page_key))
        
        # Écrire la page
        writers['pages'].writerow({
            'id': page_id,
            'url': page_data.get('url', ''),
            'title': clean_text(page_data.get('title', '')),
            'created_at': data['metadata'].get('created_at', ''),
            'scraped_at': page_data['metadata'].get('scraped_at', ''),
            'source_url': page_data['metadata'].get('source_url', '')
        })

        # Traiter les sections
        if 'sections' in page_data:
            for section_order, (section_key, section_data) in enumerate(page_data['sections'].items(), 1):
                section_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{page_key}_{section_key}"))
                
                writers['sections'].writerow({
                    'id': section_id,
                    'page_id': page_id,
                    'section_id': section_key,
                    'title': clean_text(section_data.get('title', '')),
                    'content': clean_text(section_data.get('content', '')),
                    'order': section_order
                })

                # Écrire les code snippets
                for cs_order, cs in enumerate(section_data.get('code_snippets', []), 1):
                    writers['code_snippets'].writerow({
                        'id': str(uuid.uuid4()),
                        'section_id': section_id,
                        'code': clean_text(cs.get('code', '')),
                        'language': clean_text(cs.get('language', 'unknown')),
                        'order': cs_order
                    })

                # Écrire les images
                for img_order, img in enumerate(section_data.get('images', []), 1):
                    writers['images'].writerow({
                        'id': str(uuid.uuid4()),
                        'section_id': section_id,
                        'url': img if isinstance(img, str) else img.get('url', ''),
                        'alt_text': '' if isinstance(img, str) else img.get('alt_text', ''),
                        'order': img_order
                    })

                # Écrire les tips
for tip_order, tip in enumerate(section_data.get('tips', []), 1):
    if tip:  # Ne traiter que si le tip n'est pas vide
        writers['tips'].writerow({
            'id': str(uuid.uuid4()),
            'section_id': section_id,
            'content': clean_text(tip),
            'order': tip_order
        })

print("Conversion terminée ! Fichiers CSV générés : pages.csv, sections.csv, code_snippets.csv, images.csv, tips.csv")