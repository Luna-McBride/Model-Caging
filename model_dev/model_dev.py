import os
import time
import faiss
import tempfile
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
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
    def agent(self):
        return self._agent

    @agent.setter
    def agent(self, model):
        tools = [self.retrieve_context]
        # If desired, specify custom instructions
        system_prompt = (
            """You are an expert in composing functions. You are given a question and a set of possible functions. 
            Based on the question, you will need to make one or more function/tool calls to achieve the purpose. 
            If none of the functions can be used, point it out and refuse to answer. 
            If the given question lacks the parameters required by the function, also point it out.

            You have access to the following tools:
            <tools>{{ retrieve_context }}</tools>

            This tool retrieves context from a CSV file. All prompts are expected to be related to the contents of the CSV file stored in the context.

            It takes only one argument, being the query. The CSV is stored in a vector database, so the query is used to pull relevant chunks from the database.

            The output MUST strictly adhere to the following format, and NO other text MUST be included.
            The example format is as follows. Please make sure the parameter type is correct. If no function call is needed, please make the tool calls an empty list '[]'.
            <tool_call>[
            {"name": "func_name1", "arguments": {"argument1": "value1", "argument2": "value2"}},
            ... (more tool calls as required)
            ]</tool_call>"""
        )
        self._agent = create_agent(model, tools, system_prompt = system_prompt)

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

    @tool(response_format="content_and_artifact")
    def retrieve_context(self, query):
        """Retrieve information to help answer a query."""
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

        for chunk in self.agent.stream(
            {"messages": [{"role": "user", "content": message}]},
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
                    
