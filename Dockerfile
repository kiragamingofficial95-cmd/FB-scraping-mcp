# Standalone Docker container for Facebook Search Scraper & MCP Server
FROM python:3.12-slim

WORKDIR /app

# Copy source code and installation files
COPY pyproject.toml requirements.txt ./
COPY facebook_search_scraper/ facebook_search_scraper/
COPY main.py ./

# Install package
RUN pip install --no-cache-dir .

# Default entry point
ENTRYPOINT ["facebook-search-scraper"]
CMD ["--help"]
