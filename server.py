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

HOST = os.environ.get("SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("SERVER_PORT", 8000))


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
                if not question:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self._set_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "Question cannot be empty"}).encode("utf-8"))
                    return

                print(f"\n[DataAgent Server] Processing query: {question}")
                start_time = datetime.now()

                # Invoke DataAgent
                response = data_agent.invoke(
                    {
                        "messages": [HumanMessage(content=question)],
                        "route_response": ""
                    }
                )

                elapsed = (datetime.now() - start_time).total_seconds()

                # Extract last message and route
                messages = response.messages if hasattr(response, "messages") else response.get("messages", [])
                last_msg = messages[-1] if messages else None
                content = last_msg.content if last_msg and hasattr(last_msg, "content") else str(last_msg)

                route_response = getattr(response, "route_response", "") or (response.get("route_response") if isinstance(response, dict) else "")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._set_cors_headers()
                self.end_headers()

                result_payload = {
                    "success": True,
                    "route": route_response,
                    "result": content,
                    "elapsedSeconds": round(elapsed, 2),
                    "timestamp": datetime.now().isoformat()
                }

                self.wfile.write(json.dumps(result_payload).encode("utf-8"))
                print(f"[DataAgent Server] Query resolved in {elapsed:.2f}s (Route: {route_response})")

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
