from dotenv import load_dotenv
load_dotenv()
import os
import logging
import sys
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
# Logging configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('vector_db.log')
    ]
)
logger = logging.getLogger(__name__)
api_key=os.getenv("google_api_key")
# Set default headers for external requests
headers = {
    "User-Agent": os.environ.get(
        "USER_AGENT", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}


def initialize_embeddings():
    """
    Initialize Google Generative AI Embeddings with error handling.
    
    Returns:
        GoogleGenerativeAIEmbeddings: Configured embedding model
    """
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        return embeddings
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        raise



def vectordb(docs_list=None,collection_name=None,persist_directory=None):
    persist_directory = "./chroma_db"
    os.makedirs(persist_directory, exist_ok=True)
    # collection_name = "ipl-data"

    try:
        embeddings = initialize_embeddings()
    except Exception as e:
        logger.error("Embedding initialization failed")
        raise

    try:
        client = chromadb.PersistentClient(path=persist_directory)

        # Delete existing collection if it exists
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"Old collection '{collection_name}' deleted.")
        except Exception as e:
            logger.warning(f"Collection '{collection_name}' did not exist or couldn't be deleted: {e}")

        # Create new collection and add new documents
        vectorstore = Chroma.from_documents(
            documents=docs_list,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=persist_directory
        )

        retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
        return retriever

    except Exception as e:
        logger.error(f"Vector database refresh failed: {e}")
        raise


def chain_creator():
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

    prompt = ChatPromptTemplate.from_template("""
You are CricAI, a cutting-edge AI assistant specialized in cricket analysis and match insights for IPL 2025.

You will be provided with the latest data from IPL 2025 — including match summaries, player stats, scores, and commentary.

Your job is to:
1. Understand and analyze the given context.
2. Answer user questions with accurate, up-to-date information.
3. If the context includes real-time or predictive data, use it to make logical, data-driven insights.
4. Be concise, informative, and cricket-savvy in your tone.

CONTEXT:
{context}

USER QUESTION:
{question}

CRICAI RESPONSE:
""")

    chain = prompt | llm | StrOutputParser()
    return chain
