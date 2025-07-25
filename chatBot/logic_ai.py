import pandas as pd
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain.llms import OpenAI
from dotenv import load_dotenv
import os
import openai

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

df = pd.read_csv("digitalgrow.csv")
df.columns = df.columns.str.strip()

content = ""
for _, row in df.iterrows():
    content += (
        f"Serviciu: {row['SERVICE']}\n"
        f"Descriere: {row['DESCRIERE']}\n"
        f"Beneficii: {row['BENEFICII']}\n"
        f"Preț (MD): {row['PRET (MD)']}\n"
        f"Reducere: {row['REDUCERE']}\n"
        f"Preț (UE): {row['PRET (UE)']}\n\n\n\n"
    )

print(content)

def ask_with_ai(messages , temperature = 0.9 , max_tokens = 900):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


# Definește întrebarea ta
user_question = "Vreau informatiile despre Magazin Online (E-commerce) si pretul fara reducere"

# Creează promptul cu contextul (contentul citit din CSV)
messages = [
    {
        "role": "system",
        "content": (
            "Ești un asistent care răspunde la întrebări pe baza unei liste de servicii pe care le prestam noi 'DigitalGrow'. "
            "Fiecare serviciu are nume, descriere, beneficii, prețuri și reduceri. "
            "Răspunde strict pe baza informațiilor oferite."
        )
    },
    {
        "role": "user",
        "content": (
            f"Iată lista de servicii:\n\n{content}\n\n"
            f"Întrebare: {user_question}\n"
            "Răspunde detaliat și clar."
        )
    }
]

# Apelează funcția
response = ask_with_ai(messages)

print("\n🔎 Răspuns:")
print(response)

