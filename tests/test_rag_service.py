import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Insert lightweight stubs for heavy third-party modules so rag_service can be imported safely
# These stubs provide only the attributes needed by the module under test.

# langchain_core.documents.Document
doc_module = types.ModuleType("langchain_core.documents")
class Document:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

doc_module.Document = Document
sys.modules['langchain_core.documents'] = doc_module

# langchain_text_splitters
splitters_module = types.ModuleType("langchain_text_splitters")
class Language:
    JAVA = 'java'
    PYTHON = 'python'

class RecursiveCharacterTextSplitter:
    @staticmethod
    def from_language(language=None):
        class Splitter:
            def split_text(self, text):
                # simple, deterministic splitting for tests
                return [text]
        return Splitter()

splitters_module.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
splitters_module.Language = Language
sys.modules['langchain_text_splitters'] = splitters_module

# langchain_huggingface (embedding stub)
hf_module = types.ModuleType("langchain_huggingface")
class HuggingFaceEndpointEmbeddings:
    def __init__(self, model=None):
        self.model = model
    def embed_query(self, text):
        return [0.1, 0.2, 0.3]
hf_module.HuggingFaceEndpointEmbeddings = HuggingFaceEndpointEmbeddings
sys.modules['langchain_huggingface'] = hf_module

# langchain_qdrant.QdrantVectorStore stub
qdrant_store_module = types.ModuleType("langchain_qdrant")
class QdrantVectorStore:
    def __init__(self, client=None, collection_name=None, embedding=None):
        self.client = client
        self.collection_name = collection_name
        self.embedding = embedding
    def as_retriever(self):
        return None
    def add_documents(self, documents=None):
        pass
qdrant_store_module.QdrantVectorStore = QdrantVectorStore
sys.modules['langchain_qdrant'] = qdrant_store_module

# langchain_classic.retrievers and community.compressors minimal stubs
rc_mod = types.ModuleType('langchain_classic.retrievers')
setattr(rc_mod, 'ContextualCompressionRetriever', lambda base_compressor=None, base_retriever=None: types.SimpleNamespace(invoke=lambda input: []))
sys.modules['langchain_classic.retrievers'] = rc_mod
sys.modules['langchain_community.document_compressors'] = types.ModuleType('langchain_community.document_compressors')
setattr(sys.modules['langchain_community.document_compressors'], 'FlashrankRerank', lambda top_n=3: None)

# qdrant_client and qdrant_client.models stubs
qdrant_client = types.ModuleType('qdrant_client')
class QdrantClient:
    def __init__(self, *args, **kwargs):
        pass
    def collection_exists(self, name):
        return False
    def create_collection(self, name, vectors_config=None):
        return None
qdrant_client.QdrantClient = QdrantClient

qdrant_models = types.ModuleType('qdrant_client.models')
class Distance:
    COSINE = 'cosine'
qdrant_models.Distance = Distance
class VectorParams:
    def __init__(self, size=None, distance=None):
        self.size = size
        self.distance = distance
qdrant_models.VectorParams = VectorParams

sys.modules['qdrant_client'] = qdrant_client
sys.modules['qdrant_client.models'] = qdrant_models

# Now import the module under test
from app.services.rag_service import SourceCodeRagService


def test_should_include_file():
    assert SourceCodeRagService.should_include_file('src/app/main.py')
    assert SourceCodeRagService.should_include_file('src/example/Main.java')
    assert not SourceCodeRagService.should_include_file('node_modules/lib/index.js')
    assert not SourceCodeRagService.should_include_file('.git/config')
    assert not SourceCodeRagService.should_include_file('build/output.bin')
    assert not SourceCodeRagService.should_include_file('logs/app.log')


def test_is_java():
    doc = SimpleNamespace(metadata={"file_path": "src/Main.java"})
    assert SourceCodeRagService.is_java(doc)
    doc2 = SimpleNamespace(metadata={"file_path": "src/util.py"})
    assert not SourceCodeRagService.is_java(doc2)


def test_ensure_collection_exists_creates_collection_when_missing(monkeypatch):
    # Prepare a mock client that reports collection does not exist
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = False
    mock_client.create_collection = MagicMock()

    # Use a small dummy embedding implementation
    class DummyEmbedding:
        def __init__(self, model=None):
            pass
        def embed_query(self, text):
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr('app.services.rag_service.HuggingFaceEndpointEmbeddings', DummyEmbedding)

    service = SourceCodeRagService()
    # replace the client on the instance to avoid any global side effects
    service.client = mock_client

    created = service.ensure_collection_exists('test-collection')

    assert created is True
    mock_client.collection_exists.assert_called_once_with('test-collection')
    mock_client.create_collection.assert_called_once()


def test_ensure_collection_exists_noop_when_exists(monkeypatch):
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    service = SourceCodeRagService()
    service.client = mock_client
    created = service.ensure_collection_exists('exists-collection')
    assert created is False
    mock_client.create_collection.assert_not_called()
