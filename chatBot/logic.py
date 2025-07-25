import pandas as pd
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain.llms import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 1. Citește CSV-ul
df = pd.read_csv("digitalgrow.csv")
df.columns = df.columns.str.strip()

# 2. Creează documente din fiecare rând
docs = []
categorii = df["SERVICE"].dropna().unique().tolist()
categorii_text = "Lista serviciilor disponibile este:\n" + "\n".join([f"- {cat}" for cat in categorii])
docs.append(Document(page_content=categorii_text, metadata={"categorie": "lista_servicii"}))
servicii_dict = {}

for _, row in df.iterrows():
    serviciu = row['SERVICE'].strip()
    content = (
        f"Serviciu: {row['SERVICE']}\n"
        f"Descriere: {row['DESCRIERE']}\n"
        f"Beneficii: {row['BENEFICII']}\n"
        f"Preț (MD): {row['PRET (MD)']}\n"
        f"Reducere: {row['REDUCERE']}\n"
        f"Preț (UE): {row['PRET (UE)']}"
    )
    detalii = {
        "descriere": row['DESCRIERE'],
        "beneficii": row['BENEFICII'],
        "pret_md": row['PRET (MD)'],
        "reducere": row['REDUCERE'],
        "pret_ue": row['PRET (UE)']
    }


    servicii_dict[serviciu] = detalii
    

    docs.append(Document(page_content=content, metadata={"serviciu": row['SERVICE']}))

# print(servicii_dict)

# 3. Embedding model
embedding_model = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

# 4. Creează vectorstore și salvează-l
vectorstore = Chroma.from_documents(
    docs,
    embedding_model,
    persist_directory="./vector_index"
)

# 5. Memorie conversațională
memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True, output_key='result')

# 6. LLM (poți înlocui cu ChatOpenAI dacă folosești model chat complet)
llm = OpenAI(temperature=0, api_key=OPENAI_API_KEY)

# 7. Lanț QA
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
    chain_type="stuff",
    return_source_documents=True,
    memory=memory
)

# # ✅ Exemplu de întrebare
# query = "Vreau informatiile despre Magazin Online (E-commerce) si pretul"
# result = qa_chain({"query": query})

# # 🔍 Afișează răspunsul și sursele
# print("\n🔎 Răspuns:")
# print(result["result"])

# print("\n📄 Surse:")
# for doc in result["source_documents"]:
#     print("-", doc.metadata)



# def ask_with_ai(messages, temperature=0.9, max_tokens=300):
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=messages,
#         temperature=temperature,
#         max_tokens=max_tokens
#     )
#     return response.choices[0].message.content.strip()

def extract_servicii_dict():
    return servicii_dict

def extract_info(query):
    print("query = ", query)
    query_norm = query.strip().lower()
    for k in servicii_dict:
        if k.strip().lower() == query_norm:
            print(servicii_dict[k])
            return servicii_dict[k]
    return None



