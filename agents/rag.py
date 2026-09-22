
import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START
from typing import Annotated, TypedDict
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.prebuilt import ToolNode, tools_condition
from utils.llm_pick import pick_llm
from langchain_huggingface import HuggingFaceEmbeddings
from models.schema import RAGAgentSchema


load_dotenv()

llm = pick_llm("low")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PDF_PATH = os.path.join(BASE_DIR, "The_GALE_ENCYCLOPEDIA_of_MEDICINE_SECOND.pdf")
INDEX_DIR = os.path.join(BASE_DIR, "data", "faiss_index")

# embedding
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# load or build vector store
if os.path.exists(INDEX_DIR) and os.path.exists(os.path.join(INDEX_DIR, "index.faiss")):
    vector_store = FAISS.load_local(
        INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )
else:
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    vector_store = FAISS.from_documents(
        chunks,
        embeddings
    )
    os.makedirs(INDEX_DIR, exist_ok=True)
    vector_store.save_local(INDEX_DIR)

# create retriever
retriever = vector_store.as_retriever(
    search_kwargs={"k": 4}
)


@tool
def rag_tool(query: str) -> dict:
    """
    Retrieve relevant information from the medical encyclopedia PDF document.
    Use this tool when the user asks factual, clinical, disease, symptoms,
    treatment, or health-related questions that might be answered from the stored documents.
    """

    result = retriever.invoke(query)

    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]

    return {
        "query": query,
        "context": context,
        "metadata": metadata
    }

# binding tools with llm

tools = [rag_tool]
llm_with_tools = llm.bind_tools(tools)



def chat_node(state: RAGAgentSchema):

    messages = state.messages

    response = llm_with_tools.invoke(messages)

    return {'messages': [response]}


tool_node = ToolNode(tools)


graph = StateGraph(RAGAgentSchema)

graph.add_node('chat_node', chat_node)
graph.add_node('tools', tool_node)

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')

chatbot = graph.compile()
rag_agent = chatbot


# chatbot
if __name__ == "__main__":

    result = chatbot.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Using the pdf notes, explain the treatment options for cancer"
                    )
                )
            ]
        }
    )


    messages = result.messages if hasattr(result, "messages") else result["messages"]
    print(messages[-1].content.encode("utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"))