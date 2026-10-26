import os
import sys
from typing import Annotated, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv

# 1. Document Loading and Splitting
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# 2. Dense Retrieval (Bi-encoder embeddings & FAISS vector store)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# 3. Sparse Retrieval (BM25 keyword search)
from langchain_community.retrievers import BM25Retriever

# 4. Hybrid Search (EnsembleRetriever with Reciprocal Rank Fusion)
from langchain_classic.retrievers import EnsembleRetriever

# 5. Cross-Encoder Reranking
from sentence_transformers import CrossEncoder

# 6. LangGraph Agent, Tools, and Messages
from langchain.tools import tool
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

# 7. Utilities and State Schema
from utils.llm_pick import pick_llm
from models.schema import RAGAgentSchema


load_dotenv()

# Initialize primary LLM
llm = pick_llm("low")
# ============================================================================
# STAGE 1: DOCUMENT INGESTION & VECTOR STORE SETUP
# ============================================================================


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PDF_DIR = os.path.join(BASE_DIR, "datas", "pdf")
PDF_PATH = PDF_DIR  # Alias for compatibility
INDEX_DIR = os.path.join(BASE_DIR, "data", "faiss_index")

# Bi-encoder embedding model for dense retrieval
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

chunks: list[Document] = []

# Load existing FAISS index or build a new one from multiple PDFs
if os.path.exists(INDEX_DIR) and os.path.exists(os.path.join(INDEX_DIR, "index.faiss")):
    try:
        vector_store = FAISS.load_local(
            INDEX_DIR,
            embeddings,
            allow_dangerous_deserialization=True
        )
        loaded_chunks = list(vector_store.docstore._dict.values())
        current_pdf_names = {
            os.path.basename(f)
            for f in os.listdir(PDF_DIR)
            if f.lower().endswith(".pdf")
        } if os.path.exists(PDF_DIR) else set()

        index_sources = {
            os.path.basename(doc.metadata.get("source", ""))
            for doc in loaded_chunks
        }

        # Check if the existing index matches current PDFs in datas/pdf
        if index_sources and current_pdf_names and index_sources.intersection(current_pdf_names):
            # Normalize and ensure metadata keys across all loaded chunks
            for chunk in loaded_chunks:
                source_name = os.path.basename(chunk.metadata.get("source") or chunk.metadata.get("file_name") or "document.pdf")
                raw_page = chunk.metadata.get("page", 0)
                page_num = chunk.metadata.get("page_number") or (raw_page + 1 if isinstance(raw_page, int) else 1)
                page_label = str(chunk.metadata.get("page_label") or page_num)
                chunk.metadata["source"] = source_name
                chunk.metadata["file_name"] = source_name
                chunk.metadata["page"] = raw_page
                chunk.metadata["page_number"] = page_num
                chunk.metadata["page_label"] = page_label

            chunks = loaded_chunks
            print(f"Loaded existing index with {len(chunks)} chunks from {len(index_sources)} files.")
        else:
            print(f"Existing index does not match files in {PDF_DIR}. Rebuilding index...")
            chunks = []
    except Exception as e:
        print(f"[Warning] Failed to load index from {INDEX_DIR} ({e}). Rebuilding...")
        chunks = []

