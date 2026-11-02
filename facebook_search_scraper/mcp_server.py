import json
import logging
import sys
from typing import Any, Dict, Optional

from .scraper import FacebookSearchScraper

logger = logging.getLogger("mcp_server")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s [MCP] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

MCP_PROTOCOL_VERSION = "2024-11-05"

TOOL_SPECIFICATION = {
    "name": "facebook_search_scraper",
    "description": (
        "Search and scrape Facebook data: extract pages, profiles, posts, and reels. "
        "Returns full contact details (email, phone, address, website), follower/like metrics, "
        "ratings, page ID, and Meta ad status without requiring Facebook login."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["categories"],
        "properties": {
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords, business categories, or page handles to search (e.g. ['Coffee Shop', 'Restaurant']).",
            },
            "locations": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Optional location filters (e.g. ['Montreal', 'New York', 'Paris']).",
            },
            "searchType": {
                "type": "string",
                "enum": ["pages-google", "pages", "profiles", "posts", "reels"],
                "default": "pages-google",
                "description": "Target result type: 'pages-google' (default), 'pages', 'profiles', 'posts', or 'reels'.",
            },
            "resultsLimit": {
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "description": "Maximum number of items to return.",
            },
        },
    },
}


class MCPServer:
    """Standard Model Context Protocol (MCP) server running over JSON-RPC 2.0 stdio."""

    def __init__(self, proxy: Optional[str] = None):
        self.scraper = FacebookSearchScraper(proxy=proxy)

    def run(self):
        """Read line-delimited JSON-RPC from sys.stdin, write to sys.stdout."""
        logger.info("Facebook Search Scraper MCP server running on stdio...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                resp = self.handle_message(msg)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                logger.error(f"Error handling MCP line: {e}")
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Server error: {str(e)}"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

    def handle_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "facebook-search-scraper",
                        "version": "1.0.0",
                    },
                },
            }

        elif method == "notifications/initialized":
            logger.info("MCP client acknowledged initialization.")
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [TOOL_SPECIFICATION],
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name != "facebook_search_scraper":
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found",
                    },
                }

            categories = args.get("categories", [])
            locations = args.get("locations", [])
            search_type = args.get("searchType", "pages-google")
            limit = args.get("resultsLimit", 20)

            logger.info(f"Executing scraper: categories={categories}, locations={locations}, limit={limit}")
            try:
                items = self.scraper.run(
                    categories=categories,
                    locations=locations,
                    search_type=search_type,
                    results_limit=limit,
                )
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(items, indent=2, ensure_ascii=False),
                            }
                        ]
                    },
                }
            except Exception as e:
                logger.error(f"Error executing scraper: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "isError": True,
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: {str(e)}",
                            }
                        ],
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not implemented",
                },
            }

    def run_http(self, host: str = "127.0.0.1", port: int = 8000):
        """Run MCP server over HTTP JSON-RPC & SSE endpoints."""
        from http.server import BaseHTTPRequestHandler, HTTPServer

        server_instance = self

        class MCPHTTPHandler(BaseHTTPRequestHandler):
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()

            def do_GET(self):
                if self.path in ("/sse", "/sse/"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    init_event = json.dumps({"type": "endpoint", "url": f"http://{host}:{port}/mcp"})
                    self.wfile.write(f"event: endpoint\ndata: {init_event}\n\n".encode("utf-8"))
                    self.wfile.flush()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    status_info = {
                        "status": "online",
                        "server": "facebook-search-scraper",
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "endpoints": {"mcp": "/mcp", "sse": "/sse"},
                    }
                    self.wfile.write(json.dumps(status_info, indent=2).encode("utf-8"))

            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8")
                try:
                    req_data = json.loads(body)
                    resp_data = server_instance.handle_message(req_data)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    if resp_data is not None:
                        self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode("utf-8"))
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

            def log_message(self, format, *args):
                logger.info(f"{self.client_address[0]} - {format % args}")

        httpd = HTTPServer((host, port), MCPHTTPHandler)
        logger.info(f"Facebook Search Scraper MCP HTTP server listening at http://{host}:{port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Stopping HTTP MCP server...")
            httpd.server_close()


def main():
    if "--http" in sys.argv or "--port" in sys.argv:
        port = 8000
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        server = MCPServer()
        server.run_http(port=port)
    else:
        server = MCPServer()
        server.run()


if __name__ == "__main__":
    main()
