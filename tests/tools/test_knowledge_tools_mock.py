from unittest.mock import patch, MagicMock

# Teste para a Tool de RAG Retriever
def test_rag_tool_returns_documents():
	fake_query = "O que é InfinitePay?"
	fake_docs = [
		MagicMock(page_content="InfinitePay é uma solução de pagamentos."),
		MagicMock(page_content="A InfinitePay oferece maquininha e conta PJ.")
	]
	with patch("app.services.rag_service.create_rag_retriever") as mock_create_retriever:
		mock_retriever = MagicMock()
		mock_retriever.invoke.return_value = fake_docs
		mock_create_retriever.return_value = mock_retriever

		retriever = mock_create_retriever()
		results = retriever.invoke(fake_query)

		assert isinstance(results, list)
		assert len(results) == 2
		assert "InfinitePay" in results[0].page_content

# Teste para a Tool de Web Search
def test_web_search_tool_loads_and_splits_documents():
	from app.services import rag_service
	urls = ["https://www.infinitepay.io"]
	fake_document = MagicMock(page_content="Bem-vindo à InfinitePay!")
	with patch("app.services.rag_service.WebBaseLoader") as MockLoader, \
		 patch("app.services.rag_service.RecursiveCharacterTextSplitter") as MockSplitter:
		mock_loader_instance = MockLoader.return_value
		mock_loader_instance.load.return_value = [fake_document]
		mock_splitter_instance = MockSplitter.return_value
		mock_splitter_instance.split_documents.return_value = [fake_document]

		docs = rag_service.load_and_split_documents(urls)

		MockLoader.assert_called_with(urls[0])
		mock_loader_instance.load.assert_called_once()
		MockSplitter.assert_called_once()
		mock_splitter_instance.split_documents.assert_called_once_with([fake_document])
		assert docs == [fake_document]
