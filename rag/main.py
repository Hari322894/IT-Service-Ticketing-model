import os
import sqlite3
import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain

# PASTE YOUR ACTUAL OPENAI API KEY HERE
os.environ["OPENAI_API_KEY"] = "your-actual-api-key-here"

CSV_FILE = "all_tickets_processed_improved_v3.csv"
SQL_SCRIPT = "rag.sql"
DB_FILE = "it_tickets.db"
VECTOR_DB_DIR = "./chroma_it_db"

def setup_database():
    """Reads the rag.sql schema and seeds it with Kaggle CSV data columns."""
    if not os.path.exists(CSV_FILE):
        print(f" ERROR: Cannot find '{CSV_FILE}' in this folder. Make sure it's unzipped and here!")
        return False
        
    if not os.path.exists(SQL_SCRIPT):
        print(f" ERROR: Cannot find '{SQL_SCRIPT}' script in this folder!")
        return False

    print("🧹 Cleaning up old database files for a fresh build...")
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    # 1. Initialize SQLite Database utilizing your rag.sql blueprint
    print(f" Reading schema from '{SQL_SCRIPT}' and initializing SQLite...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    with open(SQL_SCRIPT, "r") as sql_file:
        schema = sql_file.read()
        cursor.executescript(schema)
    conn.commit()

    # 2. Read raw CSV columns explicitly matching your file
    print(f"Parsing raw records from '{CSV_FILE}'...")
    df = pd.read_csv(CSV_FILE)
    
    # Clean out empty rows and take a 150-row slice to save API costs
    df_clean = df.dropna(subset=['Document', 'Topic_group']).head(150)

    print(" Seeding relational database tables...")
    tickets_data = []
    for _, row in df_clean.iterrows():
        # Mapping CSV columns: 'Topic_group' -> category, and 'Document' -> issue_description
        tickets_data.append((row['Topic_group'], row['Document']))

    # Inserts data into columns defined by your schema (id handles itself via AUTOINCREMENT)
    cursor.executemany(
        "INSERT INTO support_tickets (category, issue_description) VALUES (?, ?)", 
        tickets_data
    )
    conn.commit()
    conn.close()
    print(f" SQL Database '{DB_FILE}' successfully built and seeded.")
    return True

def run_rag_pipeline():
    """Extracts rows from SQLite, processes them into chunks, and runs RAG query."""
    print("\n Extracting records from SQL database for vectorization...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT category, issue_description FROM support_tickets")
    rows = cursor.fetchall()
    conn.close()

    # Transform SQL records into LangChain searchable documents
    documents = []
    for category, issue_description in rows:
        formatted_text = f"IT Helpdesk Department: {category} | Log Content: {issue_description}"
        documents.append(Document(page_content=formatted_text))

    print(f" Slicing structural logs into semantic text chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    print("Vectorizing chunks and building local Vector DB (Chroma)...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # Automatically creates or overwrites the local Vector DB directory
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTOR_DB_DIR
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # 3. Initialize OpenAI Chat Model API Connection
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    system_prompt = (
        "You are an expert corporate IT Systems Infrastructure Analyst.\n"
        "Use the historical incident logs provided below to answer the user's query.\n"
        "Identify overlapping technical problems, common failure modes, or patterns. "
        "If no logs match the request, reply with 'No matching technical records found.'\n\n"
        "Historical Logs Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # Assemble RAG Chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    # 4. Run sample audit query
    audit_query = "What specific issues are users reporting regarding password resets, access issues, or expiration days?"
    print(f"\n Querying RAG System: '{audit_query}'")
    
    response = rag_chain.invoke({"input": audit_query})
    
    print("\n Generated Infrastructure Audit Report:")
    print(response["answer"])

if __name__ == "__main__":
        print(" ERROR: Please replace 'your-actual-api-key-here' with your real OpenAI API key.")
else:
        # Step 1: Run table generation and file data dump
        success = setup_database()
        # Step 2: Extract from SQL table, build mathematical vector matrix database, talk to AI
        if success:
            run_rag_pipeline()