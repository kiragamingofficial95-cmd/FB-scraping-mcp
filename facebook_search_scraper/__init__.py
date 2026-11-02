"""
Facebook Search Scraper
Independent, high-performance Facebook data extraction software and MCP server.
"""

from .scraper import FacebookSearchScraper
from .mcp_server import MCPServer
from .exporters import export_to_json, export_to_jsonl, export_to_csv

__version__ = "1.0.0"
__all__ = [
    "FacebookSearchScraper",
    "MCPServer",
    "export_to_json",
    "export_to_jsonl",
    "export_to_csv",
]
