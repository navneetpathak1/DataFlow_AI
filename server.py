import os
import sys
import json
import traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Set utf-8 encoding for standard output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv()

from agents.data_agent import data_agent
from langchain_core.messages import HumanMessage

 
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", "8000")))


class DataAgentHandler(BaseHTTPRequestHandler):

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            response_data = {
                "status": "online",
                "service": "DataAgent API",
                "time": datetime.now().isoformat(),
                "endpoints": ["/api/health", "/api/query"]
            }
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/query":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body) if body else {}

                question = data.get("question", "").strip()
                require_approval = bool(data.get("require_approval", False))
                approval_decision = data.get("approval_decision", None)

                if not question:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "Question cannot be empty"}).encode("utf-8"))
                    return

                print(f"\n[DataAgent Server] Processing query: {question} (Require HITL: {require_approval})")
                start_time = datetime.now()

                # Invoke DataAgent
                response = data_agent.invoke(
                    {
                        "messages": [HumanMessage(content=question)],
                        "route_response": "",
                        "require_approval": require_approval,
                        "approval_decision": approval_decision
                    }
                )

                elapsed = (datetime.now() - start_time).total_seconds()

                # Extract last message and route
                messages = response.messages if hasattr(response, "messages") else response.get("messages", [])
                last_msg = messages[-1] if messages else None
                content = last_msg.content if last_msg and hasattr(last_msg, "content") else str(last_msg)

                route_response = getattr(response, "route_response", "") or (response.get("route_response") if isinstance(response, dict) else "")
                needs_approval = bool(getattr(response, "needs_approval", False) if hasattr(response, "needs_approval") else response.get("needs_approval", False))
                approval_data = getattr(response, "approval_data", None) if hasattr(response, "approval_data") else response.get("approval_data", None)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._set_cors_headers()
                self.end_headers()

                result_payload = {
                    "success": True,
                    "route": route_response,
                    "result": content,
                    "needs_approval": needs_approval,
                    "approval_data": approval_data,
                    "elapsedSeconds": round(elapsed, 2),
                    "timestamp": datetime.now().isoformat()
                }

                self.wfile.write(json.dumps(result_payload).encode("utf-8"))
                print(f"[DataAgent Server] Query resolved in {elapsed:.2f}s (Route: {route_response}, Needs Approval: {needs_approval})")

            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

        elif self.path == "/api/approve-sql":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body) if body else {}

                decision = str(data.get("decision", "denied")).strip().lower()
                sql_query = data.get("sql_query", "").strip()
                user_question = data.get("user_question", "").strip()
                curated_ques = data.get("curated_ques", user_question).strip()

                print(f"\n[DataAgent Server] HITL Decision received: {decision.upper()} for query:\n{sql_query}")
                start_time = datetime.now()

                from agents.sql_analyst import execute_sql, represent_final_answer
                from models.schema import AgentSchema

                state = AgentSchema(
                    messages=[],
                    user_question=user_question or "Execute approved query",
                    curated_ques=curated_ques or user_question or "Execute approved query",
                    prompt_query_context="",
                    generated_sql_query=sql_query,
                    is_safe="Yes" if decision in ["approve", "approved", "yes", "y"] else "No",
                    comments=f"Decision '{decision}' provided by human operator via UI.",
                    sql_query_execution_result="",
                    final_answer="",
                    approval_decision=decision,
                    needs_approval=False,
                    require_approval=False
                )

                if decision in ["approve", "approved", "yes", "y"]:
                    state = execute_sql(state)
                    state = represent_final_answer(state)
                    status_text = "Query approved and executed successfully."
                else:
                    state.final_answer = (
                        f"The SQL execution was denied by human operator.\n\n"
                        f"Query that was canceled:\n```sql\n{sql_query}\n```\n"
                        "No database changes were executed."
                    )
                    status_text = "Query execution denied by human operator."

                elapsed = (datetime.now() - start_time).total_seconds()

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._set_cors_headers()
                self.end_headers()

                payload = {
                    "success": True,
                    "route": "sql",
                    "decision": decision,
                    "status_text": status_text,
                    "sql_query": sql_query,
                    "execution_result": state.sql_query_execution_result,
                    "result": state.final_answer,
                    "needs_approval": False,
                    "elapsedSeconds": round(elapsed, 2),
                    "timestamp": datetime.now().isoformat()
                }

                self.wfile.write(json.dumps(payload).encode("utf-8"))
                print(f"[DataAgent Server] HITL Action finalized ({decision}) in {elapsed:.2f}s")

            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))


    def log_message(self, format, *args):
        # Custom clean logging
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} -> {args[2]}\n")


def run_server():
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, DataAgentHandler)
    print(f"DataAgent API Server listening at http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
