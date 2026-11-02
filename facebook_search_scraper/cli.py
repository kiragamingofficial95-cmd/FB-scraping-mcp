import argparse
import json
import logging
import os
import sys
from typing import Any, Dict

from .exporters import export_to_csv, export_to_json, export_to_jsonl
from .mcp_server import main as run_mcp_server
from .scraper import FacebookSearchScraper


def setup_logger(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        prog="facebook-search-scraper",
        description="Standalone Facebook Search Scraper & MCP Server.",
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Run as Model Context Protocol (MCP) server over stdio",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run MCP server over HTTP / SSE transport (e.g. http://127.0.0.1:8000/)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP MCP server (default: 8000)",
    )
    parser.add_argument(
        "-c",
        "--categories",
        nargs="+",
        help="Keywords, business types, or handles (e.g. 'Coffee Shop' 'Bakery')",
    )
    parser.add_argument(
        "-l",
        "--locations",
        nargs="+",
        default=[],
        help="Locations to apply to each search (e.g. 'Montreal' 'New York')",
    )
    parser.add_argument(
        "-t",
        "--search-type",
        default="pages-google",
        choices=["pages-google", "pages", "profiles", "posts", "reels"],
        help="Target result type (default: pages-google)",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=20,
        help="Maximum results to extract (default: 20)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path (e.g. results.json, results.csv, results.jsonl)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "jsonl", "csv"],
        default=None,
        help="Export format (auto-detected from output file extension if omitted)",
    )
    parser.add_argument(
        "-p",
        "--proxy",
        default=None,
        help="Optional HTTP/HTTPS proxy URL",
    )
    parser.add_argument(
        "-i",
        "--input",
        default=None,
        help="Path to JSON configuration file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()

    # 1. MCP Mode
    if args.mcp:
        run_mcp_server()
        return
    if args.http:
        from .mcp_server import MCPServer
        server = MCPServer(proxy=args.proxy)
        server.run_http(port=args.port)
        return

    setup_logger(args.verbose)

    # 2. Config File Loading
    input_data: Dict[str, Any] = {}
    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)

    categories = args.categories or input_data.get("categories", [])
    locations = args.locations or input_data.get("locations", [])
    search_type = args.search_type or input_data.get("searchType", "pages-google")
    limit = args.limit or input_data.get("resultsLimit", 20)
    proxy = args.proxy or input_data.get("proxy")

    if not categories:
        parser.print_help()
        print("\n[!] Error: No search categories or keywords provided.")
        print("Example: facebook-search-scraper -c 'Coffee Shop' -l 'Montreal' -n 10 -o results.json")
        sys.exit(1)

    scraper = FacebookSearchScraper(proxy=proxy)
    results = scraper.run(
        categories=categories,
        locations=locations,
        search_type=search_type,
        results_limit=limit,
    )

    # Determine export format
    fmt = args.format
    if not fmt and args.output:
        ext = os.path.splitext(args.output)[1].lower()
        if ext == ".csv":
            fmt = "csv"
        elif ext in (".jsonl", ".ndjson"):
            fmt = "jsonl"
        else:
            fmt = "json"
    elif not fmt:
        fmt = "json"

    # Export or print
    if args.output:
        if fmt == "csv":
            export_to_csv(results, args.output)
        elif fmt == "jsonl":
            export_to_jsonl(results, args.output)
        else:
            export_to_json(results, args.output)
        print(f"[OK] Saved {len(results)} items to {args.output} ({fmt.upper()})")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
