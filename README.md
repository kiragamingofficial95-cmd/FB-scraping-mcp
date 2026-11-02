# Facebook Search Scraper & MCP Server

A high-performance, standalone software suite and native **Model Context Protocol (MCP)** server to search and extract public Facebook data — including **Pages, Profiles, Posts, and Reels** — without requiring Facebook login credentials, API keys, or paid platform subscriptions.

---

## 🌟 Key Features

- **100% Independent & Free**: Self-contained software with zero dependency on third-party cloud actor platforms or paid APIs.
- **Deep Contact & Lead Extraction**:
  - 📇 Title, Vanity Handle (`pageName`), Profile Link (`pageUrl`)
  - 🆔 Facebook ID (`pageId`, `facebookId`)
  - 📑 Business Categories (`categories`)
  - 📧 Email Address
  - 📱 Contact Phone Number
  - 🏠 Full Physical Address with Google Maps & Bing Maps directions
  - 🌐 Official Website & Social Media handles (Instagram, etc.)
  - 👍 Likes & 👥 Follower Counts
  - ⭐ Customer Ratings & Review Breakdown (`rating`, `ratingOverall`, `ratingCount`)
  - 📢 Meta Ad Library status (`ad_status`, `pageAdLibrary`)
  - 🗣 Direct Messenger Link (`messenger`)
  - 📝 Bio / About Snippets (`about_me`, `info`)
- **Native MCP Server**: Directly plug into AI agents and LLM tools (Claude Desktop, Antigravity, Cursor, Windsurf, LangChain).
- **Multi-Format Export**: Save your search datasets directly to **JSON**, **JSONL**, or flattened **CSV** for Excel / Google Sheets.
- **Zero Third-Party Dependencies**: Built on Python 3 standard library; runs immediately out-of-the-box.

---

## 🚀 Installation

### Option 1: Run directly with Python

Requires Python 3.10+:

```bash
git clone <repo-url>
cd facebook-search-scraper
```

### Option 2: Install as a system CLI tool

```bash
pip install .
```

This registers the `facebook-search-scraper` (or shorthand `fb-scraper`) command globally.

---

## 🤖 Model Context Protocol (MCP) Server

You can connect this software to any MCP-enabled assistant (such as Claude Desktop, Antigravity, Cursor, or Windsurf) to give your AI direct Facebook scraping capabilities.

### Starting the MCP Server

```bash
python main.py --mcp
```
*(Or if installed via pip: `facebook-search-scraper --mcp`)*

### Configuration

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "facebook-search-scraper": {
      "command": "python",
      "args": ["<FULL_PATH_TO_DIRECTORY>/main.py", "--mcp"]
    }
  }
}
```

#### Antigravity / Cursor / Windsurf (`mcp.json`)

```json
{
  "mcpServers": {
    "facebook-search-scraper": {
      "command": "python",
      "args": ["main.py", "--mcp"]
    }
  }
}
```

### MCP Tool Exposed

- **`facebook_search_scraper`**
  - **`categories`** (array of strings, required): Search keywords, phrases, or handles (e.g. `["Coffee Shop", "Bakery"]`).
  - **`locations`** (array of strings, optional): Locations to apply (e.g. `["Montreal", "New York"]`).
  - **`searchType`** (string, default `"pages-google"`): Target type: `"pages-google"`, `"pages"`, `"profiles"`, `"posts"`, or `"reels"`.
  - **`resultsLimit`** (integer, default `20`): Maximum results to harvest.

---

## 💻 Command Line Interface (CLI)

### Search by Keyword and Location

```bash
# Export to JSON
python main.py -c "Coffee Shop" -l "Montreal" -n 10 -o montreal_cafes.json

# Export directly to CSV for Excel / Google Sheets
python main.py -c "Portuguese Restaurant" -l "Montreal" -n 10 -o restaurants.csv
```

### Scrape a Specific Business Handle or URL

```bash
python main.py -c "Jordanmcinnisdesigns" -n 1 -o page_details.json
```

### Search Facebook Posts or Reels

```bash
# Posts
python main.py -c "latte art" -t posts -n 5 -o posts.json

# Reels
python main.py -c "coffee brewing" -t reels -n 5 -o reels.json
```

### Run with a Configuration JSON File

```bash
python main.py -i search_config.json -o output.csv
```

Example `search_config.json`:
```json
{
  "categories": ["Specialty Coffee", "Artisan Bakery"],
  "locations": ["Montreal", "Toronto"],
  "searchType": "pages-google",
  "resultsLimit": 25
}
```

---

## 🐍 Python Library API

You can also import and use the scraper in your own Python applications:

```python
from facebook_search_scraper import FacebookSearchScraper, export_to_csv, export_to_json

scraper = FacebookSearchScraper()

# Execute search
results = scraper.run(
    categories=["Coffee Shop"],
    locations=["Montreal"],
    search_type="pages-google",
    results_limit=5
)

for item in results:
    print(f"Title: {item['title']}")
    print(f"Email: {item['email']}")
    print(f"Phone: {item['phone']}")
    print(f"Address: {item['address']}")
    print("-" * 40)

# Export results
export_to_csv(results, "leads.csv")
export_to_json(results, "leads.json")
```

---

## 📦 Output Format

Example record:

```json
[
  {
    "facebookUrl": "https://www.facebook.com/Jordanmcinnisdesigns/",
    "pageUrl": "https://www.facebook.com/Jordanmcinnisdesigns/",
    "title": "Jordan Mcinnis Designs | Montreal QC",
    "pageName": "Jordanmcinnisdesigns",
    "pageId": "100068579062225",
    "facebookId": "100068579062225",
    "categories": [
      "Page",
      "Graphic Designer"
    ],
    "info": [
      "Jordan Mcinnis Designs, Montreal. 84 followers. I'm Jordan Mcinnis, Montreal based Graphic & Web Designer."
    ],
    "likes": 88,
    "followers": 84,
    "messenger": "https://m.me/Jordanmcinnisdesigns",
    "priceRange": "$$",
    "address": "4972 belleville, Montreal, QC, Canada, Quebec https://maps.google.com/maps?q=4972%20belleville%2C%20Montreal%2C%20QC%2C%20Canada%2C%20Quebec&hl=en",
    "addressUrl": "https://www.bing.com/maps?q=4972%20belleville%2C%20Montreal%2C%20QC%2C%20Canada%2C%20Quebec",
    "phone": "+1 514-716-0922",
    "email": "mcinnisj.design@gmail.com",
    "website": "jordanmcinnis.com",
    "websites": [
      "jordanmcinnis.com"
    ],
    "rating": "5.0 (6 Reviews)",
    "ratingOverall": 5.0,
    "ratingCount": 6,
    "creation_date": "October 2, 2017",
    "ad_status": "This Page is not currently running ads.",
    "pageAdLibrary": {
      "is_business_page_active": false,
      "id": "1449158455201923"
    },
    "about_me": {
      "text": "Jordan Mcinnis Designs, Montreal based Graphic & Web Designer.",
      "urls": ["jordanmcinnis.com"]
    },
    "socialMedia": {
      "instagram": [
        {
          "username": "jordanmcinnis",
          "url": "https://www.instagram.com/jordanmcinnis/"
        }
      ]
    }
  }
]
```

---

## 🐳 Docker Support

Build and run in a container:

```bash
# Build
docker build -t facebook-search-scraper .

# Run CLI
docker run --rm facebook-search-scraper -c "Coffee Shop" -l "Montreal" -n 5

# Run MCP server
docker run -i --rm facebook-search-scraper --mcp
```
