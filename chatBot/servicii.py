from fuzzywuzzy import fuzz
import unicodedata
import pandas as pd
from itertools import permutations
import re

produse = """
Iată toate produsele din categoria "RoofArt; China 0.30" cu prețul din listă:

1. **Профнастил HP&HA-18**
   - Цена из списка: 145,44 MDL / м2

2. **Профнастил HP&HA-7**
   - Цена из списка: 145,44 MDL / м2

3. **Профнастил HPV&HV-7**
   - Цена из списка: 145,44 MDL / м2

4. **Профнастил HP&HA-12**
   - Цена из списка: 159,98 MDL / м
5. **Сортовая стружка**
   - Цена из списка: 63,45 MDL / мл

6. **Аксессуары B250 мм**
   - Цена из списка: 100,05 MDL / мл

7. **Гребень прямой, Гребень полукруглый**
   - Цена из списка: 124,74 MDL / мл

8. **Водосток обычный**
   - Цена из списка: 166,79 MDL / мл

9. **Водосток RoofArt**
   - Цена из списка: 251,1 MDL / мл

10. **Прямая плита (1250x2000)**
    - Цена из списка: 145,44 MDL / м2
"""


def clean_nume(text):
    # Elimină simboluri nefolositoare, păstrează litere, cifre și spații
    text = re.sub(r"[\*\n\r\t]", "", text)  # elimină ** și caractere speciale
    text = re.sub(r"[^\w\s\-&]", "", text)  # păstrează doar litere, cifre, - și &
    return text.strip().lower()



def elimina_duplicate_rezultate(rezultate):
    seen = set()
    rezultate_unice = []
    for r in rezultate:
        cheie = (r['produs'], " ".join(sorted(r['cuvinte_cautate'].split())))
        if cheie not in seen:
            rezultate_unice.append(r)
            seen.add(cheie)
    return rezultate_unice

def normalize_text(text):
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
    return text

def extract_keywords(text):
    text = clean_nume(text)
    cuvinte = normalize_text(text).split()

    # Descompune tokenuri gen 'hp&ha-18' în 'hp', 'ha', '18'
    cuvinte_extinse = []
    for c in cuvinte:
        cuvinte_extinse.append(c)
        if '-' in c:
            cuvinte_extinse.extend(c.split('-'))
        if '&' in c:
            cuvinte_extinse.extend(c.split('&'))

    # Păstrăm doar cele utile
    return [x for x in cuvinte_extinse if len(x) > 2 or x.isdigit()]

def score_relevanta_cuvinte(interogare, df, fuzzy_threshold=70):
    keywords_interogare = extract_keywords(interogare)
    toate_cuvintele_produse = set()
    for nume in df['nume']:
        toate_cuvintele_produse.update(extract_keywords(nume))
        # print(toate_cuvintele_produse)

    relevante = []
    scoruri = []
    for cuv in keywords_interogare:
        max_scor = 0
        for prod_cuv in toate_cuvintele_produse:
            scor = fuzz.ratio(cuv, prod_cuv)
            if scor > max_scor:
                max_scor = scor
        if max_scor >= fuzzy_threshold:
            relevante.append(cuv)
            scoruri.append(max_scor)
    cuvinte_ordonate = [c for _, c in sorted(zip(scoruri, relevante), reverse=True)]
    return cuvinte_ordonate[:5]

def cauta_produs_inteligent_prioritate_lungime(interogare, df, threshold=80):
    relevante = score_relevanta_cuvinte(interogare, df, fuzzy_threshold=70)
    if not relevante:
        return None

    for lungime in range(len(relevante), 0, -1):
        potriviri_curente = []
        max_scor = 0
        for comb in permutations(relevante, lungime):
            text_cautat = " ".join(comb)
            for idx, row in df.iterrows():
                nume_norm = normalize_text(row['nume'])
                scor = fuzz.token_set_ratio(text_cautat, nume_norm)
                if scor >= threshold and scor > max_scor:
                    max_scor = scor
                    potriviri_curente = [{
                        "produs": row['nume'].title(),
                        "pret": row['pret'],
                        "scor": scor,
                        "cuvinte_cautate": text_cautat
                    }]
                elif scor >= threshold and scor == max_scor:
                    potriviri_curente.append({
                        "produs": row['nume'].title(),
                        "pret": row['pret'],
                        "scor": scor,
                        "cuvinte_cautate": text_cautat
                    })
        if potriviri_curente:
            potriviri_curente = elimina_duplicate_rezultate(potriviri_curente)
            return potriviri_curente
    return None


