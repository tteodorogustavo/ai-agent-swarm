"""
RAG Service Module (The "Engine")

Contains all core logic for:
1. RAG Part 1: Ingestion pipeline (writing to the Vector Store)
2. RAG Part 2: Creating a *retriever* (reading from the Vector Store)

This service is "dumb" on purpose. It contains NO query transformation logic.
That "smart" logic belongs in the Graph (Router, Agents).
"""
import logging
import os
from typing import List
from urllib.parse import urlparse

import dotenv
from langchain_classic.indexes import index
from langchain_classic.indexes import SQLRecordManager
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
# --- RAG Part 1: Ingestion Imports ---
# These are the "CERTO" (modern) imports
# --- RAG Part 2: Retrieval Imports ---

dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- 1. Configuration (Constants) ---
INFINITEPAY_URLS = [
    "https://www.infinitepay.io",
    "https://www.infinitepay.io/maquininha",
    "https://www.infinitepay.io/maquininha-celular",
    "https://www.infinitepay.io/tap-to-pay",
    "https://www.infinitepay.io/pdv",
    "https://www.infinitepay.io/receba-na-hora",
    "https://www.infinitepay.io/gestao-de-cobranca-2",
    "https://www.infinitepay.io/gestao-de-cobranca",
    "https://www.infinitepay.io/link-de-pagamento",
    "https://www.infinitepay.io/loja-online",
    "https://www.infinitepay.io/boleto",
    "https://www.infinitepay.io/conta-digital",
    "https://www.infinitepay.io/conta-pj",
    "https://www.infinitepay.io/pix",
    "https://www.infinitepay.io/pix-parcelado",
    "https://www.infinitepay.io/emprestimo",
    "https://www.infinitepay.io/cartao",
    "https://www.infinitepay.io/rendimento",
]

VECTOR_STORE_PATH = "data/vector_store"
RECORD_MANAGER_DB_PATH = "data/record_manager_db.sql"


# --- 2. RAG Part 1: Ingestion Logic ---


def _get_topic_from_url(url: str) -> str:
    """Helper function to extract a 'topic' from the URL path for metadata."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "homepage"
    return path.split("/")[0]


def get_vector_store(embeddings: OpenAIEmbeddings) -> FAISS:
    """
    Loads the FAISS vector store if it exists, otherwise creates a new one.
    """
    faiss_index_file = os.path.join(VECTOR_STORE_PATH, "index.faiss")
    if os.path.exists(faiss_index_file):
        logging.info(f"Loading existing vector store from {VECTOR_STORE_PATH}")
        return FAISS.load_local(
            VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True
        )
    else:
        logging.info(
            f"No existing index found at {faiss_index_file}. Creating new vector store."
        )
        # Create an empty store to be populated by the indexer
        placeholder_doc = Document(page_content="init")
        vector_store = FAISS.from_documents([placeholder_doc], embeddings)
        vector_store.delete(vector_store.index_to_docstore_id.values())
        return vector_store


def load_and_split_documents(urls: List[str]) -> List[Document]:
    """
    Loads docs from URLs, adds custom metadata (tagging), and splits them.
    """
    logging.info(f"Loading {len(urls)} URLs...")
    all_docs = []

    for url in urls:
        try:
            loader = WebBaseLoader(url)
            docs = loader.load()

            # Add our custom 'topic' metadata for filtering
            topic = _get_topic_from_url(url)
            for doc in docs:
                doc.metadata["topic"] = topic

            all_docs.extend(docs)
        except Exception as e:
            logging.warning(f"Failed to load {url}: {e}")

    logging.info(f"Loaded {len(all_docs)} documents. Now splitting...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
    )

    all_splits = text_splitter.split_documents(all_docs)
    logging.info(f"Split into {len(all_splits)} chunks.")
    return all_splits


def run_full_ingestion():
    """
    Main function to run the full incremental ingestion pipeline.
    This orchestrates all components.
    """
    logging.info("Starting ingestion service...")

    try:
        # "CERTO" Way: Initialize *without* manual api_key.
        # LangChain will automatically find the OPENAI_API_KEY from the .env file.
        embeddings = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY"), model="text-embedding-3-small"
        )
        vector_store = get_vector_store(embeddings)
    except Exception as e:
        logging.error(
            f"Failed to initialize embeddings or vector store: {e}", exc_info=True
        )
        return

    try:
        namespace = "infinitepay_docs"
        record_manager = SQLRecordManager(
            namespace, db_url=f"sqlite:///{RECORD_MANAGER_DB_PATH}"
        )
        record_manager.create_schema()
    except Exception as e:
        logging.error(f"Failed to initialize record manager: {e}", exc_info=True)
        return

    try:
        # Load and split all documents
        all_splits = load_and_split_documents(INFINITEPAY_URLS)
    except Exception as e:
        logging.error(f"Failed to load and split documents: {e}", exc_info=True)
        return

    if not all_splits:
        logging.warning("No documents were loaded or split. Aborting indexing.")
        return

    logging.info("Starting incremental indexing...")

    try:
        result = index(
            all_splits,
            record_manager,
            vector_store,
            cleanup="incremental",
            source_id_key="source",
        )
    except Exception as e:
        logging.error(f"Indexing failed: {e}", exc_info=True)
        return

    # "CERTO" Way: Use an f-string to log the result dictionary
    logging.info(
        f"Indexing complete. Added: {result.get('num_added', 0)}, Updated: {result.get('num_updated', 0)}, Deleted: {result.get('num_deleted', 0)}"
    )

    # Save the updated store to disk
    vector_store.save_local(VECTOR_STORE_PATH)
    logging.info(f"Vector store saved to {VECTOR_STORE_PATH}")


# --- 3. RAG Part 2: Retrieval Logic (The "Dumb" Librarian) ---


def create_rag_retriever() -> BaseRetriever:
    """
    Creates the RAG Retriever that the Knowledge Agent will use.

    This function is "dumb" on purpose. It simply loads the FAISS store
    and returns a retriever with its "Permanent Orders" (k=4).

    It does NOT know about LLMs or Query Analysis.
    That "smart" logic is handled by the Graph (Router/Agents).
    """
    logging.info("Initializing RAG Retriever (FAISS)...")

    # 1. Load Embeddings (needed to load the store)
    # "CERTO" Way: Initialize *without* manual api_key.
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # 2. Load FAISS Vector Store
    index_path = os.path.join(VECTOR_STORE_PATH, "index.faiss")
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Vector store not found: {index_path}")

    vector_store = FAISS.load_local(
        VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True
    )

    # 3. Create and return the "Dumb" Retriever
    # We give it its "Permanent Orders" (k=4)
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 4}  # The "Permanent Order"
    )

    logging.info("RAG Retriever (FAISS) initialized successfully.")
    return retriever
