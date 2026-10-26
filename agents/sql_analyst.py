import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv

load_dotenv()

import langchain_groq
from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from models.schema import AgentSchema, JudgeSchema
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

# -------------------------------------- AI Agent Code--------------------------------------
 

# ---------------------- Curate Question Node ----------------------

def curate_ques(state: AgentSchema) -> AgentSchema: 

    user_question = state.user_question # Bcz this is a Pydantic model object

    llm = pick_llm("low")  # Pick the appropriate LLM based on the level of the question

    prompt = f"""You are a question curator for an SQL analyst agent.
Clean, clarify, and rephrase the user's question into a concise, unambiguous natural language question suitable for SQL generation.
Do NOT write SQL queries, do NOT explain DBMS syntax, and do NOT answer the question.
Only return the curated natural language question text.

User Question: {user_question}"""

    response = llm.invoke(prompt).content.strip()

    state.curated_ques = response
    state.messages = state.messages + [HumanMessage(content=f"{response}")]  # Append the curated question to the messages list

    return state 

# ---------------------- Prompt Query Context Node ----------------------

def prompt_query_context(state: AgentSchema) -> AgentSchema:

    curated_question = state.curated_ques

    conn_details = {
        "host": os.environ.get('host', 'localhost'),
        "port": int(os.environ.get('port', 5432)),
        "user": os.environ.get('user', 'postgres'),
        "password": os.environ.get('password', ''),
        "dbname": os.environ.get('database', 'first')
    }

    obj = DatabaseUtil(conn_details)

    schema_info = obj.schema_details("public")  # Fetch schema details for the 'public' schema

    # Constructing the prompt query for the agent to generate the SQL query
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless the user explicitly asks for a specific number of rows, always limit the output to a maximum of 5 rows (e.g. LIMIT 5).
    Note - Just generate the raw SQL query without any explanation, markdown code blocks (no ```sql or ```), or additional text because
    this query will be executed directly on the database. The output should be SQL ready to be executed without any modifications.  
    
    User's Original Query: {curated_question}

    Database Schema Details:
    {schema_info}
    
    """    

    state.prompt_query_context = prompt

    return state


# ---------------------- Generate SQL Query Node ----------------------

def generate_sql(state: AgentSchema) -> AgentSchema:

    prompt = state.prompt_query_context

    llm = pick_llm("medium")  # Pick the appropriate LLM based on the level of the question

    generated_sql_query = llm.invoke(prompt).content.strip()  # Generate the SQL query using the LLM

    # Strip markdown code block formatting if returned by the LLM
    if generated_sql_query.startswith("```"):
        lines = generated_sql_query.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        generated_sql_query = "\n".join(lines).strip()

    state.generated_sql_query = generated_sql_query

    return state


# ---------------------- Is Safe Node ----------------------

# ------------------This one is by llm----------------------------

def is_safe_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    llm = pick_llm("medium")  
    llm_judge = llm.with_structured_output(JudgeSchema, method="json_mode")

    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.
    Return your response strictly as a JSON object with keys "answer" ("Yes" or "No") and "comments" (string).
    Here's the SQL query to evaluate:
    {sql_query}"""

    try:
        response = llm_judge.invoke(prompt)
        if hasattr(response, "model_dump"):
            data = response.model_dump()
        elif isinstance(response, dict):
            data = response
        else:
            data = {"answer": getattr(response, "answer", "No"), "comments": getattr(response, "comments", "")}
    except Exception as e:
        print(f"[Warning] Structured output fallback: {e}")
        raw = llm.invoke(f"{prompt}\n\nRespond with valid JSON: {{\"answer\": \"Yes\" or \"No\", \"comments\": \"...\"}}").content
        import json, re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            data = {"answer": "No", "comments": "Could not verify SQL safety."}

    state.is_safe = data.get('answer', 'No')
    state.comments = data.get('comments', '')

    return state


# ---------------------- Human-in-the-Loop (HITL) Node ----------------------

def human_approval(state: AgentSchema) -> AgentSchema:
    """
    Human-in-the-Loop (HITL) approval node.
    Presents the generated SQL query and judge evaluation to the human operator.
    - If approved: remains in the graph and proceeds to execute_sql.
    - If denied: updates state to unsafe and routes to canceled_sql.
    - If pending: pauses graph at awaiting_approval so the Web Frontend or API can prompt the user.
    """
    sql_query = state.generated_sql_query
    judge_status = state.is_safe
    judge_comments = state.comments
    user_q = state.curated_ques or state.user_question

    decision = ""
    # 1. Programmatic decision passed from API/Frontend
    if getattr(state, "approval_decision", None):
        decision = str(state.approval_decision).strip().lower()
    # 2. Interactive CLI input (if running inside a real terminal interactive session)
    elif sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        print("\n" + "=" * 60)
        print(" [HITL] HUMAN-IN-THE-LOOP APPROVAL REQUIRED")
        print("=" * 60)
        print(f"User Question:          {user_q}")
        print(f"Generated SQL Query:    {sql_query}")
        print(f"Automated Safety Check: {judge_status}")
        print(f"Judge Comments:         {judge_comments}")
        print("-" * 60)
        try:
            decision = input("Do you approve executing this SQL query? (approve/yes to execute, deny/no to cancel): ").strip().lower()
        except (EOFError, OSError):
            decision = ""
    # 3. Non-interactive / Web Server mode:
    else:
        auto_decision = os.environ.get("HITL_AUTO_APPROVE", "").strip().lower()
        if auto_decision in ["yes", "y", "true", "1", "approve"]:
            decision = "approve"
        elif auto_decision in ["no", "n", "false", "0", "deny"]:
            decision = "deny"
        else:
            decision = "pending"

    if decision in ["approve", "approved", "yes", "y"]:
        state.is_safe = "Yes"
        state.needs_approval = False
        state.comments = f"Approved by human operator. (Judge: {judge_comments})"
        print(">> [HITL Decision]: APPROVED. Proceeding to execute SQL.\n")
    elif decision in ["deny", "denied", "no", "n", "cancel"]:
        state.is_safe = "No"
        state.needs_approval = False
        state.comments = f"Denied by human operator during HITL review. (Judge: {judge_comments})"
        print(">> [HITL Decision]: DENIED. Routing to canceled_sql.\n")
    else:
        # Awaiting human decision via Web Frontend
        state.needs_approval = True
        state.comments = f"Awaiting human approval before execution. (Judge: {judge_comments})"
        print(">> [HITL Decision]: PENDING. Handing off to human operator.\n")

    return state