def fuzzy_contains(keyword_list, text, threshold=90):
    for kw in keyword_list:
        print("kw = " , kw)
        scor = fuzz.partial_ratio(kw.lower(), text.lower())
        print("scor = " , scor)
        if scor >= threshold:
            return True
    return False


def function_check_product(interogare, servicii , language):
    interogare_lower = interogare.lower().strip()
    chatbot_messenger = ["mesenger", "chatbot messenger" , "Mesenger"]
    
    if "pachet" in interogare_lower:
        # Cuvinte cheie per categorie
        business_keywords = ["business", "smart"]
        enterprise_keywords = ["enterprise", "complete"]
        startup_keywords = ["startup", "light"]
        print("business = " , fuzzy_contains(business_keywords, interogare_lower))
        print("enterprise = " , fuzzy_contains(enterprise_keywords, interogare_lower))
        print("startup = " , fuzzy_contains(startup_keywords, interogare_lower))
        print("111111111")
        if fuzzy_contains(business_keywords, interogare_lower):
            return [{
                "produs": "Pachet : Business Smart",
                "pret": "La cerere",
                "scor": 100,
                "cuvinte_cautate": "pachet business"
            }]
        elif fuzzy_contains(enterprise_keywords, interogare_lower):
            return [{
                "produs": "Pachet : Enterprise Complete",
                "pret": "La cerere",
                "scor": 100,
                "cuvinte_cautate": "pachet enterprise"
            }]
        elif fuzzy_contains(startup_keywords, interogare_lower):
            return [{
                "produs": "Pachet : Startup Light",
                "pret": "La cerere",
                "scor": 100,
                "cuvinte_cautate": "pachet startup"
            }]

        else:
            # Dacă e doar „pachet” fără cuvinte relevante fuzzy
            rezultate_directe = []
            for s in servicii:
                if "pachet" in s.lower():
                    rezultate_directe.append({
                        "produs": s,
                        "pret": "La cerere",
                        "scor": 100,
                        "cuvinte_cautate": "pachet"
                    })
            if rezultate_directe:
                return rezultate_directe
    elif fuzzy_contains(chatbot_messenger, interogare_lower , 90):
        # Dacă e o mențiune simplă de "mesenger", dar nu include și alte platforme
        if not any(p in interogare_lower for p in ["instagram", "telegram"]):
            return [{
                "produs": "Chatbot Simplu, integrat pe Mesenger",
                "pret": "La cerere",
                "scor": 100,
                "cuvinte_cautate": "chatbot messenger"
            }]
        
    # Fallback fuzzy general
    df_servicii = pd.DataFrame({
        "nume": servicii,
        "pret": ["La cerere"] * len(servicii)
    })


    rezultate = cauta_produs_inteligent_prioritate_lungime(interogare, df_servicii)
    print(rezultate)
    if rezultate:
        print("Cea mai bună potrivire/ potriviri (prioritate lungime expresie):")
        for r in rezultate:
            print(f"- {r['produs']} | {r['pret']} | scor: {r['scor']} (cuvinte căutate: '{r['cuvinte_cautate']}')")
    else:
        print("Niciun produs potrivit găsit.")
        rezultate = "NU"

    return rezultate


# servicii = [
#     'Landing Page One-Page', 'Site Simplu (3–5 pagini)', 'Site Complex Multilingv (>5 pagini)',
#     'Magazin Online (E-commerce)', 'Creare Logo Profesional', 'Maiou cu logo personalizat',
#     'Chipiu cu logo personalizat', 'Stilou cu logo personalizat', 'Carte de vizita personalizata',
#     'Agenda personalizata', 'Refresh Logo', 'Chatbot Simplu (Rule-Based)',
#     'Chatbot Simplu, integrat pe Instagram', 'Chatbot Simplu, integrat pe Mesenger',
#     'Chatbot Simplu, integrat pe Mesenger, Instagram, Telegram',
#     'Chatbot Inteligent cu GPT & CRM', 'Implementare & Configurare CRM', 'Mentenanță Lunara',
#     'Pachet : Startup Light', 'Pachet : Business Smart', 'Pachet : Enterprise Complete'
# ]


# interogare = "ma intereseaza si pachet"
# rezultate = function_check_product(interogare, servicii, "RO")






