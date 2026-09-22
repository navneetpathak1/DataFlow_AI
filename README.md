# 🤖 DataAgent: Autonomous Multi-Agent Data & Knowledge Platform

## 📖 About the Project

**DataAgent** is an intelligent, multi-agent AI system designed to automate data operations, database analytics, and document knowledge retrieval. Built with a hierarchical supervisor architecture using **LangGraph**, it dynamically interprets natural language user requests and routes them to specialized agents:

1. **Text-to-SQL Analyst Agent (`sql_node`)**:
   - Performs automated schema introspection on live PostgreSQL databases (tables, columns, types, and sample records).
   - Curates and standardizes user questions to generate accurate Postgres SQL queries.
   - Features an **AI Safety Judge** that inspects generated queries to block harmful DDL/DML mutations (`DROP`, `DELETE`, `UPDATE`, `TRUNCATE`, `ALTER`) before execution.
   - Executes safe queries and synthesizes conversational, insight-rich answers.

2. **Autonomous ETL Agent (`etl_node`)**:
   - Extracts data from external REST APIs and endpoints.
   - Dynamically inspects data structures and generates custom Pandas transformation scripts on-the-fly.
   - Filters, cleans, and saves datasets across formats including CSV, JSON, and Parquet.

3. **Medical Knowledge RAG Agent (`rag_node`)**:
   - Implements a Retrieval-Augmented Generation (RAG) pipeline over extensive medical encyclopedia documentation.
   - Uses semantic chunking and dense vector embeddings to retrieve relevant clinical contexts.
   - Powered by a local persistent FAISS vector store and LangGraph ReAct tool-calling loop to answer factual, clinical, and health queries.

4. **Supervisor Router (`router_node`)**:
   - Uses structured LLM outputs (`RouterSchema`) to classify queries into `sql`, `etl`, or `rag`, directing each request to the right specialized agent.

---

## 🛠️ Tech Stack Used

| Technology / Library | Category | Description |
| :--- | :--- | :--- |
| **[Python 3.13+](https://www.python.org/)** | Programming Language | Core runtime environment managed with `uv`. |
| **[LangGraph](https://github.com/langchain-ai/langgraph)** | Agent Orchestration | Builds stateful, cyclical, multi-agent graphs and supervisor routing workflows. |
| **[LangChain](https://github.com/langchain-ai/langchain)** | Agent Framework | Tool bindings, message abstractions (`HumanMessage`, `AIMessage`, `ToolMessage`), and prompt orchestration. |
| **[Groq (`ChatGroq`)](https://groq.com/)** | LLM Inference | Ultra-low latency model inference running `openai/gpt-oss-120b`. |
| **[FAISS (`faiss-cpu`)](https://github.com/facebookresearch/faiss)** | Vector Database | Local vector indexing and similarity search for RAG document retrieval. |
| **[HuggingFace / Sentence-Transformers](https://huggingface.co/sentence-transformers)** | Embeddings | Generates dense embeddings using `sentence-transformers/all-MiniLM-L6-v2`. |
| **[PyPDF](https://pypdf.readthedocs.io/)** | Document Loader | Parses and extracts text content from PDF reference documents. |
| **[PostgreSQL](https://www.postgresql.org/)** | Relational Database | Production database storing structured business datasets (users, rides, payments, ratings, vehicles). |
| **[psycopg2-binary](https://www.psycopg.org/)** | Database Driver | Handles PostgreSQL connections, schema introspection, and analytical query execution. |
| **[Pydantic v2](https://docs.pydantic.dev/)** | Validation & Schemas | Type-safe state management, router classification schemas, and safety evaluation contracts. |
| **[python-dotenv](https://github.com/theskumar/python-dotenv)** | Configuration | Loads sensitive API keys and database credentials securely from environment variables. |
