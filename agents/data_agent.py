import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from utils.llm_pick import pick_llm
from models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst
from agents.rag import chatbot as rag_agent


llm = pick_llm("medium")
llm_router = llm.with_structured_output(RouterSchema)


# ---------------------------- HELPER FUNCTIONS ---------------------------- #

def _get_latest_user_message(state: DataAgentSchema) -> str:
    """Safely extracts the latest user query from the message history."""
    if not state.messages:
        return ""

    for msg in reversed(state.messages):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            content = getattr(msg, "content", "")
            return content if isinstance(content, str) else str(content)

    last_msg = state.messages[-1]
    return last_msg.content if hasattr(last_msg, "content") else str(last_msg)


def _to_ai_message(response_obj) -> AIMessage:
    """Converts subagent response output into a standardized AIMessage."""
    if isinstance(response_obj, AIMessage):
        return response_obj
    if hasattr(response_obj, "content"):
        return AIMessage(content=str(response_obj.content))
    return AIMessage(content=str(response_obj))


# ---------------------------- DATA AGENT GRAPH ---------------------------- #

def router_node(state: DataAgentSchema) -> dict:
    message = _get_latest_user_message(state)

    router_prompt = (
        "You are an expert request router. Analyze the user's message and determine the correct destination:\n"
        "- 'sql': For queries asking to inspect, query, or retrieve data from relational database tables (e.g. store, employee, customer, sales).\n"
        "- 'etl': For requests to extract data from APIs/URLs, transform data (filtering, cleaning, formatting CSV/JSON), or load data pipelines.\n"
        "- 'rag': For company privacy policy, company overview, company information, questions about the company, or anything that does not fall under sql or etl.\n\n"
        f"User message: {message}"
    )

    route_response = "rag"
    try:
        route_result = llm_router.invoke(router_prompt)
        if hasattr(route_result, "model_dump"):
            data = route_result.model_dump()
        elif isinstance(route_result, dict):
            data = route_result
        else:
            data = {"answer": getattr(route_result, "answer", "rag")}
        route_response = str(data.get("answer", "rag")).strip().lower()
    except Exception as e:
        print(f"[Warning] Router structured output fallback: {e}")
        fallback_prompt = (
            "Classify the following query into exactly one category: 'sql', 'etl', or 'rag'.\n"
            f"Query: {message}\n"
            "Respond with ONLY one word ('sql', 'etl', or 'rag'):"
        )
        try:
            raw = llm.invoke(fallback_prompt).content.strip().lower()
            if "sql" in raw:
                route_response = "sql"
            elif "etl" in raw:
                route_response = "etl"
            else:
                route_response = "rag"
        except Exception:
            route_response = "rag"

    # Normalize to known destinations
    if "sql" in route_response:
        clean_route = "sql"
    elif "etl" in route_response:
        clean_route = "etl"
    else:
        clean_route = "rag"

    return {"route_response": clean_route}


def etl_node(state: DataAgentSchema) -> dict:
    message = _get_latest_user_message(state)

    response = etl_analyst.invoke(
        {"messages": [HumanMessage(content=message)]}
    )

    msgs = response.messages if hasattr(response, "messages") else response.get("messages", [])
    last_msg = msgs[-1] if msgs else AIMessage(content="ETL process completed.")

    return {"messages": [_to_ai_message(last_msg)]}


def sql_node(state: DataAgentSchema) -> dict:
    message = _get_latest_user_message(state)

    input_schema = {
        "messages": [],
        "user_question": message,
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": "",
        "approval_decision": getattr(state, "approval_decision", None),
        "require_approval": getattr(state, "require_approval", False)
    }

    response = sql_analyst.invoke(input_schema)

    # Check final_answer first, then last message
    final_ans = None
    if isinstance(response, dict):
        final_ans = response.get("final_answer")
        msgs = response.get("messages", [])
        last_msg = msgs[-1] if msgs else None
        needs_approval = bool(response.get("needs_approval", False))
        gen_sql = response.get("generated_sql_query", "")
        judge_status = response.get("is_safe", "No")
        judge_comments = response.get("comments", "")
        curated_q = response.get("curated_ques", message)
    else:
        final_ans = getattr(response, "final_answer", None)
        msgs = getattr(response, "messages", [])
        last_msg = msgs[-1] if msgs else None
        needs_approval = bool(getattr(response, "needs_approval", False))
        gen_sql = getattr(response, "generated_sql_query", "")
        judge_status = getattr(response, "is_safe", "No")
        judge_comments = getattr(response, "comments", "")
        curated_q = getattr(response, "curated_ques", message)

    if final_ans:
        result_message = AIMessage(content=str(final_ans))
    elif last_msg:
        result_message = _to_ai_message(last_msg)
    else:
        result_message = AIMessage(content="SQL query execution completed.")

    approval_data = None
    if needs_approval:
        approval_data = {
            "sql_query": gen_sql,
            "judge_status": judge_status,
            "judge_comments": judge_comments,
            "user_question": message,
            "curated_ques": curated_q
        }

    return {
        "messages": [result_message],
        "needs_approval": needs_approval,
        "approval_data": approval_data
    }


def rag_node(state: DataAgentSchema) -> dict:
    message = _get_latest_user_message(state)

    response = rag_agent.invoke(
        {"messages": [HumanMessage(content=message)]}
    )

    msgs = response.messages if hasattr(response, "messages") else response.get("messages", [])
    last_msg = msgs[-1] if msgs else AIMessage(content="No relevant information found.")

    return {"messages": [_to_ai_message(last_msg)]}


# ---------------------------- GRAPH DEFINITION ---------------------------- #

data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)
data_agent_graph.add_node("rag_node", rag_node)

data_agent_graph.add_edge(START, "router_node")


def route_edge(state: DataAgentSchema) -> str:
    route = (state.route_response or "").strip().lower()
    if "sql" in route:
        return "sql_node"
    elif "etl" in route:
        return "etl_node"
    elif "rag" in route:
        return "rag_node"
    else:
        return "rag_node"


data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "sql_node": "sql_node",
        "etl_node": "etl_node",
        "rag_node": "rag_node"
    }
)

data_agent_graph.add_edge("sql_node", END)
data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("rag_node", END)

data_agent = data_agent_graph.compile()


if __name__ == "__main__":
    # Optional graph visualization
    try:
        from IPython.display import Image
        img = Image(data_agent.get_graph().draw_mermaid_png())
        with open("data_agent_graph.png", "wb") as f:
            f.write(img.data)
    except Exception as e:
        print(f"Could not save graph image: {e}")

    test_queries = [
        "What are the top 2 highest paid employees in our store database?",
        "Explain the company's privacy policy regarding customer personal information."
    ]

    for q in test_queries:
        print("\n" + "=" * 60)
        print(f"Testing Query: {q}")
        print("=" * 60)
        res = data_agent.invoke(
            {
                "messages": [HumanMessage(content=q)],
                "route_response": ""
            }
        )
        print(f"Route selected: {res.route_response if hasattr(res, 'route_response') else res.get('route_response')}")
        last = res.messages[-1] if hasattr(res, "messages") else res.get("messages", [])[-1]
        print(f"Total messages in history: {len(res.messages if hasattr(res, 'messages') else res.get('messages', []))}")
        print("Answer:\n", getattr(last, "content", str(last)))
