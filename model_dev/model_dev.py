import os
import time
import faiss
from langchain.chat_models import init_chat_model
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore

class rag_model:
    def __init__(self, model_type = "HuggingFaceTB/SmolLM2-360M-Instruct",
        embeddings_type = "sentence-transformers/all-MiniLM-l6-v2", doc_store = InMemoryDocstore()):
        self.model = model_type
        self.embeddings = embeddings_type
        self.vector_db = doc_store

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model_type):
        self._model = init_chat_model(
            model_type,
            model_provider = "huggingface",
            temperature = 0.7,
            max_tokens = 1024,
        )

    @property
    def embeddings(self):
        return self._embeddings
    
    @embeddings.setter
    def embeddings(self, embeddings_type):
        self._embeddings = HuggingFaceEmbeddings(model_name = embeddings_type)
        self.embeddings_dim = len(self.embeddings.embed_query("hello world"))

    @property
    def vector_db(self):
        return self._vector_db

    @vector_db.setter
    def vector_db(self, doc_store):
        self.index = faiss.IndexFlatL2(self.embeddings_dim)
        self._vector_db = FAISS(
            embedding_function = self.embeddings,
            index = self.index,
            docstore = doc_store,
            index_to_docstore_id = {},
        )

    def stream_model(self, message):
        for chunk in self._model.stream(message):
            yield chunk.text