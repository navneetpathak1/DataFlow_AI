import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_pick import pick_llm
from models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst
from agents.rag import chatbot as rag_agent


llm = pick_llm("medium")

llm_router = llm.with_structured_output(RouterSchema)


# ---------------------------- DATA AGENT GRAPH ---------------------------- #


def router_node(state: DataAgentSchema):

    message = state.messages[-1].content

    router_prompt = (
        "You are an expert request router. Analyze the user's message and determine the correct destination:\n"
        "- 'sql': For queries asking to inspect, query, or retrieve data from relational database tables (e.g. users, rides, payments, ratings, vehicles).\n"
        "- 'etl': For requests to extract data from APIs/URLs, transform data (filtering, cleaning, formatting CSV/JSON), or load data pipelines.\n"
        "- 'rag': For medical, clinical, healthcare questions, diseases, symptoms, treatment options, or queries answerable from medical encyclopedia/reference documents.\n\n"
        f"User message: {message}"
    )

    route_response_dict = llm_router.invoke(router_prompt).model_dump()

    route_response = route_response_dict['answer']

    state.route_response = route_response

    return state

def etl_node(state: DataAgentSchema):

    message = state.messages[-1].content

    response = etl_analyst.invoke(
        {"messages": [HumanMessage(content=message)]}
    )
    last_message = response.messages[-1] if hasattr(response, "messages") else response["messages"][-1]
    state.messages = state.messages + [last_message]

    return state

def sql_node(state: DataAgentSchema):

    message = state.messages[-1].content

    input_schema = {
        "messages": [],
        "user_question": f"{message}",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    response = sql_analyst.invoke(input_schema)

    last_message = response.messages[-1] if hasattr(response, "messages") else response["messages"][-1]
    state.messages = state.messages + [last_message]

    return state


def rag_node(state: DataAgentSchema):

    message = state.messages[-1].content

    response = rag_agent.invoke(
        {"messages": [HumanMessage(content=message)]}
    )

    last_message = response.messages[-1] if hasattr(response, "messages") else response["messages"][-1]
    state.messages = state.messages + [last_message]

    return state


data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)
data_agent_graph.add_node("rag_node", rag_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    elif state.route_response == "rag":
        return "rag_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


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
        from IPython.display import display, Image
        img = Image(data_agent.get_graph().draw_mermaid_png())
        with open("data_agent_graph.png", "wb") as f:
            f.write(img.data)
    except Exception as e:
        print(f"Could not save graph image: {e}")

    response = data_agent.invoke(
        {
            "messages": [
                HumanMessage(content="Using the medical notes, explain the treatment options for cancer")
            ],
            "route_response": ""
        }
    )

    last_msg = response.messages[-1] if hasattr(response, "messages") else response["messages"][-1]
    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    print(content.encode("utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"))
 


