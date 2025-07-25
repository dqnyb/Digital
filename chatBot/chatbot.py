from openai import OpenAI
from flask import Flask, request, jsonify , redirect, render_template , send_from_directory
from flask_cors import CORS
from openpyxl import Workbook, load_workbook
from datetime import datetime
from thefuzz import fuzz
from thefuzz import process
import pandas as pd
import os
import random
from dotenv import load_dotenv
import openai
import re
from servicii import function_check_product
from logic import extract_info
import unicodedata
from logic import extract_servicii_dict
from email_validator import validate_email, EmailNotValidError
import requests


app = Flask(__name__)
CORS(app)

load_dotenv()

TOKEN = os.getenv("HUBSPOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM = os.getenv("TELEGRAM_API_KEY")
CHAT_ID = os.getenv("CHAT_ID")

HUBSPOT_TOKEN = f"Bearer {TOKEN}"



# Pentru acest proiect am lăsat cheia publică (pentru a fi testată mai repede), dar desigur că nu se face așa!
# Aș fi folosit client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) și aș fi dat export în env la key: export OPENAI_API_KEY="sk-..."

client = OpenAI(
    api_key=f"{OPENAI_API_KEY}",  # pune aici cheia ta reală!
)
df = pd.read_excel('chatBot/digitalgrow.xlsx')
categorii = df['SERVICE']
categorii_unice = list(dict.fromkeys(categorii.dropna().astype(str)))
preferinte = {}
preferinte["pret"] = ""
preferinte["BUDGET"] = ""
preferinte["Nume_Prenume"] = ""
preferinte["Numar_Telefon"] = ""
preferinte["Serviciul_Ales"] = ""
preferinte["Limba_Serviciului"] = ""
preferinte["Preferintele_Utilizatorului_Cautare"] = ""

preferinte["Pret_MD"] = ""
preferinte["Pret_UE"] = ""
def log_message(sender, message):
    # Creează calea absolută către folderul logs ! Pentru a salva log-urile in excel !
    base_dir = os.path.expanduser("../logs")
    os.makedirs(base_dir, exist_ok=True)
    file_path = os.path.join(base_dir, "chat_log1.xlsx")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = {"Timestamp": timestamp, "Sender": sender, "Message": message}

    try:
        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df = pd.DataFrame([new_row])

        df.to_excel(file_path, index=False)
        print(f"[{timestamp}] [LOGGED] {sender}: {message}")
    except Exception as e:
        print(f"[EROARE] Logarea a eșuat: {e}")

def is_fuzzy_comanda(user_text, threshold=90):

    comanda_keywords = [
        # română
        "comand", "cumpăr", "achiziționez", "trimit factură", "factura", "plătesc", "finalizez",
        "trimit date", "comand", "cumpăr", "pregătiți comanda", "ofertă pentru", "cerere ofertă",
        "cât costă x bucăți", "preț 50 mp", "livrare comandă", "plată", "comanda", "comanda" ,"curier","achizitionez",
        
        # rusă (litere chirilice, intenție clară de comandă)
        "заказ", "купить", "купить", "покупка", "покупаю", "оплата", "оформить заказ", "счет", "выставите счет",
        "отправьте счет", "приобрести", "доставку", "плачу", "готов оплатить", "оплатить", "сделать заказ"
    ]
        
    user_text = user_text.lower()
    words = user_text.split()

    for keyword in comanda_keywords:
        for word in words:
            if fuzz.token_set_ratio(user_text, keyword) >= threshold:
                return True
        # verificăm și fraze întregi
        if fuzz.partial_ratio(user_text, keyword) >= threshold:
            return True
    return False


def is_fuzzy_preferinte(user_text, threshold=85):
    preferinte_keywords = [
        "preferințe", "preferinte", "nevoi", "personalizat", "personalizate", "cerințe", 
        "criterii", "criterii", "criteriu", "potrivit", "ajutor alegere", "vreau ceva pentru mine", 
        "selectare", "în funcție de", "ajută-mă să aleg", "bazat pe nevoi",
        "prefrinte", "prefferinte", "preferintze", "aleg ceva", "ce mi se potrivește",
        "custom", "tailored", "personalized", "match my needs", "fit for me", "select based on"
    ]
    
    user_text = user_text.lower()
    words = user_text.split()
    
    for keyword in preferinte_keywords:
        for word in words:
            if fuzz.token_set_ratio(user_text, keyword) >= threshold:
                return True
        if fuzz.partial_ratio(user_text, keyword) >= threshold:
            return True
    return False
    

def check_interest_pref(interest):
    print(interest)

    if is_fuzzy_preferinte(interest):
        return "preferinte"
    
    if is_fuzzy_comanda(interest):
        return "comandă"

    interests_prompt = (
        "Analizează mesajul utilizatorului pentru a identifica intenția exactă în funcție de următoarele categorii detaliate:\n\n"

        "1. produs_informații – când mesajul arată interes, curiozitate sau cerere de informații despre servicii, chiar dacă este vag. Se clasifică aici:\n"
        "- Orice interes exprimat despre:\n"
        "  - Website-uri: Landing Page, Site Simplu, Site Complex Multilingv, Magazin Online\n"
        "  - Branding: Creare Logo Profesional, Refresh Logo\n"
        "  - Produse promoționale: Maiou, Chipiu, Stilou, Carte de vizită, Agendă\n"
        "  - Chatbot: Rule-Based, Instagram, Messenger, Telegram, GPT\n"
        "  - CRM, mentenanță, pachete (Startup Light, Business Smart, Enterprise Complete)\n"
        "- Cereri generale de tipul:\n"
        "  - 'Ce servicii aveți?'\n"
        "  - 'Aș vrea ceva pentru branding'\n"
        "  - 'Vreau un chatbot'\n"
        "  - 'Trimiteți lista de oferte'\n"
        "  - 'Ce opțiuni aveți pentru CRM?'\n"
        "  - 'Cât costă un site?' (dacă nu cere mai multe bucăți)\n"
        "  - 'Vreau să văd portofoliul'\n"
        "- Chiar și mesaje vagi precum: 'servicii?', 'ofertă?', 'branding', 'chatbot GPT'\n\n"

        "2. comandă - DOAR când există o intenție clar exprimată de achiziție sau colaborare:\n"
        "- Verbe explicite: 'vreau să comand', 'vreau să achiziționez', 'cumpăr', 'să colaborăm', 'să lucrăm împreună', 'factura', 'plătesc', 'să începem'\n"
        "- Mesaje cu număr de bucăți/cerere concretă: 'Vreau 50 cărți de vizită', 'Cât costă 2 landing page-uri?'\n"
        "- Cerere de contract, factură, început de proiect: 'Trimiteți contractul', 'Cum procedăm?', 'Începem cu pachetul Business Smart'\n\n"

        "3. altceva - doar pentru:\n"
        "- Saluturi fără context ('salut', 'bună ziua')\n"
        "- Mulțumiri fără alte informații\n"
        "- Glume, comentarii irelevante, spam\n"
        "- Mesaje fără legătură cu serviciile sau comenzile\n\n"

        "REGULI IMPORTANTE:\n"
        "- Orice interes exprimat despre serviciile tale => produs_informații\n"
        "- Orice ambiguitate => produs_informații (mai bine fals pozitiv decât să pierzi un lead)\n"
        "- Doar când există formulare clare de achiziție/comandă => clasifici ca 'comandă'\n"
        "- Verbe precum „vreau”, „aș dori” NU înseamnă 'comandă' dacă nu sunt urmate de acțiune concretă (comand, colaborez, achiziționez, plătesc, etc.)\n\n"

        "EXEMPLE CLASIFICATE:\n"
        "'Ce chatboturi aveți?' => produs_informații\n"
        "'Aș vrea ceva pentru branding' => produs_informații\n"
        "'Vreau pachetul Business Smart' => comandă\n"
        "'Trimiteți-mi factura pentru chatbot GPT' => comandă\n"
        "'Bună, salut' => altceva\n\n"

        f"Mesaj de analizat: \"{interest}\"\n\n"
        "Răspunde STRICT cu unul dintre tag-uri: produs_informații, comandă, altceva. Fără explicații suplimentare."
    )

    messages = [{"role": "system", "content": interests_prompt}]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip().lower()

def check_interest(interest):
    print(interest)
    if is_fuzzy_comanda(interest):
        return "comandă"

    interests_prompt = (
        "Analizează mesajul utilizatorului pentru a identifica intenția exactă în funcție de următoarele categorii detaliate:\n\n"

        "1. produs_informații – când mesajul arată interes, curiozitate sau cerere de informații despre servicii, chiar dacă este vag. Se clasifică aici:\n"
        "- Orice interes exprimat despre:\n"
        "  - Website-uri: Landing Page, Site Simplu, Site Complex Multilingv, Magazin Online\n"
        "  - Branding: Creare Logo Profesional, Refresh Logo\n"
        "  - Produse promoționale: Maiou, Chipiu, Stilou, Carte de vizită, Agendă\n"
        "  - Chatbot: Rule-Based, Instagram, Messenger, Telegram, GPT\n"
        "  - CRM, mentenanță, pachete (Startup Light, Business Smart, Enterprise Complete)\n"
        "- Cereri generale de tipul:\n"
        "  - 'Ce servicii aveți?'\n"
        "  - 'Aș vrea ceva pentru branding'\n"
        "  - 'Vreau un chatbot'\n"
        "  - 'Trimiteți lista de oferte'\n"
        "  - 'Ce opțiuni aveți pentru CRM?'\n"
        "  - 'Cât costă un site?' (dacă nu cere mai multe bucăți)\n"
        "  - 'Vreau să văd portofoliul'\n"
        "- Chiar și mesaje vagi precum: 'servicii?', 'ofertă?', 'branding', 'chatbot GPT'\n\n"

        "2. comandă - DOAR când există o intenție clar exprimată de achiziție sau colaborare:\n"
        "- Verbe explicite: 'vreau să comand', 'vreau să achiziționez', 'cumpăr', 'să colaborăm', 'să lucrăm împreună', 'factura', 'plătesc', 'să începem'\n"
        "- Mesaje cu număr de bucăți/cerere concretă: 'Vreau 50 cărți de vizită', 'Cât costă 2 landing page-uri?'\n"
        "- Cerere de contract, factură, început de proiect: 'Trimiteți contractul', 'Cum procedăm?', 'Începem cu pachetul Business Smart'\n\n"

        "3. altceva - doar pentru:\n"
        "- Saluturi fără context ('salut', 'bună ziua')\n"
        "- Mulțumiri fără alte informații\n"
        "- Glume, comentarii irelevante, spam\n"
        "- Mesaje fără legătură cu serviciile sau comenzile\n\n"

        "REGULI IMPORTANTE:\n"
        "- Orice interes exprimat despre serviciile tale => produs_informații\n"
        "- Orice ambiguitate => produs_informații (mai bine fals pozitiv decât să pierzi un lead)\n"
        "- Doar când există formulare clare de achiziție/comandă => clasifici ca 'comandă'\n"
        "- Verbe precum „vreau”, „aș dori” NU înseamnă 'comandă' dacă nu sunt urmate de acțiune concretă (comand, colaborez, achiziționez, plătesc, etc.)\n\n"

        "EXEMPLE CLASIFICATE:\n"
        "'Ce chatboturi aveți?' => produs_informații\n"
        "'Aș vrea ceva pentru branding' => produs_informații\n"
        "'Vreau pachetul Business Smart' => comandă\n"
        "'Trimiteți-mi factura pentru chatbot GPT' => comandă\n"
        "'Bună, salut' => altceva\n\n"

        f"Mesaj de analizat: \"{interest}\"\n\n"
        "Răspunde STRICT cu unul dintre tag-uri: produs_informații, comandă, altceva. Fără explicații suplimentare."
    )

    messages = [{"role": "system", "content": interests_prompt}]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content.strip().lower()



# def fuzzy_check_category(user_interest, categorii_unice, threshold=70):

#     best_match, best_score = process.extractOne(user_interest, categorii_unice, scorer=fuzz.token_set_ratio)
#     print("------------------------------------------------")
#     if best_score >= threshold:
#         print("best match = " ,best_match)
#         return best_match

#     # Dacă nu găsește potriviri bune, încearcă să compari fiecare cuvânt din user_interest separat
#     words = user_interest.split()
#     for word in words:
#         best_match, best_score = process.extractOne(word, categorii_unice, scorer=fuzz.token_set_ratio)
#         if best_score >= threshold:
#             return best_match

#     # Nu s-a găsit nimic relevant
#     return "NU"



# def smart_category_prompt(user_interest, categorii_unice):
#     prompt = (
#         "Având în vedere lista de categorii:\n"
#         f"{', '.join(categorii_unice)}\n"
#         f"Utilizatorul a spus: '{user_interest}'\n"
#         "Sugerează cea mai potrivită categorie dintre lista de mai sus. "
#         "Răspunde doar cu numele categoriei, fără alte explicații. "
#         "Dacă niciuna nu se potrivește, răspunde cu NU."
#     )
#     messages = [{"role": "system", "content": prompt}]
#     response = ask_with_ai(messages).strip()

#     if not response or response.upper() == "NU":
#         return "NU"
    
#     if response not in categorii_unice:
#         return "NU"

#     return response


# def check_and_get_category(user_interest, categorii_unice, threshold=70):
#     fuzzy_result = fuzzy_check_category(user_interest, categorii_unice, threshold)

#     if fuzzy_result != "NU":
#         return fuzzy_result

#     ai_result = smart_category_prompt(user_interest, categorii_unice)
#     return ai_result


def genereaza_prompt_produse(rezultat, categorie, language_saved):
    if not rezultat:
        if language_saved == "RO":
            return "⚠️ Nu am identificat servicii relevante în categoria selectată."
        else:
            return "⚠️ Не удалось найти подходящие услуги в выбранной категории."

    lista_formatata = ""
    for idx, serv in enumerate(rezultat, 1):
        nume = serv['produs'].replace("**", "")
        pret = serv['pret']
        lista_formatata += f"{idx}. <strong>{nume}</strong><br />"

    if language_saved == "RO":
        prompt = (
            f"Am identificat câteva servicii relevante în urma cererii tale:<br /><br />"
            f"{lista_formatata}<br />"
            "Te rog să alegi <strong>exact denumirea serviciului dorit</strong> pentru a continua configurarea."
        )
    else:
        prompt = (
            "По вашему запросу найдены следующие релевантные услуги:<br /><br />"
            f"{lista_formatata}<br />"
            "Пожалуйста, укажите <strong>точное название нужной услуги</strong>, чтобы мы могли продолжить."
        )

    return prompt

def check_response(message):
    msg = message.lower()

    general_keywords = ["general", "informatii", "prezentare", "descriere", "detalii generale"]
    preferinte_keywords = ["preferinte", "personalizat", "nevoi", "ajutor", "alegere", "criterii"]

    general_score = max([fuzz.partial_ratio(msg, kw) for kw in general_keywords])
    preferinte_score = max([fuzz.partial_ratio(msg, kw) for kw in preferinte_keywords])

    if general_score > preferinte_score and general_score > 70:
        return "general"
    elif preferinte_score > general_score and preferinte_score > 70:
        return "preferinte"
    else:
        print("22222222")
        user_msg = f"""
        Clasifică intenția utilizatorului în UNA dintre cele trei opțiuni:
        - general → dacă vrea informații generale despre servicii
        - preferinte → dacă vrea un serviciu personalizat, în funcție de nevoi
        - altceva → dacă mesajul nu e relevant pentru clasificare , daca e o intrebare sau in general nu este legat de servicii IT

        Mesaj: "{message}"

        Răspunde DOAR cu un singur cuvânt: general, preferinte sau altceva.
        """
        messages = [
            {"role": "user", "content": user_msg}
        ]

        response = ask_with_ai(messages).strip().lower()
        
        # fallback în caz de răspuns greșit
        if response not in ["general", "preferinte", "altceva"]:
            return "altceva"
        
        return response
    


@app.route("/start", methods=["GET"])
def start():

    ask_name = (
        '👋 <strong style="font-size: 12;">Bun venit la <span style="color: #9333ea; text-shadow: 0 0 5px #d8b4fe, 0 0 10px #9333ea;">DigitalGrow</span>!</strong> 😊<br><br>'
        f"Te pot ajuta cu informații despre <strong>serviciile disponibile</strong> sau poate ești gata să <strong>achiziționezi unul</strong>? 💼✨<br>"
    )

    return jsonify({"ask_name": ask_name})

def build_service_prompt(categorii_unice):
    emoji_list = [
        "💼", "🧠", "📱", "💻", "🛠️", "🎨", "🚀", "🧰", "📈", "📊", "🔧",
        "🖥️", "📦", "🧾", "🌐", "📣", "🤖", "🧑‍💻", "📇", "🗂️", "🖌️", "💡", "📍", "🆕"
    ]
    
    intro = (
        "Îți pot oferi o gamă variată de servicii IT specializate. <br><br>"
        "Te rog alege serviciul dorit din lista de mai jos și răspunde cu <strong>denumirea exactă</strong>.<br>\n\n"
        "<em>(Apasă sau scrie exact denumirea serviciului pentru a continua)</em><br><br>\n\n"
    )
    
    service_lines = []
    used_emojis = set()
    for categorie in categorii_unice:
        emoji = random.choice(emoji_list)
        
        # Evită repetițiile excesive dacă e posibil
        while emoji in used_emojis and len(used_emojis) < len(emoji_list):
            emoji = random.choice(emoji_list)
        used_emojis.add(emoji)
        
        line = f"{emoji} <strong>{categorie}</strong>"
        service_lines.append(line)
    
    prompt = intro + "<br>".join(service_lines)
    return prompt

def build_general_or_personal_prompt():
    prompt = (
        "📌 Cum ai dori să continuăm?<br><br>"
        "🔍 Ai vrea să afli <strong>informații generale</strong> despre serviciile noastre?<br>"
        "🎯 Preferi să alegem un serviciu în funcție de <strong> nevoile și preferințele </strong> tale?<br><br>"
        "✍️ Te rugăm să scrii: <strong>general</strong> sau <strong>preferinte</strong> pentru a merge mai departe."
    )
    return prompt

def build_service_prompt_2(categorii_unice):
    emoji_list = [
        "💼", "🧠", "📱", "💻", "🛠️", "🎨", "🚀", "🧰", "📈", "📊", "🔧",
        "🖥️", "📦", "🧾", "🌐", "📣", "🤖", "🧑‍💻", "📇", "🗂️", "🖌️", "💡", "📍", "🆕"
    ]
    
    intro = (
        "Te rog alege serviciul dorit din lista de mai jos și răspunde cu <strong>denumirea exactă</strong> : <br><br>"
    )
    
    service_lines = []
    used_emojis = set()
    for categorie in categorii_unice:
        emoji = random.choice(emoji_list)
        
        # Evită repetițiile excesive dacă e posibil
        while emoji in used_emojis and len(used_emojis) < len(emoji_list):
            emoji = random.choice(emoji_list)
        used_emojis.add(emoji)
        
        line = f"{emoji} <strong>{categorie}</strong>"
        service_lines.append(line)
    
    prompt = intro + "<br>".join(service_lines)
    return prompt


def check_budget(user_response: str) -> str:

    raw_numbers = re.findall(r"\d[\d\s]*\d|\d+", user_response)

    cleaned_numbers = []
    for num in raw_numbers:
        # Elimină spațiile din număr (ex: "50 000" → "50000")
        cleaned = num.replace(" ", "")
        if cleaned.isdigit():
            cleaned_numbers.append(int(cleaned))

    if cleaned_numbers:
        return str(max(cleaned_numbers))

    prompt = (
        f"Utilizatorul a spus: \"{user_response}\".\n"
        "Scop: Extrage o valoare numerică aproximativă exprimată în text ca buget (ex: 1200, 5000, 25000).\n\n"
        "Reguli:\n"
        "- Dacă sunt mai multe numere, returnează cel mai relevant (suma principală).\n"
        "- Dacă este exprimat doar în cuvinte (ex: „buget mare”, „peste o mie”), transformă-l într-un număr estimativ (ex: 10000).\n"
        "- Dacă nu există nicio valoare estimabilă, răspunde cu: NONE.\n\n"
        "Exemple:\n"
        "\"cam 3000\" → 3000\n"
        "\"între 5000 și 7000\" → 6000\n"
        "\"buget mare\" → 10000\n"
        "\"приблизительно 10000\" → 10000\n"
        "\"до 2000\" → 2000\n"
        "\"не știu\" → NONE\n"
        "\"depinde\" → NONE\n"
        "\"vreau doar să aflu\" → NONE\n"
    )

    messages = [
        {"role": "system", "content": "Extrage doar un număr (fără text). Dacă nu e clar, răspunde cu NONE."},
        {"role": "user", "content": prompt}
    ]

    try:
        answer = ask_with_ai(messages, temperature=0, max_tokens=10)
        answer = answer.strip().upper()

        if answer != "NONE":
            return answer
        else:
            return "NONE"
    except Exception as e:
        print(f"[EROARE] check_budget failed: {e}")
        return "NONE"


@app.route("/interests", methods=["POST"])
def interests():
    user_data = request.get_json()
    name = user_data.get("name", "prieten")

    check = check_interest(name)
    if check == "produs_informații":
        # reply = build_service_prompt(categorii_unice)
        reply = build_general_or_personal_prompt()

    elif check == "comandă":

        mesaj = (
            "🎉 Mǎ bucur că vrei să plasezi o comandă!<br><br>"
            "📋 Hai să parcurgem împreună câțiva pași simpli pentru a înregistra comanda cu succes. 🚀<br><br>"
        )

        mesaj1 = build_service_prompt_2(categorii_unice)
        mesaj = mesaj + mesaj1
                
        return jsonify({"ask_interests": mesaj})
    else:
        print(name)
        prompt = (
            f"Utilizatorul a scris : '{name}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )
        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj += (
            "<br><br>❓ Te rugăm să ne spui dacă:<br>"
            "👉 vrei să <strong>afli mai multe informații</strong> despre serviciu<br>"
            "🛒 sau vrei să <strong>faci o comandă</strong> direct.<br><br>"
            )
        reply = mesaj

    return jsonify({"ask_interests": reply})


@app.route("/criteria", methods=["POST"])
def criteria():
    user_data = request.get_json()
    name = user_data.get("name", "prieten")
    message = user_data.get("message", "")
    response = check_response(message)
    print("response = ", response)
    if response == "general":
        # reply = "general"
        reply = build_service_prompt(categorii_unice)
    elif response == "preferinte":
            reply = """
            💰 <strong>Haide să alegem un buget potrivit pentru serviciul dorit!</strong><br><br>
            Alege una dintre opțiunile de mai jos, sau scrie un buget estimativ dacă ai altă preferință:<br><br>
            🔹 <strong>10 000 MDL</strong> – Proiect simplu, ideal pentru un început clar și eficient<br>
            🔸 <strong>20 000 MDL</strong> – Echilibru între funcționalitate și personalizare<br>
            🌟 <strong>50 000 MDL+</strong> – Soluții avansate, complete, cu funcții extinse și design premium<br><br>
            ✍️ <em>Ne poți scrie direct o altă sumă dacă ai un buget diferit în minte!</em>
            """
    else:
        prompt = (
            f"Utilizatorul a scris : '{message}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )
        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj += (
            "<br><br>✍️ Te rugăm să scrii: <strong>general</strong> sau <strong>preferinte</strong> pentru a merge mai departe."  
        )
        reply = mesaj
    return jsonify({"message": reply})


@app.route("/budget", methods=["POST"])
def budget():
    data = request.json
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")
    budget_ = check_budget(message)
    print("budget_ = ", budget_)
    if budget_ == "NONE":
        prompt = (
            f"Utilizatorul a scris categoria: '{message}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )
        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj += (
            "<br><br>💬 Apropo, ca să pot veni cu sugestii potrivite, îmi poți spune cam ce buget ai în minte? (în MDL)"
            "<br>💸 <strong>&lt;2000 MDL</strong> – buget mic<br>"
            "💶 <strong>2000–10 000 MDL</strong> – buget mediu<br>"
            "💰 <strong>10 000–25 000 MDL</strong> – buget generos<br>"
            "💎 <strong>50 000+ MDL</strong> – soluții avansate<br>"
            "✍️ Sau scrie pur și simplu suma estimativă."
        )
        return jsonify({"message": mesaj})
    else:
        preferinte["BUDGET"] = budget_
        mesaj = (
            f"✅ Am notat bugetul tău: <strong>{budget_} MDL</strong>.<br><br>"
            "🌐 În ce limbă ai prefera să fie oferit serviciul?<br><br>"
            "🇷🇴 <strong>Română</strong> – comunicare completă în limba română<br>"
            "🇷🇺 <strong>Русский</strong> – обслуживание на русском языке<br>"
            "🇬🇧 <strong>English</strong> – full service in English<br>"
            "🌍 <strong>Multilingv</strong> – combinăm limbile după preferință<br><br>"
            "✍️ Te rog scrie limba dorită sau alege <strong>multilingv</strong> dacă dorești flexibilitate."
        )
        return jsonify({"message": mesaj})


def normalize_text(text):
    # Fără diacritice + lowercase
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower()


def check_response_comanda(user_message):
    prompt = (
        f"Utilizatorul a spus: '{user_message}'\n\n"
        "Clasifică mesajul utilizatorului într-una dintre următoarele categorii, răspunzând cu un singur cuvânt:\n\n"
        "- NU: dacă mesajul exprimă o refuzare, o ezitare sau o lipsă de interes. "
        "Exemple: 'Nu', 'Nu acum', 'Nu sunt sigur', 'Mai târziu', 'Nu am comandat', 'Nu am mai comandat', 'Nu am comandat dar as vrea' etc.\n\n"
        "- DA: dacă mesajul exprimă o intenție clară și pozitivă, cum ar fi o confirmare, o dorință de a merge mai departe, un interes real sau dacă utilizatorul afirmă că a mai comandat de la noi, chiar dacă nu spune explicit că dorește din nou. "
        "Exemple: 'Da', 'Sigur', 'Aș dori', 'Sunt interesat', 'Vreau acel produs', 'Desigur', 'Perfect', 'sunt curios', 'am mai avut comandă', 'am mai comandat de la voi', etc.\n\n"
        "- ALTCEVA: dacă mesajul nu se încadrează în niciuna dintre categoriile de mai sus, de exemplu dacă utilizatorul pune o întrebare nespecifică, schimbă subiectul sau oferă informații fără legătură cu decizia, comanda sau interesul față de produs.\n\n"
    )
    messages = [{"role": "system", "content": prompt}]
    result = ask_with_ai(messages).strip().upper()
    return result

def check_preference_language(message: str) -> str:

    msg = message.lower()
    language_keywords = {
        "romana": [
            "romana", "română", "limba română", "in romana" , "româna", "ромынский", "romanian", "limba romana"
        ],
        "rusa": [
            "rusa", "rusă", "limba rusă", "rusește", "русский", "на русском", "по русски", "russian", "rusă"
        ],
        "engleza": [
            "engleza", "engleză", "limba engleză", "englește", "english", "angla", "in engleza", "eng", "английский", "limba engleza"
        ],
        "multilingv": [
            "multilingv", "mai multe limbi", "toate limbile", "combinat", "flexibil", "multi-language", "multilanguage", 
            "multilingua", "multi limbi", "mix limbi", "multilimba", "orice limba", "indiferent de limba", "orice limbă", 
            "на любом языке", "any language", "languages combined"
        ]
    }

    normalized = normalize_text(message)
    tokens = re.findall(r'\b\w+\b', normalized)

    for lang, keywords in language_keywords.items():
        for kw in keywords:
            kw_norm = normalize_text(kw)
            if kw_norm in tokens or kw_norm in normalized:
                return lang 

    # Fuzzy matching
    best_match = "necunoscut"
    best_score = 0
    for lang, keywords in language_keywords.items():
        for kw in keywords:
            print("kw = ", kw)
            score = fuzz.partial_ratio(msg, kw)
            print("score = ", score)
            if score > best_score:
                best_score = score
                best_match = lang

    if best_score > 85:
        print("best_match = ", best_match)
        return best_match
    else:
        return "necunoscut"


@app.route("/preference_language", methods=["POST"])
def preference_language():
    data = request.json
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")
    preference_language = check_preference_language(message)

    if preference_language == "necunoscut":
        prompt = (
            f"Utilizatorul a scris categoria: '{message}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )
        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj += (
            "<br><br>🌍 <strong>Ca să-ți ofer informațiile cât mai potrivit, îmi poți spune în ce limbă preferi să fie serviciul?</strong><br><br>"
            "🟡 <strong>Romana</strong> – limba română<br>"
            "🔵 <strong>Rusa</strong> – русский язык<br>"
            "🟢 <strong>Engleza</strong> – english<br>"
            "🌐 <strong>Multilingv</strong> – mai multe limbi combinate, după preferințe"
        )
        return jsonify({"message": mesaj})
    else:
        preferinte["Limba_Serviciului"] = preference_language
        reply = (
            "💡 <strong>Super! Spune-mi, te rog, ce funcționalități ți-ar plăcea să includă serviciul?</strong><br><br>"
            "📌 De exemplu: <em>„Platformă de vânzări online cu plată prin card”</em> sau <em>„Pagină de prezentare pentru un eveniment”</em> , <em>„Site cu ChatBot Inteligent + CRM”</em> etc.<br><br>"
            "✍️ Poți scrie liber ce ai în minte, iar noi îți vom propune opțiuni potrivite."
        )
        return jsonify({"message": reply})

def check_functionalities_with_ai(message, all_descriptions):
    descriptions_text = "\n\n".join(all_descriptions)
    prompt = f"""
    Ești un consultant digital care ajută clienții să găsească serviciile potrivite dintr-o listă de oferte. Ai mai jos o listă de servicii digitale disponibile, fiecare cu nume și descriere. 

    Un utilizator a trimis acest mesaj:
    "{message}"

    Scopul tău este să identifici, din lista de mai jos:
    1. Serviciile care se potrivesc DIRECT cu ceea ce spune utilizatorul (funcționalități, dorințe, scopuri).
    2. Dacă aceste funcționalități sunt ACOPERITE (parțial sau complet) de un pachet, include în rezultat DOAR UN SINGUR PACHET relevant.
    - Alege pachetul care acoperă cele mai multe dintre funcționalitățile potrivite.
    - Nu include pachete care nu au legătură cu cererea utilizatorului.
    - Nu include mai mult de un pachet.

    🔒 REGULI IMPORTANTE:
    - Incearca mereu sa returnezei 2-3 servicii daca este posibil , daca nu returneaza cate trebuie
    - Nu returna pachete decât dacă acoperă CLAR funcționalitățile menționate.
    - Nu inventa funcționalități care nu există în lista de servicii.
    - NU returna nimic dacă potrivirea este vagă sau generală.
    - Fii selectiv și profesionist ca un vânzător real.

    📤 Outputul trebuie să fie:
    - O listă de nume de servicii separate prin `;` (fără ghilimele, explicații sau alte caractere).
    - Fără introduceri, concluzii sau text suplimentar.
    - Dacă nu identifici nimic relevant, returnează exact: `NONE`

    Serviciile disponibile:
    {descriptions_text}
    """
    messages = [{"role": "system", "content": prompt}]
    return ask_with_ai(messages)



def parse_pret(pret_str):
    # Extrage doar cifrele și returnează ca int (ex: '15 000' -> 15000)
    pret_str = str(pret_str)
    pret_clean = re.sub(r"[^\d]", "", pret_str)
    return int(pret_clean) if pret_clean else 0

def filtreaza_servicii_dupa_buget(servicii_dict, buget_str):
    buget = parse_pret(buget_str)
    rezultate = {}

    for nume_serviciu, detalii in servicii_dict.items():
        pret_md = parse_pret(detalii.get("pret_md", "0"))
        pret_ue = parse_pret(detalii.get("pret_ue", "0"))

        if pret_md <= buget and pret_ue <= buget:
            rezultate[nume_serviciu] = detalii

    return rezultate


@app.route("/functionalities", methods=["POST"])
def functionalities():
    data = request.json
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")
    preferinte["Preferintele_Utilizatorului_Cautare"] = message;
    servicii_dict = extract_servicii_dict()
    servicii_potrivite = filtreaza_servicii_dupa_buget(servicii_dict, preferinte["BUDGET"])
    length_servicii_potrivite_buget = len(servicii_potrivite)
    print("length_servicii_potrivite_buget = ", length_servicii_potrivite_buget)
    if length_servicii_potrivite_buget == 0:
        func = check_functionalities_with_ai(message, servicii_dict)

        if func == "NONE":
            prompt = (
                f"Utilizatorul a scris serviciul: '{message}'.\n\n"
                "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
                "Scrie un mesaj politicos, prietenos și natural, care:\n"
                "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
                "2. Mesajul să fie scurt, cald, empatic și prietenos. "
                "Nu mai mult de 2-3 propoziții.\n"
                "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
            )
            messages = [{"role": "system", "content": prompt}]
            mesaj = ask_with_ai(messages).strip()
            mesaj += (
                "<br><br>❗️ Din ce ai scris, nu am reușit să identific un serviciu potrivit pentru nevoia ta."
                "<br>💬 Te rog să-mi spui mai clar ce funcționalități ți-ar plăcea să aibă – de exemplu: <em>„platformă de vânzare produse online”, „site de prezentare cu 3-5 pagini”, „creare logo”</em> etc."
                "<br><br>🔍 Cu cât mai clar, cu atât mai ușor îți pot recomanda variante potrivite!"
            )
            return jsonify({"message": mesaj})
        else:
            if ";" in func:
                splited_func = func.split(";")
                print("splited_func = ", splited_func)
            elif "\n" in func:
                splited_func = func.split("\n")
            else:
                splited_func = ["Pachet : Business Smart" , "Site Complex Multilingv (>5 pagini)" , "Magazin Online (E-commerce)" ]
            mesaj = ""
            for i in splited_func:
                detalii = extract_info(i)
                
                if detalii:
                    descriere = detalii.get("descriere", "N/A")
                    beneficii = detalii.get("beneficii", "N/A")
                    pret_md = detalii.get("pret_md", "N/A")
                    pret_ue = detalii.get("pret_ue", "N/A")
                    pret_reducere = detalii.get("reducere", "N/A")

                    mesaj += (
                        f"✅ Iată toate detaliile despre <strong>{i}</strong> 🧩<br /><br />"
                        f"📌 <strong>Descriere:</strong><br />{descriere}<br /><br />"
                        f"🎯 <strong>Beneficii:</strong><br />{beneficii}<br /><br />"
                        f"💸 <strong>Prețuri:</strong><br />"
                        f"🇲🇩 Moldova: <strong>{pret_md} MDL</strong><br />"
                        f"🇪🇺 Uniunea Europeană: <strong>{pret_ue} MDL</strong><br /><br /><br>"
                        f"💸 Reducere : <strong>{pret_reducere} MDL</strong><br /><br /><br>"
                        f"<hr style='border: none; border-top: 1px solid #ccc; margin: 20px 0;'><br>"

                    )
            mesaj += (
                "❗️ <strong>Nu sunt servicii potrivite pentru bugetul ales , dar am gasit dupa functionalitatile alese</strong><br>"
            )

            mesaj += "<hr style='border: none; border-top: 1px solid #ccc; margin: 20px 0;'><br>"

            mesaj += "<br>💬 <em>Dorești să faci o comandă ? Raspunde cu <strong>DA</strong> sau <strong>NU</strong></em><br>"


    else:

        func = check_functionalities_with_ai(message, servicii_potrivite)
        print("func = ", func)
        # func += ("<br><br> Acestea sunt serviciile potrivite pentru bugetul + functionalitatile alese")
        # print("func ======= ", func)
        if func == "NONE":
            func = check_functionalities_with_ai(message, servicii_dict)
            if func == "NONE":
                prompt = (
                    f"Utilizatorul a scris serviciul: '{message}'.\n\n"
                    "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
                    "Scrie un mesaj politicos, prietenos și natural, care:\n"
                    "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
                    "2. Mesajul să fie scurt, cald, empatic și prietenos. "
                    "Nu mai mult de 2-3 propoziții.\n"
                    "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
                )
                messages = [{"role": "system", "content": prompt}]
                mesaj = ask_with_ai(messages).strip()
                mesaj += (
                    "<br><br>❗️ Din ce ai scris, nu am reușit să identific un serviciu potrivit pentru nevoia ta."
                    "<br>💬 Te rog să-mi spui mai clar ce funcționalități ți-ar plăcea să aibă – de exemplu: <em>„platformă de vânzare produse online”, „site de prezentare cu 3-5 pagini”, „creare logo”</em>."
                    "<br><br>🔍 Cu cât mai clar, cu atât mai ușor îți pot recomanda variante potrivite!"
                )
                return jsonify({"message": mesaj})
            else:
                if ";" in func:
                    splited_func = func.split(";")
                elif "\n" in func:
                    splited_func = func.split("\n")
                else:
                    splited_func = ["Pachet : Business Smart" , "Site Complex Multilingv (>5 pagini)" , "Magazin Online (E-commerce)"]

                mesaj = ""
                
                for i in splited_func:
                    detalii = extract_info(i)
                    
                    if detalii:
                        descriere = detalii.get("descriere", "N/A")
                        beneficii = detalii.get("beneficii", "N/A")
                        pret_md = detalii.get("pret_md", "N/A")
                        pret_ue = detalii.get("pret_ue", "N/A")
                        pret_reducere = detalii.get("reducere", "N/A")

                        mesaj += (
                            f"✅ Iată toate detaliile despre <strong>{i}</strong> 🧩<br /><br />"
                            f"📌 <strong>Descriere:</strong><br />{descriere}<br /><br />"
                            f"🎯 <strong>Beneficii:</strong><br />{beneficii}<br /><br />"
                            f"💸 <strong>Prețuri:</strong><br />"
                            f"🇲🇩 Moldova: <strong>{pret_md} MDL</strong><br />"
                            f"🇪🇺 Uniunea Europeană: <strong>{pret_ue} MDL</strong><br /><br />"
                            f"💸 Reducere : <strong>{pret_reducere} MDL</strong><br /><br /><br>"
                            f"<hr style='border: none; border-top: 1px solid #ccc; margin: 20px 0;'><br>"
                        )
                mesaj += (
                    "❗️ <strong>Nu sunt servicii potrivite pentru bugetul ales , dar am gasit dupa functionalitatile alese</strong><br>"
                )

                mesaj += "<hr style='border: none; border-top: 1px solid #ccc; margin: 20px 0;'><br>"

                mesaj += "<br>💬 <em>Dorești să faci o comandă ? Raspunde cu <strong>DA</strong> sau <strong>NU</strong></em><br>"

        else:
            
            if ";" in func:
                splited_func = func.split(";")
            elif "\n" in func:
                splited_func = func.split("\n")
            else:
                splited_func = ["Pachet : Business Smart" , "Site Complex Multilingv (>5 pagini)" , "Magazin Online (E-commerce)"]

            mesaj = ""
            for i in splited_func:
                detalii = extract_info(i)
                
                if detalii:
                    descriere = detalii.get("descriere", "N/A")
                    beneficii = detalii.get("beneficii", "N/A")
                    pret_md = detalii.get("pret_md", "N/A")
                    pret_ue = detalii.get("pret_ue", "N/A")
                    pret_reducere = detalii.get("reducere", "N/A")

                    mesaj += (
                        f"✅ Iată toate detaliile despre <strong>{i}</strong> 🧩<br /><br />"
                        f"📌 <strong>Descriere:</strong><br />{descriere}<br /><br />"
                        f"🎯 <strong>Beneficii:</strong><br />{beneficii}<br /><br />"
                        f"💸 <strong>Prețuri:</strong><br />"
                        f"🇲🇩 Moldova: <strong>{pret_md} MDL</strong><br />"
                        f"🇪🇺 Uniunea Europeană: <strong>{pret_ue} MDL</strong><br /><br />"
                        f"💸 Reducere : <strong>{pret_reducere} MDL</strong><br /><br /><br>"
                        f"<hr style='border: none; border-top: 1px solid #ccc; margin: 20px 0;'><br>"
                    )
            mesaj += (
            "❗️ <strong>Acestea sunt serviciile potrivite pentru bugetul + functionalitatile alese</strong><br>"
            )
            mesaj += "<hr style='border: none; border-top: 1px solid #ccc; margin: 20px 0;'><br>"

            mesaj += "<br>💬 <em>Dorești să faci o comandă ? Raspunde cu <strong>DA</strong> sau <strong>NU</strong></em><br>"
    

    return jsonify({"message": mesaj})



@app.route("/welcome", methods=["POST"])
def welcome():
    data = request.json
    name = data.get("name", "")
    interests = data.get("interests", "")

    prompt_verify = (
        f"Ai o listă de servicii valide: {categorii_unice}\n\n"
        f"Verifică dacă textul următor conține cel puțin un serviciu valid sau o denumire care seamănă suficient (similaritate mare) cu vreuna din serviciile valide.\n\n"
        f'Text de verificat: "{interests}"\n\n'
        f'Răspunde strict cu "DA" dacă există o potrivire validă sau asemănătoare, altfel răspunde cu "NU".'
    )
    messages = [{"role": "system", "content": prompt_verify}] 
    resp = ask_with_ai(messages , max_tokens=10)
    print("RASPUNS = ", resp)

    rezultat = function_check_product(interests , categorii_unice, "RO")
    print("rezultat = ", rezultat)

    if rezultat == "NU":
        lungime_rezultat = 0
    else:
        lungime_rezultat = len(rezultat)

    if lungime_rezultat == 1:
        produs = rezultat[0]['produs']
        print("rezultatul =", produs)
        detalii = extract_info(produs)
        
        if detalii:
            descriere = detalii.get("descriere", "N/A")
            beneficii = detalii.get("beneficii", "N/A")
            pret_md = detalii.get("pret_md", "N/A")
            pret_ue = detalii.get("pret_ue", "N/A")

            preferinte["Pret_MD"] = pret_md
            preferinte["Pret_UE"] = pret_ue
            pret_reducere = detalii.get("reducere", "N/A")

            mesaj = (
                f"✅ Am găsit serviciul tău! Iată toate detaliile despre <strong>{produs}</strong> 🧩<br /><br />"
                f"📌 <strong>Descriere:</strong><br />{descriere}<br /><br />"
                f"🎯 <strong>Beneficii:</strong><br />{beneficii}<br /><br />"
                f"💸 <strong>Prețuri:</strong><br />"
                f"🇲🇩 Moldova: <strong>{pret_md} MDL</strong><br />"
                f"🇪🇺 Uniunea Europeană: <strong>{pret_ue} MDL</strong><br /><br />"
                f"💸 Reducere : <strong>{pret_reducere} MDL</strong><br /><br /><br>"
                "🔄 Dacă vrei detalii despre un <strong>alt serviciu</strong> , să faci o <strong>comandă</strong> sau <strong>sa alegem după preferințe</strong> scrie-mi te rog! 😊"
            )

    elif lungime_rezultat > 1:
        reply = genereaza_prompt_produse(rezultat, resp, "RO")
        return jsonify({"message": reply})
    else:
        prompt = (
            f"Utilizatorul a scris categoria: '{interests}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )

        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        reply = build_service_prompt_2(categorii_unice)
        mesaj = mesaj + reply

        return jsonify({"message": mesaj})
        
        

    # categoria_aleasa = check_and_get_category(interests, categorii_unice)
    # print("categoria_aleasa = ", categoria_aleasa)

    # log_message("USER", interests)

    # welcome_msg = generate_welcome_message(name, interests)
    # log_message("AI BOT", welcome_msg)

    return jsonify({"message": mesaj})


@app.route("/chat", methods=["POST" , "GET"])
def chat():
    step = request.args.get('step')
    if step == 'feedback':
        return redirect('/feedback')
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")




    print("mmmmmm = ", message)

    prompt_verify = (
        f"Ai o listă de servicii valide: {categorii_unice}\n\n"
        f"Verifică dacă textul următor conține cel puțin un serviciu valid sau o denumire care seamănă suficient (similaritate mare) cu vreuna din serviciile valide.\n\n"
        f'Text de verificat: "{message}"\n\n'
        f'Răspunde strict cu "DA" dacă există o potrivire validă sau asemănătoare, altfel răspunde cu "NU".'
    )

    messages = [{"role": "system", "content": prompt_verify}] 
    resp = ask_with_ai(messages , max_tokens=10)

    if resp == "DA":
        rezultat = function_check_product(interests , categorii_unice, "RO")
        print("rezultat = ", rezultat)

        if rezultat == "NU":
            lungime_rezultat = 0
        else:
            lungime_rezultat = len(rezultat)

        if lungime_rezultat == 1:
            produs = rezultat[0]['produs']
            print("rezultatul =", produs)
            detalii = extract_info(produs)
            
            if detalii:
                descriere = detalii.get("descriere", "N/A")
                beneficii = detalii.get("beneficii", "N/A")
                pret_md = detalii.get("pret_md", "N/A")
                pret_ue = detalii.get("pret_ue", "N/A")

                preferinte["Pret_MD"] = pret_md
                preferinte["Pret_UE"] = pret_ue
                pret_reducere = detalii.get("reducere", "N/A")

                mesaj = (
                    f"✅ Am găsit serviciul tău! Iată toate detaliile despre <strong>{produs}</strong> 🧩<br /><br />"
                    f"📌 <strong>Descriere:</strong><br />{descriere}<br /><br />"
                    f"🎯 <strong>Beneficii:</strong><br />{beneficii}<br /><br />"
                    f"💸 <strong>Prețuri:</strong><br />"
                    f"🇲🇩 Moldova: <strong>{pret_md} MDL</strong><br />"
                    f"🇪🇺 Uniunea Europeană: <strong>{pret_ue} MDL</strong><br /><br />"
                    f"💸 Reducere : <strong>{pret_reducere} MDL</strong><br /><br /><br>"
                    "🔄 Dacă vrei detalii despre un <strong>alt serviciu</strong> , să faci o <strong>comandă</strong> sau <strong>sa alegem după preferințe</strong> scrie-mi te rog! 😊"
                )
            return jsonify({"message": mesaj})

        elif lungime_rezultat > 1:
            reply = genereaza_prompt_produse(rezultat, resp, "RO")
            return jsonify({"message": reply})
        else:
            prompt = (
                f"Utilizatorul a scris categoria: '{interests}'.\n\n"
                "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
                "Scrie un mesaj politicos, prietenos și natural, care:\n"
                "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
                "2. Mesajul să fie scurt, cald, empatic și prietenos. "
                "Nu mai mult de 2-3 propoziții.\n"
                "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
            )

            messages = [{"role": "system", "content": prompt}]
            mesaj = ask_with_ai(messages).strip()
            reply = build_service_prompt_2(categorii_unice)
            mesaj = mesaj + reply
            
            return jsonify({"message": mesaj})
    elif resp == "NU":
        check = check_interest_pref(message)
        print(check)
        if check == "produs_informații":
            reply = build_service_prompt(categorii_unice)
        elif check == "comandă":
            mesaj = (
                "🎉 Mǎ bucur că vrei să plasezi o comandă!<br><br>"
                "📋 Hai să parcurgem împreună câțiva pași simpli pentru a înregistra comanda cu succes. 🚀<br><br>"
            )

            mesaj1 = build_service_prompt_2(categorii_unice)
            reply = mesaj + mesaj1
        elif check == "preferinte":
            prompt_buget = """
            💰 <strong>Haide să alegem un buget potrivit pentru serviciul dorit!</strong><br><br>
            Alege una dintre opțiunile de mai jos, sau scrie un buget estimativ dacă ai altă preferință:<br><br>
            🔹 <strong>10 000 MDL</strong> – Proiect simplu, ideal pentru un început clar și eficient<br>
            🔸 <strong>20 000 MDL</strong> – Echilibru între funcționalitate și personalizare<br>
            🌟 <strong>50 000 MDL+</strong> – Soluții avansate, complete, cu funcții extinse și design premium<br><br>
            ✍️ <em>Ne poți scrie direct o altă sumă dacă ai un buget diferit în minte!</em>
            """
            return jsonify({"message": prompt_buget})
        else:
            print(message)
            prompt = (
                f"Utilizatorul a scris : '{message}'.\n\n"
                "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
                "Scrie un mesaj politicos, prietenos și natural, care:\n"
                "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
                "2. Mesajul să fie scurt, cald, empatic și prietenos. "
                "Nu mai mult de 2-3 propoziții.\n"
                "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
            )
            messages = [{"role": "system", "content": prompt}]
            mesaj = ask_with_ai(messages).strip()
            mesaj += (
                "<br><br>❓ Te rugăm să ne spui dacă:<br>"
                "&nbsp;&nbsp;🔍 <em>Vrei mai multe informații</em> despre serviciu<br>"
                "&nbsp;&nbsp;🛒 <em>Vrei să achiziționezi</em> un serviciu<br><br>"
                "&nbsp;&nbsp;🛒 <em>Vrei să alegem după preferințe</em><br><br>"
                )
            reply = mesaj

    return jsonify({"message": reply})

def check_surname_command_ro(command):
    prompt = f"""
    Ești un validator automat inteligent care răspunde STRICT cu "DA" sau "NU" dacă textul conține un nume complet valid de persoană, format din cel puțin două cuvinte consecutive (prenume + nume sau invers), indiferent dacă acestea sunt nume reale sau inventate.

    Reguli:
    0. Dacă textul este o întrebare, răspunde STRICT "NU".
    1. Acceptă orice combinație de două sau mai multe cuvinte consecutive ce pot forma un nume (nu trebuie să fie neapărat nume reale).
    2. Nu accepta secvențe care conțin emoji, cifre, simboluri (!, @, # etc.) sau abrevieri de tipul „a.”, „b.” etc.
    3. Cuvintele pot fi cu majuscule sau minuscule.
    4. NU accepta nume incomplete (doar un singur cuvânt), răspunsuri vagi sau întrebări.
    5. Răspunde STRICT cu "DA" sau "NU", fără alte explicații.

    Exemple valide (DA):
    - mă numesc ana mamaliga
    - numele meu este gigel beton
    - sunt violeta spartacus
    - brinza daniel
    - ion stan
    - elena cucurigu
    - florin soare
    - dan moldovan
    - da, mă cheamă andrei caramida

    Exemple invalide (NU):
    - daniel
    - popescu
    - 😊😊😊
    - 12345
    - cum te numești?
    - numele meu este ion!
    - mă numesc!
    - ion2 popescu
    - @maria ionescu
    - florin 😊 betișor

    Text de verificat:
    \"\"\"{command}\"\"\"

    Răspuns STRICT:
    """

    messages = [{"role": "system", "content": prompt}]

    response1 = ask_with_ai(messages, temperature=0.5, max_tokens=5).strip().upper()

    if response1 == "NU":
        # Reîncercare cu temperatură diferită pentru robustețe
        response1 = ask_with_ai(messages, temperature=0.2, max_tokens=5).strip().upper()

    return "DA" if response1 == "DA" else "NU"


@app.route("/comanda", methods=["POST"])
def comanda():
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")

    resp = check_response_comanda(message)
    print("resp = ", resp)


    if resp == "DA":
        mesaj = (
            "🎉 Mǎ bucur că vrei să plasezi o comandă!<br><br>"
            "📋 Hai să parcurgem împreună câțiva pași simpli pentru a înregistra comanda cu succes. 🚀<br><br>"
        )

        mesaj1 = build_service_prompt_2(categorii_unice)
        mesaj = mesaj + mesaj1

        # rezultat = function_check_product(interests , categorii_unice, "RO")
        # print("rezultat = ", rezultat)
                
        return jsonify({"message": mesaj})
    elif resp == "NU":
        mesaj = (
            "🙏 Îți mulțumim pentru răspuns! <br><br>"
            "🔄 Dacă vrei detalii despre un <strong>alt serviciu</strong> sau "
            "să faci o <strong>comandă</strong> "
            "scrie-mi te rog! 😊"
        )
        return jsonify({"message": mesaj})
    else:
        prompt = (
            f"Utilizatorul a scris : '{message}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )
        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj += "<br><br>💬 Nu mi-e clar dacă vrei să faci o comandă. Dacă da, te rog răspunde cu <strong>DA</strong>, iar dacă nu, scrie <strong>NU</strong>. 😊"
        return jsonify({"message": mesaj})



@app.route("/comanda_inceput", methods=["POST"])
def comanda_inceput():
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")

    rezultat = function_check_product(message , categorii_unice, "RO")
    print("rezultat = ", rezultat)
    if rezultat == "NU":
        lungime_rezultat = 0
    else:
        lungime_rezultat = len(rezultat)

    if lungime_rezultat == 1:
        produs = rezultat[0]['produs']
        print("rezultatul =", produs)
        detalii = extract_info(produs)
        preferinte["Serviciul_Ales"] = rezultat[0]['produs']
        if detalii:
            descriere = detalii.get("descriere", "N/A")
            beneficii = detalii.get("beneficii", "N/A")
            pret_md = detalii.get("pret_md", "N/A")
            pret_ue = detalii.get("pret_ue", "N/A")

            preferinte["Pret_MD"] = pret_md
            preferinte["Pret_UE"] = pret_ue
            pret_reducere = detalii.get("reducere", "N/A")

            mesaj = (
                f"✅ Iată toate detaliile despre <strong>{produs}</strong> 🧩<br /><br />"
                f"📌 <strong>Descriere:</strong><br />{descriere}<br /><br />"
                f"🎯 <strong>Beneficii:</strong><br />{beneficii}<br /><br />"
                f"💸 <strong>Prețuri:</strong><br />"
                f"🇲🇩 Moldova: <strong>{pret_md} MDL</strong><br />"
                f"🇪🇺 Uniunea Europeană: <strong>{pret_ue} MDL</strong><br /><br /><br>"
                f"💸 Reducere : <strong>{pret_reducere} MDL</strong><br /><br /><br>"
                "✅ <strong>Dacă dorești acest produs, confirmă cu DA</strong><br />"
                "❌ <strong>Dacă vrei să alegi altul, răspunde cu NU</strong>"
            )
            print("mesaj = ", mesaj)
            return jsonify({"message": mesaj})

    elif lungime_rezultat > 1:
        
        reply = genereaza_prompt_produse(rezultat, "OK", "RO")
        return jsonify({"message": reply})
    else:
        prompt = (
            f"Utilizatorul a scris categoria: '{interests}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )

        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj +="<br><br>"
        reply = build_service_prompt_2(categorii_unice)
        mesaj = mesaj + reply
    return jsonify({"message": mesaj})

@app.route("/afiseaza_produs", methods=["POST"])
def afiseaza_produs():
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")

    rezultat = function_check_product(message , categorii_unice, "RO")
    preferinte["Serviciul_Ales"] = rezultat[0]['produs']
    print("rezultat = ", rezultat)
    if rezultat == "NU":
        lungime_rezultat = 0
    else:
        lungime_rezultat = len(rezultat)

    if lungime_rezultat == 1:
        produs = rezultat[0]['produs']
        print("rezultatul =", produs)
        detalii = extract_info(produs)

        
        if detalii:
            descriere = detalii.get("descriere", "N/A")
            beneficii = detalii.get("beneficii", "N/A")
            pret_md = detalii.get("pret_md", "N/A")
            pret_ue = detalii.get("pret_ue", "N/A")
            preferinte["Pret_MD"] = pret_md
            preferinte["Pret_UE"] = pret_ue

            preferinte["Serviciul_Ales"] = produs
            pret_reducere = detalii.get("reducere", "N/A")
            
            mesaj = (
                f"✅ Iată toate detaliile despre <strong>{produs}</strong> 🧩<br /><br />"
                f"📌 <strong>Descriere:</strong><br />{descriere}<br /><br />"
                f"🎯 <strong>Beneficii:</strong><br />{beneficii}<br /><br />"
                f"💸 <strong>Prețuri:</strong><br />"
                f"🇲🇩 Moldova: <strong>{pret_md} MDL</strong><br />"
                f"🇪🇺 Uniunea Europeană: <strong>{pret_ue} MDL</strong><br /><br /><br>"
                f"💸 Reducere : <strong>{pret_reducere} MDL</strong><br /><br /><br>"
                "✅ <strong>Dacă dorești acest produs, confirmă cu DA</strong><br />"
                "❌ <strong>Dacă vrei să alegi altul, răspunde cu NU</strong>"
            )
            print("mesaj = ", mesaj)
            return jsonify({"message": mesaj})

    elif lungime_rezultat > 1:
        
        reply = genereaza_prompt_produse(rezultat, "OK", "RO")
        return jsonify({"message": reply})
    else:
        prompt = (
            f"Utilizatorul a scris categoria: '{interests}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )

        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj +="<br><br>"
        reply = build_service_prompt_2(categorii_unice)
        mesaj = mesaj + reply

    return jsonify({"message": mesaj})

@app.route("/confirma_produs", methods=["POST"])
def confirma_produs():
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")
    resp = check_response_comanda(message)
    if resp == "DA":
        mesaj = (
            "✅ Serviciul a fost salvat cu succes!<br><br>"
            "📝 Pentru a continua comanda cât mai rapid, te rog scrie <strong>numele și prenumele</strong> "
        )
        return jsonify({"message": mesaj})
    elif resp == "NU":
        mesaj = build_service_prompt_2(categorii_unice)
        return jsonify({"message": mesaj})
    else:
        prompt = (
            f"Utilizatorul a scris categoria: '{interests}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )
        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj += (
            "<br><br>❓ Te rog spune-mi clar dacă alegi acest produs sau vrei să alegem altul.<br>"
            "Răspunde cu <strong>DA</strong> dacă dorești acest produs, sau <strong>NU</strong> dacă vrei să căutăm altceva. 😊"
        )
    return jsonify({"message": mesaj})

def extrage_nume_din_text(text):
    prompt = f"""
    Extrage doar numele complet (nume și prenume) din următorul text:
    "{text}"
    
    Returnează doar numele complet cu majuscula pentru ca este nume si prenume, fără explicații sau alte informații.
    """
    messages = [{"role": "system", "content": prompt}]

    response = ask_with_ai(messages , temperature=0.3 , max_tokens=50)

    return response

# @app.route("/comanda_verifica_daca_e_client", methods=["POST"])
# def comanda_etapa_nume_prenume():
#     data = request.get_json()
#     name = data.get("name", "")
#     interests = data.get("interests", "")
#     message = data.get("message", "")
#     # check_sur = check_surname_command_ro(message)

# @app.route("/ai_mai_comandat", methods=["POST"])
# def ai_mai_comandat():
#     data = request.get_json()
#     name = data.get("name", "")
#     interests = data.get("interests", "")
#     message = data.get("message", "")
#     resp = check_response_comanda(message)
#     if resp == "DA":
#         mesaj = (
#             "🤗 Ne bucurăm să te avem din nou alături și îți mulțumim că ești deja clientul nostru!<br><br>"
#             "📝 Pentru a continua comanda cât mai rapid, te rog scrie <strong>numele și prenumele</strong> "
#             "cu care ai făcut comenzile anterioare. Astfel putem verifica mai ușor istoricul tău. 🙌"
#         )
#         return jsonify({"message": mesaj})
#     elif resp == "NU":
        
#         return jsonify({"message": "nu a mai comandat"})
#     else:
#         return jsonify({"message": "altceva"})

@app.route("/check_name_surname", methods=["POST"])
def check_name_surname():
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")
    check_sur = check_surname_command_ro(message)
    if check_sur == "DA":
        nume_prenume_corect = extrage_nume_din_text(message)
        preferinte["Nume_Prenume"] = nume_prenume_corect
        print("nume_prenume_corect = ", nume_prenume_corect)
        preferinte["Nume_Prenume"] = nume_prenume_corect
        reply = (
            "😊 Mulțumim! Ai un nume frumos! 💬<br>"
            "📞 Te rugăm să ne lași un <strong>număr de telefon</strong> pentru a putea <strong>inregistra comanda</strong><br><br>"
            "Te rugăm să te asiguri că numărul începe cu <strong>0</strong> sau <strong>+373</strong>. ✅"
        )
    else:
        prompt_ai = (
            f"Nu te saluta niciodata pentru ca deja avem o discutie.\n"
            f"Acționează ca un asistent prietenos și politicos.\n"
            f"Răspunde la următorul mesaj ca și cum ai fi un agent uman care vrea să ajute clientul.\n"
            f"Răspunsul trebuie să fie cald, clar și la obiect. "
            f'Mesajul clientului: "{message}"\n\n'
            f"Răspuns:"
        )

        messages = [{"role": "system", "content": prompt_ai}]
        reply = ask_with_ai(messages, temperature=0.9 , max_tokens= 150)
        

        reply += "<br><br>📞 Introdu, te rog, <strong>doar numele si prenumele</strong> – este foarte important pentru a înregistra comanda. Mulțumim ! 🙏😊"

    
    return jsonify({"message": reply})


def este_numar_valid_local(numar):
    numar = numar.strip()
    if numar.startswith('0') and len(numar) == 9:
        return numar[1] in ['6', '7']
    elif numar.startswith('+373') and len(numar) == 12:
        return numar[4] in ['6', '7']
    elif numar.startswith('373') and len(numar) == 11:
        return numar[3] in ['6', '7']
    else:
        return False

def extrage_si_valideaza_numar(text):
    pattern = r'(?<!\d)(\+?373\d{8}|373\d{8}|0\d{8})(?!\d)'
    posibile_numere = re.findall(pattern, text)
    nr = None
    for nr in posibile_numere:
        if este_numar_valid_local(nr):
            return nr , "VALID"
    return nr , "INVALID"

def check_numar(message):
    prompt = (
        "Verifică dacă textul de mai jos conține un număr de telefon, indiferent de format (poate conține spații, paranteze, simboluri, prefix +, etc.).\n"
        "Important este să existe o secvență de cifre care să poată fi considerată un număr de telefon.\n\n"
        f'Text: "{message}"\n\n'
        "RĂSPUNDE STRICT cu:\n"
        "DA – dacă există un număr de telefon în text\n"
        "NU – dacă nu există niciun număr de telefon în text\n\n"
        "Răspunde doar cu DA sau NU. Fără explicații. Fără alte cuvinte."
    )

    messages = [{"role": "system", "content": prompt}]
    response = ask_with_ai(messages, max_tokens=10)
    return response


@app.route("/numar_de_telefon", methods=["POST"])
def numar_de_telefon():
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")


    valid = check_numar(message)

    print("valid = " , valid)
    if valid == "NU":
        prompt = (
            "Nu te saluta pentru ca deja avem o discutie.\n"
            "Acționează ca un asistent prietenos și politicos.\n"
            "Răspunde natural și cald la mesajul clientului.\n"
            f"Mesaj client: \"{message}\"\n\n"
            "Răspuns:"
        )

        messages = [{"role": "system", "content": prompt}]
        ai_reply = ask_with_ai(messages, max_tokens=150)
        ai_reply += "<br><br> 🙏 Te rog să introduci un număr de telefon valid pentru a putea continua. 📞"

        return jsonify({"message": ai_reply})

    print(message)
    nr, status = extrage_si_valideaza_numar(message)
    preferinte["Numar_Telefon"] = nr
    print(f"valid = {status}")


    if status != "VALID":
        reply = (
            "⚠️ Hmm, numărul introdus nu pare a fi valid.<br>"
            "Te rog să scrii un număr de telefon care începe cu <strong>0</strong> sau <strong>+373</strong>. 📞"
        )

    else:
        reply = (
            "✅ Numărul tău a fost salvat cu succes!<br><br>"
            "📧 Acum te rog introdu o <strong>adresă de email validă</strong> pentru a putea trimite confirmarea comenzii și detalii suplimentare."
        )


    return jsonify({"message": reply})

@app.route("/email", methods=["POST"])
def email():
    data = request.get_json()
    name = data.get("name", "")
    interests = data.get("interests", "")
    message = data.get("message", "")
    potential_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', message)
    valid_emails = []
    for email in potential_emails:
        try:
            valid = validate_email(email)
            valid_email = valid.email
            print(f"Email valid: {valid_email}")
            valid_emails.append(valid_email)
        except EmailNotValidError as e:
            print(f"Email invalid: {email} - {e}")

    if valid_emails:
        email_list = ", ".join(f"<strong>{email}</strong>" for email in valid_emails)
        url = "https://api.hubapi.com/crm/v3/objects/contacts"
        EMAIL = valid_emails[0]

        search_url = "https://api.hubapi.com/crm/v3/objects/contacts/search"

        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }

        search_body = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": EMAIL
                        }
                    ]
                }
            ],
            "properties": ["email"]
        }

        search_response = requests.post(search_url, headers=headers, json=search_body)
        search_data = search_response.json()
        if search_data.get("results"):
            contact_id = search_data["results"][0]["id"]
        else:
            contact_id = "NONE"

        nume_split = preferinte["Nume_Prenume"].split(" ")
        nume = nume_split[0]
        prenume = nume_split[1]
        headers = {
            "Authorization": HUBSPOT_TOKEN,
            "Content-Type": "application/json"
        }
        # print("preferinte = ", preferinte["Serviciul_Ales"])
        if preferinte["BUDGET"] != "":
            mesaj_telegram = (
                "🔔 <b><u>Nouă solicitare primită!</u></b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Nume:</b> <i>{preferinte['Nume_Prenume']}</i>\n"
                f"📧 <b>Email:</b> <i>{valid_emails[0]}</i>\n"
                f"📞 <b>Telefon:</b> <code>{preferinte['Numar_Telefon']}</code>\n"
                f"🛠️ <b>Serviciu dorit:</b> <i>{preferinte['Serviciul_Ales']}</i>\n"
                f"🌐 <b>Limba dorita:</b> <i>{preferinte['Limba_Serviciului']}</i>\n"
                f"💲 <b>Buget:</b> <i>{preferinte['BUDGET']}</i>\n"
                f"💬 <b>Mesaj cu preferintele înregistrare din chat:</b> <i>{preferinte['Preferintele_Utilizatorului_Cautare']}</i>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ <b>Verifică și confirmă comanda din sistem!</b>\n"
            )

            if contact_id == "NONE":
                data = {
                    "properties": {
                        "firstname" : f"{prenume}",
                        "lastname" : f"{nume}",
                        "buget" : f"{preferinte['BUDGET']}",
                        "phone": f"{preferinte['Numar_Telefon']}",
                        "email": f"{valid_emails[0]}",
                        "produs": f"{preferinte['Serviciul_Ales']}",
                        "limba_serviciu": f"{preferinte['Limba_Serviciului']}",
                        "pret_md": f"{int(preferinte['Pret_MD'].replace(" ", ""))}",
                        "pret_ue": f"{int(preferinte['Pret_UE'].replace(" ", ""))}",
                        "hs_lead_status" : "NEW",
                        "preferinte_inregistrare": f"{preferinte['Preferintele_Utilizatorului_Cautare']}",
                        # "contract": f"{}"
                    }
                }

                response_hubspot = requests.post(url, headers=headers, json=data)
                print(response_hubspot.json())

            else:
                update_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
                update_body = {
                    "properties": {
                        "firstname" : f"{prenume}",
                        "lastname" : f"{nume}",
                        "buget" : f"{preferinte['BUDGET']}",
                        "phone": f"{preferinte['Numar_Telefon']}",
                        "email": f"{valid_emails[0]}",
                        "produs": f"{preferinte['Serviciul_Ales']}",
                        "limba_serviciu": f"{preferinte['Limba_Serviciului']}",
                        "pret_md": f"{int(preferinte['Pret_MD'].replace(" ", ""))}",
                        "pret_ue": f"{int(preferinte['Pret_UE'].replace(" ", ""))}",
                        "hs_lead_status" : "NEW",
                        "preferinte_inregistrare": f"{preferinte['Preferintele_Utilizatorului_Cautare']}",
                    }
                }
                update_response = requests.patch(update_url, headers=headers, json=update_body)
                if update_response.status_code == 200:
                    print("✅ Contact actualizat cu succes!")
                else:
                    print("❌ Eroare la actualizare:", update_response.json())
        else:
            mesaj_telegram = (
                "🔔 <b><u>Nouă solicitare primită!</u></b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Nume:</b> <i>{preferinte['Nume_Prenume']}</i>\n"
                f"📧 <b>Email:</b> <i>{valid_emails[0]}</i>\n"
                f"📞 <b>Telefon:</b> <code>{preferinte['Numar_Telefon']}</code>\n"
                f"🛠️ <b>Serviciu dorit:</b> <i>{preferinte['Serviciul_Ales']}</i>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ <b>Verifică și confirmă comanda din sistem!</b>\n"
            )

            if contact_id == "NONE":
                data = {
                    "properties": {
                        "firstname" : f"{prenume}",
                        "lastname" : f"{nume}",
                        "phone": f"{preferinte['Numar_Telefon']}",
                        "email": f"{valid_emails[0]}",
                        "produs": f"{preferinte['Serviciul_Ales']}",
                        "pret_md": f"{int(preferinte['Pret_MD'].replace(" ", ""))}",
                        "pret_ue": f"{int(preferinte['Pret_UE'].replace(" ", ""))}",
                        "hs_lead_status" : "NEW",
                    }
                }

                response_hubspot = requests.post(url, headers=headers, json=data)
                print(response_hubspot.json())

            else:
                update_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
                update_body = {
                    "properties": {
                        "firstname" : f"{prenume}",
                        "lastname" : f"{nume}",
                        "phone": f"{preferinte['Numar_Telefon']}",
                        "email": f"{valid_emails[0]}",
                        "produs": f"{preferinte['Serviciul_Ales']}",
                        "pret_md": f"{int(preferinte['Pret_MD'].replace(" ", ""))}",
                        "pret_ue": f"{int(preferinte['Pret_UE'].replace(" ", ""))}",
                        "hs_lead_status" : "NEW",
                    }
                }
                update_response = requests.patch(update_url, headers=headers, json=update_body)
                if update_response.status_code == 200:
                    print("✅ Contact actualizat cu succes!")
                else:
                    print("❌ Eroare la actualizare:", update_response.json())


        url = f"https://api.telegram.org/bot{TELEGRAM}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": mesaj_telegram,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=payload)
        return jsonify({
            "message": """
                <strong>🎉 Comandă înregistrată cu succes!</strong><br>
                <em>✅ Am notat toate datele importante și totul este pregătit.</em><br><br>

                <b>💬 Ce dorești să faci mai departe?</b><br><br>

                👉 <strong>Plasăm o nouă comandă?</strong> 🛒<br>
                👉 <strong>Descoperim alte servicii?</strong> 🧰<br>

                🧭 <em>Spune-mi ce te interesează și te ghidez cu drag!</em> 😊
            """
        })
    else:
        prompt = (
            f"Utilizatorul a scris : '{message}'.\n\n"
            "Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
            "Scrie un mesaj politicos, prietenos și natural, care:\n"
            "1. Răspunde pe scurt la ceea ce a spus utilizatorul . "
            "2. Mesajul să fie scurt, cald, empatic și prietenos. "
            "Nu mai mult de 2-3 propoziții.\n"
            "Nu folosi ghilimele și nu explica ce faci – scrie doar mesajul final pentru utilizator."
        )
        messages = [{"role": "system", "content": prompt}]
        mesaj = ask_with_ai(messages).strip()
        mesaj += (
            "<br><br>😊 <strong>Te rog frumos să introduci o adresă de email validă</strong> ca să putem continua fără probleme. ✨ Mulțumesc din suflet! 💌"
        )
        return jsonify({"message": mesaj})



def generate_welcome_message(name, interests):
    system_prompt = (
        f"Ești un chatbot inteligent, prietenos și util. Evită să repeți saluturi precum „Salut”, „Bine ai venit” sau numele utilizatorului ({name}) în fiecare mesaj. "
        f"Nu spune niciodată „Salut”, gen toate chestiile introductive, pentru că noi deja ducem o discuție și ne cunoaștem. "
        f"Generează un mesaj foarte scurt și natural, mai scurt de 80 de tokenuri, "
        f"referitor la interesele mele: {interests}. "
        f"Mesajul trebuie să fie cald și încurajator, fără introduceri formale. "
        f"Mesajul trebuie să se termine exact cu: „Cu ce te pot ajuta astăzi?” "
        f"Nu adăuga alte întrebări sau fraze suplimentare. "
        f"Nu saluta, nu repeta numele, doar treci direct la subiect. "
        f"Mereu când ești întrebat de vreo preferință, sfat, alegere sau orice, fă referire la {interests} mele și apoi spune și ceva adițional."
    )
    messages = [{"role": "system", "content": system_prompt}]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.9,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()





def ask_with_ai(messages, temperature=0.9, max_tokens=200):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


def get_user_info():
    name_prompt = (
        "Generează o întrebare scurtă și prietenoasă prin care să ceri utilizatorului să-și spună numele. "
        "Întrebarea trebuie să înceapă cu un salut simplu, cum ar fi „Salut”, „Bună” sau „Hei”. "
        "Formularea trebuie să fie naturală, clară și fără exagerări. "
        "Evită expresii siropoase sau prea entuziaste (ex: „Ce nume frumos”, „dezvăluie”). "
        "Păstrează un ton prietenos, dar echilibrat. Variază formulările între rulări."
    )
    interests_prompt = (
        "Generează o întrebare naturală și prietenoasă prin care să afli ce interese sau hobby-uri are utilizatorul. "
        "Fii creativ și nu repeta aceeași formulare."
    )

    ask_name = ask_with_ai(name_prompt)
    name = input(ask_name + " ")

    ask_interests = ask_with_ai(interests_prompt)
    interests = input(f"{ask_interests} ")

    return name, interests


def build_messages(name, interests):
    system_prompt = (
        f"Răspunsul să fie mai scurt de 250 de tokenuri. "
        f"Utilizatorul se numește {name} și este interesat de: {interests}. "
        f"Ajută-l să își atingă obiectivele prin răspunsuri precise și relevante. "
        f"Fă referire la {interests} de fiecare dată când îi propui ceva, ține cont de ceea ce îi place. Pe lângă asta, poți adăuga și alte variante. "
        f"Dacă utilizatorul are intenția de a încheia discuția, dacă formulează fraze de adio, atunci încheie discuția elegant. "
        f"Ești un chatbot inteligent, prietenos și util. Evită să repeți saluturi precum „Salut”, „Bine ai venit” sau numele utilizatorului ({name}) în fiecare mesaj. "
        f"Răspunde direct, personalizat, scurt și clar, ca și cum conversația este deja în desfășurare. "
        f"Dacă utilizatorul îți zice că nu mai vrea să audă așa mult despre {interests}, atunci schimbă puțin subiectul. "
        f"Ești un chatbot inteligent, prietenos și util. Pe utilizator îl cheamă {name}, "
        f"și este interesat de: {interests}. Oferă răspunsuri personalizate, scurte și clare. Arată cât mai evident că știi acea persoană și ajut-o să își atingă obiectivele prin răspunsuri clare și bine puse la punct!"
    )
    return [{"role": "system", "content": system_prompt}]


@app.route("/", methods=["GET"])
def home():
    return render_template('website.html')


@app.route("/feedback", methods=["POST", "GET"])
def feedback():
    if request.method == "POST":
        data = request.get_json()
        print("Feedback primit:", data)
        # Poți salva feedback-ul aici, dacă vrei
        return jsonify({"status": "ok"})
    return render_template('website.html')


# if __name__ == "__main__":
#     app.run(debug=True, use_reloader=False)

# @app.route("/", defaults={"path": ""})
# @app.route("/<path:path>")
# def serve(path):
#     if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
#         return send_from_directory(app.static_folder, path)
#     else:
#         return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port,debug=True, use_reloader=False)
