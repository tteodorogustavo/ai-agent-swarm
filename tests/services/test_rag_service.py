"""
Unit Tests for the RAG Service (The "Dumb" Librarian)

This file tests the `rag_service.py`.
Since we moved all "smart" logic (LLMs, Query Construction) to the
Graph layer (Router/Agents), these tests are simple.

We only need to "mock" (fake) the parts that cost money (Embeddings)
or touch the disk/network (Loaders, FAISS, SQLRecordManager).
"""
import os
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.services.rag import rag_service
# This is the "Engine" we are testing

# --- Test 1: Test the "Writer" (Ingestion) ---


@patch("app.services.rag.rag_service.index")
@patch("app.services.rag.rag_service.SQLRecordManager")
@patch("app.services.rag.rag_service.get_vector_store")
@patch("app.services.rag.rag_service.load_and_split_documents")
@patch("app.services.rag.rag_service.OpenAIEmbeddings")
def test_run_full_ingestion(
    MockEmbeddings, mock_load_splits, mock_get_store, MockRecordManager, mock_index
):
    """
    Tests the main orchestrator function `run_full_ingestion`.
    We mock *all* external calls to just check the "flow".
    """
    # 1. Setup Mocks (Fakes)
    mock_splits = [Document(page_content="fake chunk")]
    mock_load_splits.return_value = mock_splits

    mock_vector_store_instance = MagicMock()
    mock_get_store.return_value = mock_vector_store_instance

    mock_record_manager_instance = MagicMock()
    MockRecordManager.return_value = mock_record_manager_instance

    mock_embeddings_instance = MagicMock()
    MockEmbeddings.return_value = mock_embeddings_instance

    # 2. Run the Orchestrator
    rag_service.run_full_ingestion()

    # 3. Assert (Check the "flow")

    # Did it try to load/split documents?
    mock_load_splits.assert_called_once_with(rag_service.INFINITEPAY_URLS)

    # Did it setup the embeddings and vector store?
    MockEmbeddings.assert_called_once()
    mock_get_store.assert_called_once_with(mock_embeddings_instance)

    # Did it setup the record manager?
    MockRecordManager.assert_called_once()
    mock_record_manager_instance.create_schema.assert_called_once()

    # Did it call the main LangChain 'index' function correctly?
    mock_index.assert_called_once_with(
        mock_splits,
        mock_record_manager_instance,
        mock_vector_store_instance,
        cleanup="incremental",
        source_id_key="source",
    )

    # Did it save the final result?
    mock_vector_store_instance.save_local.assert_called_once_with(
        rag_service.VECTOR_STORE_PATH
    )


# --- Test 2: Test the "Reader" (Librarian) ---


@patch("app.services.rag.rag_service.FAISS")
@patch("app.services.rag.rag_service.OpenAIEmbeddings")
@patch("app.services.rag.rag_service.os.path.exists", return_value=True)
def test_create_rag_retriever(mock_path_exists, MockEmbeddings, MockFAISS):
    """
    Tests the "Dumb" Librarian creator.

    We just need to check:
    1. Does it load the FAISS store from the correct path?
    2. Does it configure the retriever with the correct "k" value?
    3. Does it return a valid retriever?
    """
    # 1. Setup Mocks
    mock_vector_store_instance = MagicMock()
    mock_retriever = MagicMock(spec=BaseRetriever)
    mock_vector_store_instance.as_retriever.return_value = mock_retriever
    mock_embeddings_instance = MagicMock()
    MockEmbeddings.return_value = mock_embeddings_instance
    MockFAISS.load_local.return_value = mock_vector_store_instance

    # 2. Run the function
    retriever = rag_service.create_rag_retriever()

    # 3. Assert

    # Did it check for the *correct* file path?
    mock_path_exists.assert_called_with(
        os.path.join(rag_service.VECTOR_STORE_PATH, "index.faiss")
    )

    # Did it load the embeddings and FAISS store correctly?
    MockEmbeddings.assert_called_once()
    MockFAISS.load_local.assert_called_with(
        rag_service.VECTOR_STORE_PATH,
        mock_embeddings_instance,
        allow_dangerous_deserialization=True,
    )

    mock_vector_store_instance.as_retriever.assert_called_with(search_kwargs={"k": 4})

    # Did it return a retriever?
    assert isinstance(retriever, BaseRetriever)


@patch("app.services.rag.rag_service.os.path.exists", return_value=False)
def test_create_rag_retriever_file_not_found(mock_path_exists):
    """
    Tests if the retriever correctly raises an error
    if the index file is missing.
    """
    # 1. Arrange, Act, Assert
    # We use pytest.raises to check if the *correct error* is raised
    with pytest.raises(FileNotFoundError, match="Vector store not found"):
        rag_service.create_rag_retriever()
