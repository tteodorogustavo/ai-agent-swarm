from typing import List

from langchain_core.documents import Document

import app.services.rag.rag_service as rag_service


class DummyEmbeddings:
    """A tiny embeddings shim that returns deterministic vectors for documents."""

    def __init__(self, *args, **kwargs):
        pass

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # simple deterministic embedding: vector of token counts
        return [[float(len(t)) for _ in range(8)] for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return [float(len(text)) for _ in range(8)]


def test_create_rag_retriever_with_local_store(tmp_path, monkeypatch):
    """Create a FAISS store with dummy embeddings and ensure create_rag_retriever loads it."""
    # Prepare paths
    temp_store = tmp_path / "vector_store"
    temp_store.mkdir()

    # Prepare sample documents
    docs = [Document(page_content=f"Doc about taxas {i}") for i in range(5)]

    # Monkeypatch the embedding class used by the service
    monkeypatch.setattr(rag_service, "OpenAIEmbeddings", DummyEmbeddings)

    # Monkeypatch VECTOR_STORE_PATH to our temp dir
    monkeypatch.setattr(rag_service, "VECTOR_STORE_PATH", str(temp_store))

    # Build a FAISS store using the DummyEmbeddings
    embeddings = DummyEmbeddings()
    from langchain_community.vectorstores import FAISS

    vs = FAISS.from_documents(docs, embeddings)
    # save local index files
    vs.save_local(str(temp_store))

    # Now call create_rag_retriever (it will use DummyEmbeddings via monkeypatch)
    retriever = rag_service.create_rag_retriever()

    # Basic sanity checks: retriever loaded and has a backing vectorstore
    assert retriever is not None
    assert hasattr(retriever, "vectorstore")


def test_load_and_split_documents_with_mocked_loader(monkeypatch):
    """Mock WebBaseLoader to return a predictable document and ensure splitting runs."""
    sample_url = "https://example.com/test"

    class FakeLoader:
        def __init__(self, url):
            self.url = url

        def load(self):
            from langchain_core.documents import Document

            # produce a long document that will be split into multiple chunks
            return [Document(page_content=("Para testes. \n" * 2000))]

    # Patch WebBaseLoader in the rag_service module
    monkeypatch.setattr(rag_service, "WebBaseLoader", FakeLoader)

    docs = rag_service.load_and_split_documents([sample_url])
    assert isinstance(docs, list)
    assert len(docs) > 1
