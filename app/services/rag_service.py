import time
from pathlib import Path
from typing import Sequence, List

import logging

from github import GithubException, Github
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_core.documents import Document
from langchain_community.document_compressors import FlashrankRerank
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)


class SourceCodeRagService:
    """
    Rag service for java and python which fetch source code from Github
    """

    client = QdrantClient(path=settings.database.qdrant_db_path)

    splitter_java = RecursiveCharacterTextSplitter.from_language(language=Language.JAVA)
    splitter_python = RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON)


    def create_vector_store(self, github_user_name: str, github_repository: str):
        collection = f"{github_user_name}-{github_repository}"
        self.ensure_collection_exists(collection)
        embedding = HuggingFaceEndpointEmbeddings(
            model= settings.llm.hugging_face_embedding_model,
        )
        return QdrantVectorStore(
            client=self.client,
            collection_name=collection,
            embedding=embedding,
        )

    def ensure_collection_exists(self, collection: str) -> bool:
        if self.client.collection_exists(collection):
            return False
        embedding = HuggingFaceEndpointEmbeddings(
            model= settings.llm.hugging_face_embedding_model,
        )
        vector_size = len(embedding.embed_query("sample text"))
        self.client.create_collection(collection, vectors_config = VectorParams(size=vector_size, distance=Distance.COSINE))
        logger.info(f"new collection created with name: {collection}")
        return True


    def retrieve_documents(self, github_user_name: str, github_repository: str, query: str) -> Sequence[Document]:
        retriever = self.create_vector_store(github_user_name, github_repository).as_retriever()
        compressor = FlashrankRerank(top_n=settings.ranker.top_n)
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=retriever
        )
        compressed_docs = compression_retriever.invoke(input=query)
        return compressed_docs

    def load_repository_contents(self, github_user_name: str, github_repository: str, github_token: str|None , branch: str = "main") -> List[Document]:
        """
        Recursively fetch all files from a GitHub repository.

        Args:
            repo_name: Repository name in format "owner/repo"
            branch: Branch name to fetch from

        Returns:
            List of Document objects containing file contents
            :param branch:
            :param github_token:
            :param github_repository:
            :param github_user_name:
        """
        logger.info(f"Fetching contents from {github_repository} (branch: {branch})...")

        documents = []
        try:
            github = Github(github_token or github_user_name)
            repo = github.get_repo(f"{github_user_name}/{github_repository}")

            # Get contents from the specified branch
            contents = repo.get_contents("", ref=branch)

            while contents:
                file_content = contents.pop(0)

                if file_content.type == "dir":
                    # If it's a directory, add its contents to the queue
                    try:
                        contents.extend(repo.get_contents(file_content.path, ref=branch))
                    except GithubException as e:
                        logger.error(f"Error accessing directory {file_content.path}: {e}")
                        continue

                elif file_content.type == "file":
                    # Process file if it should be included
                    if self.should_include_file(file_content.path):
                        try:
                            # Decode file content
                            file_data = file_content.decoded_content.decode('utf-8', errors='ignore')

                            # Create metadata for the document
                            metadata = {
                                "source": file_content.html_url,
                                "file_path": file_content.path,
                                "file_name": Path(file_content.path).name,
                                "repo_name": github_repository,
                                "branch": branch,
                                "size": file_content.size,
                                "type": "code_file"
                            }

                            # Create document
                            doc = Document(
                                page_content=file_data,
                                metadata=metadata
                            )
                            documents.append(doc)
                            logger.info(f"Loaded: {file_content.path}")

                        except UnicodeDecodeError:
                            logger.error(f"Skipping binary file: {file_content.path}")
                        except Exception as e:
                            logger.error(f"Error processing {file_content.path}: {e}")

                    # Rate limiting to avoid API throttling
                    time.sleep(0.1)

        except GithubException as e:
            logger.error(f"Error accessing repository {github_repository}: {e}")

        logger.info(f"Loaded {len(documents)} code files from {github_repository}")
        return documents

    @staticmethod
    def should_include_file(file_path: str) -> bool:
        """
        Determine if a file should be included in indexing.
        """
        # Exclude common non-code files and directories
        exclude_patterns = [
            '__pycache__', '.git', '.env', 'node_modules',
            'venv', 'dist', 'build', '.idea', '.vscode',
            '*.pyc', '*.log', '*.tmp', '*.lock'
        ]

        # Only index common code files java, python
        include_extensions = [
            '.py', '.java'
        ]

        # Check exclude patterns
        for pattern in exclude_patterns:
            if pattern in file_path:
                return False

        # Check file extension
        return any(file_path.endswith(ext) for ext in include_extensions)


    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into smaller chunks for better retrieval.
        """
        logger.info(f"Splitting {len(documents)} documents into chunks...")

        chunked_docs = []
        for doc in documents:
            # Split the document content
            if self.is_java(doc):
                chunks = self.splitter_java.split_text(doc.page_content)
            else:
                chunks = self.splitter_python.split_text(doc.page_content)

            # Create a new document for each chunk with preserved metadata
            for i, chunk in enumerate(chunks):
                chunk_metadata = doc.metadata.copy()
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(chunks)

                chunked_docs.append(
                    Document(
                        page_content=chunk,
                        metadata=chunk_metadata
                    )
                )

        logger.info(f"Created {len(chunked_docs)} chunks")
        return chunked_docs

    def retrieve_and_embed(self, github_user_name: str,  github_repository: str, github_token: str|None) :

        logger.info(f"indexing data started repository: {github_repository}")
        docs = self.load_repository_contents(github_user_name, github_repository, github_token, branch="main")

        # chunk documents
        chunks = self.chunk_documents(docs)

        # embed and store documents
        self.create_vector_store(github_user_name, github_repository).add_documents(documents=chunks)
        logger.info(f"indexing data finished and stored in vector store for repository: {github_repository}")


    @staticmethod
    def is_java(doc):
        return doc.metadata["file_path"].endswith(".java")

source_code_rag_service: SourceCodeRagService = SourceCodeRagService()
