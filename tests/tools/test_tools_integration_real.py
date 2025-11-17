from app.services import rag_service

def test_rag_retriever_real():
    """
    Teste de integração real para o RAG Retriever.
    Requer que o índice FAISS já exista e contenha dados.
    """
    retriever = rag_service.create_rag_retriever()
    query = "O que é InfinitePay?"
    results = retriever.invoke(query)
    assert isinstance(results, list)
    assert len(results) > 0
    assert any("InfinitePay" in doc.page_content for doc in results)

def test_web_search_real():
    """
    Teste de integração real para Web Search.
    Faz uma busca real em uma página pública.
    """
    urls = ["https://www.infinitepay.io"]
    docs = rag_service.load_and_split_documents(urls)
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert any("InfinitePay" in doc.page_content for doc in docs)