# Awaiting Approval Node
def awaiting_approval(state: AgentSchema) -> AgentSchema:
    judge_comments = state.comments or "Safety review required before execution."
    state.final_answer = (
        f"⚠️ Human-in-the-Loop review is required before this SQL query can be executed.\n\n"
        f"**Generated SQL Query:**\n```sql\n{state.generated_sql_query}\n```\n\n"
        f"**Safety Assessment:** {state.is_safe}\n"
        f"**Judge Reason:** {judge_comments}\n\n"
        f"Please approve or deny execution using the review controls above."
    )
    state.messages = state.messages + [AIMessage(content=state.final_answer)]
    return state


# Canceled SQL Query Node
def canceled_sql(state: AgentSchema) -> AgentSchema:

    comments = state.comments

    state.final_answer = f"The generated SQL query was canceled. Reason: {comments}. Therefore, the SQL query was not executed."
    state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")]  # Append the final answer to the messages list  

    return state


# Execute SQL Query Node
def execute_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    conn_details = {
        "host": os.environ.get('host', 'localhost'),
        "port": int(os.environ.get('port', 5432)),
        "user": os.environ.get('user', 'postgres'),
        "password": os.environ.get('password', ''),
        "dbname": os.environ.get('database', 'first')
    }

    obj = DatabaseUtil(conn_details)

    execution_result = obj.execute_sql(sql_query)  # Execute the SQL query on the database

    state.sql_query_execution_result = execution_result

    return state


# Represent the final answer Node
def represent_final_answer(state: AgentSchema) -> AgentSchema:

    execution_result = state.sql_query_execution_result
    curated_question = state.curated_ques

    llm = pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """

    llm_response = llm.invoke(prompt).content  # Get the final answer from the LLM

    state.final_answer = llm_response
    state.messages = state.messages + [AIMessage(content=f"{llm_response}")]  # Append the final answer to the messages list

    return state


# ------------------------------------------- Graph Building -------------------------------------------

sql_agent_graph = StateGraph(AgentSchema)

# Nodes
sql_agent_graph.add_node("curate_ques", curate_ques)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql", generate_sql)
sql_agent_graph.add_node("is_safe_sql", is_safe_sql)
sql_agent_graph.add_node("human_approval", human_approval)
sql_agent_graph.add_node("awaiting_approval", awaiting_approval)
sql_agent_graph.add_node("canceled_sql", canceled_sql)
sql_agent_graph.add_node("execute_sql", execute_sql)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)

# Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")

# Conditional Edge Function from is_safe_sql
def check_safety_edge(state: AgentSchema) -> str:
    # If human review was explicitly requested for this query
    if getattr(state, "require_approval", False):
        return "human_approval"

    is_safe = state.is_safe
    if is_safe and is_safe.lower() in ["yes", "approved", "approve"]:
        return "execute_sql"
    else:
        return "human_approval"

sql_agent_graph.add_conditional_edges("is_safe_sql", check_safety_edge,
                                      {
                                          "execute_sql": "execute_sql",
                                          "human_approval": "human_approval"
                                      })

# Conditional Edge Function for Human-in-the-Loop (HITL)
def hitl_approval_edge(state: AgentSchema) -> str:
    if getattr(state, "needs_approval", False):
        return "awaiting_approval"

    is_safe = state.is_safe
    if is_safe and is_safe.lower() in ["yes", "approved", "approve"]:
        return "execute_sql"
    else:
        return "canceled_sql"

sql_agent_graph.add_conditional_edges("human_approval", hitl_approval_edge,
                                      {
                                          "execute_sql": "execute_sql",
                                          "canceled_sql": "canceled_sql",
                                          "awaiting_approval": "awaiting_approval"
                                      })

sql_agent_graph.add_edge("awaiting_approval", END)
sql_agent_graph.add_edge("canceled_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)


# Compile the Graph
sql_analyst = sql_agent_graph.compile()


# 

if __name__ == "__main__":


    # Optional
    from IPython.display import display, Image
    img = Image(sql_analyst.get_graph().draw_mermaid_png())
    with open("sql_analyst_graph.png", "wb") as f:
        f.write(img.data)

    input_schema = {
        "messages": [],
        "user_question": "Retrieve the names and salaries of the top 2 highest-paid employees in our database",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    # Execute the Graph
    sql_analyst_response = sql_analyst.invoke(input_schema)
    print(sql_analyst_response['messages'])  # Print the final output of the graph execution
    print("********************************")

    print(sql_analyst_response['generated_sql_query'])  # Print the generated SQL query

    print("********************************")

    print(sql_analyst_response['sql_query_execution_result'])  # Print the result of executing the SQL query

    print("********************************")

    print(sql_analyst_response['prompt_query_context'])  # Print the prompt query context