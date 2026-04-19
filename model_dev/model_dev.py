from __future__ import annotations
from typing import Annotated, List, Tuple

from transformers import BitsAndBytesConfig

import os
import torch
import faiss
import tempfile
from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain.chat_models import init_chat_model
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.docstore.in_memory import InMemoryDocstore

from dotenv import load_dotenv

load_dotenv() 

os.environ["HUGGINGFACEHUB_API_TOKEN"] = os.getenv("HUGGINGFACEHUB_API_TOKEN")

class rag_model:
    def __init__(self, model_type = "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        embeddings_type = "sentence-transformers/all-MiniLM-l6-v2", doc_store = InMemoryDocstore()):
        self.model = model_type
        self.embeddings = embeddings_type
        self.vector_db = doc_store

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model_type):
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        self._model = init_chat_model(
            model_type,
            model_provider="huggingface",
            temperature=0.7,
            max_tokens=1024,
            quantization_config=bnb_config,
        )

    @property
    def agent(self):
        return self._agent

    @agent.setter
    def agent(self, model):
        system_prompt = """Using the information contained in the context,
                    give a comprehensive answer to the question.
                    Respond only to the question asked, response should be concise and relevant to the question.
                    If the answer cannot be deduced from the context, say you don't know."""
        self._agent = create_agent(model, [], system_prompt = system_prompt)

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

    def fill_database(self, file):
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=True, delete_on_close=False) as temp_file:
            content = file.read().decode('utf-8')
            temp_file.write(content)
            temp_file.flush()
            temp_file.seek(0)
            
            loader = CSVLoader(file_path=temp_file.name)
            docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                add_start_index=True,
            )
            all_splits = text_splitter.split_documents(docs)

            self.vector_db.add_documents(documents=all_splits)

    def retrieve_context(self, query: Annotated[str, "The question being asked."]) -> Tuple[str, List[Document]]:
        """Retrieve information to help answer a query using a similarity search on the vector database.
        
        Args:
            query: the question being asked.

        Returns:
            serialized: a serialized version of the documents collected from the vector database.
            retrieved_docs: the documents retrieved from the vector database's similarity search.
        
        """
        retrieved_docs = self._vector_db.similarity_search(query, k=2)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\nContent: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

    def stream_model(self, message):
        for chunk in self.model.stream(message):
            yield chunk.text

    def stream_agent(self, message):
        self.agent = self.model

        context, _ = self.retrieve_context(message)
        final_prompt = {
                "role": "user",
                "content": f"""Context:
                    {context}
                    ---
                    Now here is the question you need to answer.

                    Question: {message}""",
            }

        for chunk in self.agent.stream(
            {"messages": [final_prompt]},
            stream_mode="messages",
            version="v2",
        ):
            print(chunk)
            if chunk["type"] == "messages":
                token, metadata = chunk["data"]
                try:
                    yield f"{token.content_blocks[0]["text"]}"

                except:
                    pass
                    