if not chunks:
    if not os.path.exists(PDF_DIR):
        raise FileNotFoundError(f"PDF directory not found at {PDF_DIR}")

    pdf_files = [
        os.path.join(PDF_DIR, f)
        for f in sorted(os.listdir(PDF_DIR))
        if f.lower().endswith(".pdf")
    ]
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {PDF_DIR}")

    print(f"Loading documents from {len(pdf_files)} PDF file(s) in {PDF_DIR}...")
    docs: list[Document] = []
    for idx, pdf_file in enumerate(pdf_files, start=1):
        file_name = os.path.basename(pdf_file)
        print(f"  [{idx}/{len(pdf_files)}] Loading {file_name}...")
        try:
            loader = PyPDFLoader(pdf_file)
            file_docs = loader.load()
            for doc in file_docs:
                raw_page = doc.metadata.get("page", 0)
                page_num = raw_page + 1 if isinstance(raw_page, int) else 1
                page_label = str(doc.metadata.get("page_label") or page_num)
                doc.metadata["source"] = file_name
                doc.metadata["file_name"] = file_name
                doc.metadata["page"] = raw_page
                doc.metadata["page_number"] = page_num
                doc.metadata["page_label"] = page_label
            docs.extend(file_docs)
        except Exception as e:
            print(f"  [Warning] Failed to load {file_name}: {e}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(docs)

    # Ensure page numbers and source metadata are cleanly preserved
    for chunk in chunks:
        source_name = os.path.basename(chunk.metadata.get("source") or chunk.metadata.get("file_name") or "document.pdf")
        raw_page = chunk.metadata.get("page", 0)
        page_num = chunk.metadata.get("page_number") or (raw_page + 1 if isinstance(raw_page, int) else 1)
        page_label = str(chunk.metadata.get("page_label") or page_num)
        chunk.metadata["source"] = source_name
        chunk.metadata["file_name"] = source_name
        chunk.metadata["page"] = raw_page
        chunk.metadata["page_number"] = page_num
        chunk.metadata["page_label"] = page_label

    print(f"Created {len(chunks)} chunks from {len(docs)} pages. Building FAISS index...")
    vector_store = FAISS.from_documents(chunks, embeddings)
    os.makedirs(INDEX_DIR, exist_ok=True)
    vector_store.save_local(INDEX_DIR)
    print(f"FAISS index successfully saved to {INDEX_DIR}.")

# ============================================================================
# STAGES 2, 3 & 4: DENSE, SPARSE & HYBRID RETRIEVAL (RRF)
# ============================================================================

# Stage 2: Dense retriever (semantic similarity search)
dense_retriever = vector_store.as_retriever(
    search_kwargs={"k": 8}
)

# Stage 3: Sparse retriever (BM25 keyword search for corporate terms, policies, reports, and acronyms)
bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 8

# Stage 4: Hybrid search combining dense and sparse retrievers via Reciprocal Rank Fusion (RRF)
hybrid_retriever = EnsembleRetriever(
    retrievers=[dense_retriever, bm25_retriever],
    weights=[0.5, 0.5]
)

# ============================================================================
# STAGE 5: QUERY TRANSFORMATION
# ============================================================================

def transform_query(query: str) -> str:
    """
    Rewrite user queries to improve retrieval across dense and sparse retrievers
    without changing their original intent.
    """
    prompt = f"""You are a query rewriting assistant for a corporate knowledge and document RAG system.

    Rewrite the user's question into a concise, semantically rich corporate search query that will maximize recall across dense and keyword retrievers.

    Rules:
    - Preserve the user's original intent exactly.
    - Expand corporate terminology, abbreviations, and acronyms, and include relevant business synonyms (e.g. privacy policies, employee conduct, customer policies, financial reports, disclosures).
    - Do NOT attempt to answer the question.
    - Do NOT fabricate or introduce unmentioned items.
    - Return ONLY the rewritten query text.

    Original Question: {query}"""

    try:
        response = llm.invoke(prompt)
        transformed = response.content.strip()
        return transformed if transformed else query
    except Exception as e:
        print(f"[Warning] Query transformation failed ({e}), using original query.")
        return query

# ============================================================================
# STAGE 6: CROSS-ENCODER RERANKING
# ============================================================================

# Cross-Encoder model computes joint query-document attention scores
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_documents(query: str, docs: list[Document], top_k: int = 4) -> list[Document]:
    """
    Rerank candidate documents using a Cross-Encoder to compute full query-document
    joint attention scores. Preserves original metadata, filename, and page numbers.
    """
    if not docs:
        return []

    pairs = [[query, doc.page_content] for doc in docs]
    try:
        scores = cross_encoder.predict(pairs)
        scored_docs = list(zip(docs, scores))
        # Sort descending by cross-encoder score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        # Select top-k documents and strictly preserve all metadata
        reranked_docs = []
        for doc, score in scored_docs[:top_k]:
            reranked_docs.append(
                Document(
                    page_content=doc.page_content,
                    metadata={**doc.metadata, "rerank_score": float(score)}
                )
            )
        return reranked_docs
    except Exception as e:
        print(f"[Warning] Cross-encoder reranking failed ({e}), retaining candidate order.")
        return docs[:top_k]

# ============================================================================
# STAGE 7: CONTEXT COMPRESSION & RELEVANT PASSAGE EXTRACTION
# ============================================================================

def compress_context(query: str, docs: list[Document]) -> list[Document]:
    """
    Extract query-relevant passages from reranked documents while preserving
    corporate policies, employee guidelines, customer policies, reports, and source metadata alignment.
    """
    if not docs:
        return []

    compressed_docs: list[Document] = []
    for doc in docs:
        compression_prompt = f"""You are a corporate document passage compression assistant. Given a user query and an excerpt from company documents (privacy policies, employee policies, customer guidelines, reports, or disclosures):
        1. Extract ONLY the specific sentences, policy clauses, compliance rules, employee/customer requirements, guidelines, and metrics directly relevant to answering the query.
        2. Preserve exact terminology, dates, figures, definitions, and official policy constraints. Do NOT alter or hallucinate details.
        3. If the excerpt contains no relevant information for this query, reply with "NO_RELEVANT_INFO".
        4. Do NOT include greetings, preamble, or conversational comments.

        User Query: {query}

        Document Excerpt:
        {doc.page_content}

        Extracted Relevant Passages:"""
        try:
            res = llm.invoke(compression_prompt)
            extracted = res.content.strip()
            if not extracted or "NO_RELEVANT_INFO" in extracted:
                continue

            compressed_docs.append(
                Document(
                    page_content=extracted,
                    metadata=dict(doc.metadata)  # Preserves page, source, etc.
                )
            )
        except Exception as e:
            print(f"[Warning] Context compression failed for document ({e}), using full chunk.")
            compressed_docs.append(doc)

    # Fallback: If all documents were filtered out, preserve top reranked document
    if not compressed_docs and docs:
        compressed_docs = [docs[0]]

    return compressed_docs

# ============================================================================
# STAGE 8: PROGRAMMATIC CITATIONS & GROUNDED ANSWER GENERATION
# ============================================================================

def extract_metadata_citations(docs: list[Document]) -> list[dict]:
    """
    Programmatically extract structured citation metadata from documents.
    Guarantees accurate, un-hallucinated filenames and page numbers directly from chunks.
    """
    citations = []
    seen = set()
    for doc in docs:
        meta = doc.metadata or {}
        source = os.path.basename(meta.get("source") or meta.get("file_name") or "Document.pdf")
        page = meta.get("page_label") or meta.get("page_number")
        if page is None:
            raw_page = meta.get("page", 0)
            page = raw_page + 1 if isinstance(raw_page, int) else 1

        key = (source, str(page))
        if key not in seen:
            seen.add(key)
            citations.append({
                "source": source,
                "page": str(page),
                "citation": f"[{source}, Page {page}]"
            })
    return citations


def build_programmatic_citations_block(citations: list[dict] | list[str]) -> str:
    """
    Build a clean, deterministic citations section to attach to responses.
    """
    if not citations:
        return ""

    entries = []
    for c in citations:
        if isinstance(c, dict):
            entries.append(c["citation"])
        elif isinstance(c, str):
            c_clean = c.strip()
            entries.append(c_clean if c_clean.startswith("[") else f"[{c_clean}]")

    if not entries:
        return ""

    formatted = "\n".join(f"- {e}" for e in entries)
    return f"\n\n**Sources & Verified Citations:**\n{formatted}"


def extract_citations_from_messages(messages: list) -> list[str]:
    """
    Inspect message history to programmatically retrieve verified citations
    returned by rag_tool, avoiding LLM hallucinations.
    """
    for msg in reversed(messages):
        if getattr(msg, "type", "") == "tool" or msg.__class__.__name__ == "ToolMessage":
            content = getattr(msg, "content", "")
            if isinstance(content, dict):
                if "citations" in content and isinstance(content["citations"], list):
                    return content["citations"]
            elif isinstance(content, str):
                try:
                    import json
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "citations" in parsed:
                        return parsed["citations"]
                except Exception:
                    import re
                    matches = re.findall(r"\[([^\[\]]+\.pdf,\s*Page\s*\d+)\]", content)
                    if matches:
                        return [f"[{m}]" for m in dict.fromkeys(matches)]
    return []


CORPORATE_DISCLAIMER = (
    "*Company Disclaimer: The information provided is extracted directly from official company reference documents, "
    "policy manuals, employee/customer guidelines, and corporate reports for informational purposes.*"
)

def generate_grounded_answer(query: str, docs: list[Document]) -> str:
    """
    Generate an accurate, faithful corporate answer grounded strictly in the compressed context,
    with programmatic verified citations and standard policy disclaimers.
    """
    if not docs:
        return (
            "Based on the provided corporate documents, policies, and reports, there is insufficient evidence to answer this question.\n\n"
            f"{CORPORATE_DISCLAIMER}"
        )

    structured_citations = extract_metadata_citations(docs)
    citations_block = build_programmatic_citations_block(structured_citations)

    context_blocks = []
    for i, doc in enumerate(docs, start=1):
        meta = doc.metadata or {}
        page = meta.get("page_label") or meta.get("page_number") or (meta.get("page", 0) + 1)
        source = os.path.basename(meta.get("source") or meta.get("file_name") or "Document.pdf")
        context_blocks.append(f"[Excerpt {i} | Source: {source}, Page {page}]\n{doc.page_content}")

    context_str = "\n\n".join(context_blocks)

    generation_prompt = f"""You are a specialized corporate knowledge assistant referencing official company documents, including employee policies, customer policies, privacy notices, and corporate reports.

    Context Excerpts:
    {context_str}

    User Question: {query}

    Instructions:
    1. Ground your answer STRICTLY in the provided Context Excerpts. Do not extrapolate, assume, or introduce external claims.
    2. Reference specific source documents and page numbers where applicable.
    3. If the excerpts do not contain sufficient evidence to answer the question, explicitly state: "Based on the provided corporate documents, policies, and reports, there is insufficient evidence to answer this question."

    Answer:"""

    response = llm.invoke(generation_prompt)
    answer = response.content.strip()

    # Programmatically append verified citations derived directly from chunk metadata
    if citations_block and "**Sources & Verified Citations:**" not in answer:
        answer = f"{answer}{citations_block}"

    if CORPORATE_DISCLAIMER not in answer:
        answer = f"{answer}\n\n{CORPORATE_DISCLAIMER}"
    return answer

# ============================================================================
# STEP 3: INTEGRATION INTO RAG_TOOL & LANGGRAPH AGENT
# ============================================================================

@tool
def rag_tool(query: str) -> dict:
    """
    Retrieve relevant information from corporate company documents, privacy policies,
    employee policies, customer policies, guidelines, and corporate reports.
    Use this tool when the user asks questions about company policies, conduct, privacy,
    customer guidelines, employee rules, earnings, or business operations.
    """
    # 1. Query Transformation
    improved_query = transform_query(query)
    print("\n" + "=" * 50)
    print(f"Original Query:    {query}")
    print(f"Improved Query:    {improved_query}")

    # 2. Hybrid Retrieval (Dense FAISS + Sparse BM25 via RRF)
    raw_candidates = hybrid_retriever.invoke(improved_query)
    print(f"Hybrid Candidates: {len(raw_candidates)}")

    # 3. Cross-Encoder Reranking
    reranked_docs = rerank_documents(improved_query, raw_candidates, top_k=4)
    print(f"Reranked Top Docs: {len(reranked_docs)}")

    # 4. Context Compression
    compressed_docs = compress_context(improved_query, reranked_docs)
    print(f"Compressed Docs:   {len(compressed_docs)}")
    print("=" * 50 + "\n")

    # Programmatically extract verified citations directly from chunk metadata
    structured_citations = extract_metadata_citations(compressed_docs)
    citation_tags = [c["citation"] for c in structured_citations]
    citations_block = build_programmatic_citations_block(structured_citations)

    # Format excerpts with explicit source and page metadata for LLM grounding
    formatted_evidence = []
    for i, doc in enumerate(compressed_docs, start=1):
        meta = doc.metadata or {}
        source = os.path.basename(meta.get("source") or meta.get("file_name") or "Document.pdf")
        page = meta.get("page_label") or meta.get("page_number") or (meta.get("page", 0) + 1)
        formatted_evidence.append(f"[Excerpt {i} | Source: {source}, Page {page}]\n{doc.page_content}")

    return {
        "query": query,
        "improved_query": improved_query,
        "context": [doc.page_content for doc in compressed_docs],
        "metadata": [doc.metadata for doc in compressed_docs],
        "citations": citation_tags,
        "structured_citations": structured_citations,
        "citations_block": citations_block,
        "evidence": "\n\n".join(formatted_evidence) if formatted_evidence else "No relevant corporate documents found."
    }

# Bind tools to LLM
tools = [rag_tool]
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = f"""You are a specialized corporate knowledge assistant referencing official company documents, including privacy policies, employee policies, customer guidelines, and corporate reports.

When assisting users:
1. Always call `rag_tool` to retrieve evidence for questions regarding corporate policies, employee/customer guidelines, privacy rules, compliance, reports, or business operations.
2. Ground your final response STRICTLY in the evidence returned by `rag_tool`.
3. Reference the retrieved document names and page numbers in your discussion.
4. If the retrieved evidence does not contain sufficient information to answer the question, explicitly state: "Based on the provided corporate documents, policies, and reports, there is insufficient evidence to answer this question."
"""

def chat_node(state: RAGAgentSchema):
    messages = state.messages
    # Prepend system instruction if not already present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages_to_send = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
    else:
        messages_to_send = messages

    response = llm_with_tools.invoke(messages_to_send)

    # Programmatically attach verified citations derived directly from chunk metadata to the final answer
    if not getattr(response, "tool_calls", None) and hasattr(response, "content") and response.content:
        citations = extract_citations_from_messages(messages)
        content = response.content.strip()
        if citations:
            citations_block = build_programmatic_citations_block(citations)
            if citations_block and "**Sources & Verified Citations:**" not in content:
                content = f"{content}\n{citations_block}"

        if CORPORATE_DISCLAIMER not in content:
            content = f"{content}\n\n{CORPORATE_DISCLAIMER}"

        response = type(response)(
            content=content,
            id=getattr(response, "id", None),
            response_metadata=getattr(response, "response_metadata", {})
        )

    return {"messages": [response]}

tool_node = ToolNode(tools)

# Construct LangGraph workflow
graph = StateGraph(RAGAgentSchema)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile()
rag_agent = chatbot



if __name__ == "__main__":
    from IPython.display import Image

    try:
        img = Image(rag_agent.get_graph().draw_mermaid_png())
        with open("rag_agent_graph.png", "wb") as f:
            f.write(img.data)
    except Exception as e:
        print(f"[Notice] Graph image export skipped: {e}")

    result = chatbot.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Using the pdf notes, explain the company's privacy policy"
                    )
                )
            ]
        }
    )

    messages = result.messages if hasattr(result, "messages") else result["messages"]
    print(
        messages[-1]
        .content.encode("utf-8", errors="replace")
        .decode(sys.stdout.encoding or "utf-8", errors="replace")
    )
