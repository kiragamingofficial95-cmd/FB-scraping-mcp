import html
import http.cookiejar
import random
import re
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
]


def get_random_user_agent() -> str:
    """Return a randomized modern desktop user agent string."""
    return random.choice(USER_AGENTS)


def create_http_session(proxy: Optional[str] = None) -> urllib.request.OpenerDirector:
    """Build an HTTP opener with CookieJar session state and optional proxy handler."""
    cookie_jar = http.cookiejar.CookieJar()
    handlers: List[Any] = [urllib.request.HTTPCookieProcessor(cookie_jar)]
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener(*handlers)


def fetch_url(
    opener: urllib.request.OpenerDirector,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
) -> Tuple[Optional[str], int, str]:
    """
    Fetch a URL with exponential backoff and automatic retry.
    Returns (content, status_code, final_url).
    """
    default_headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    if headers:
        default_headers.update(headers)

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=default_headers)
            with opener.open(req, timeout=timeout) as resp:
                status = resp.status
                final_url = resp.geturl()
                content = resp.read().decode("utf-8", errors="ignore")
                return content, status, final_url
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 504) and attempt < max_retries - 1:
                sleep_time = backoff_factor * (2**attempt) + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
                continue
            return None, e.code, url
        except Exception:
            if attempt < max_retries - 1:
                sleep_time = backoff_factor * (2**attempt) + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)
                continue
            return None, 0, url
    return None, 0, url


def clean_facebook_url(raw_url: str) -> str:
    """Normalize and strip query parameters/tracking tokens from Facebook URLs."""
    if not raw_url:
        return ""
    parsed = urllib.parse.urlparse(raw_url)
    clean_path = parsed.path
    if not clean_path.endswith("/"):
        clean_path += "/"
    return f"https://www.facebook.com{clean_path}"


def clean_text(text: Optional[str]) -> Optional[str]:
    """Unescape unicode and HTML entities in strings."""
    if not text:
        return None
    try:
        decoded = text.encode("utf-8").decode("unicode_escape")
    except Exception:
        decoded = text
    decoded = html.unescape(decoded)
    return decoded.strip()


def parse_count_metric(text: Optional[str], metric_name: str) -> Optional[int]:
    """Extract numeric counts like '1.2K likes', '88 followers', '3,450 were here'."""
    if not text:
        return None
    pattern = rf"([\d,.]+\s*[kmbKMB]?)\s*(?:{metric_name})"
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    raw_num = m.group(1).replace(",", "").strip()
    try:
        multiplier = 1
        if raw_num.lower().endswith("k"):
            multiplier = 1000
            raw_num = raw_num[:-1]
        elif raw_num.lower().endswith("m"):
            multiplier = 1000000
            raw_num = raw_num[:-1]
        elif raw_num.lower().endswith("b"):
            multiplier = 1000000000
            raw_num = raw_num[:-1]
        return int(float(raw_num) * multiplier)
    except (ValueError, TypeError):
        return None


def generate_map_url(address: str) -> str:
    """Generate a standard Google Maps link for the given address."""
    encoded = urllib.parse.quote(address)
    return f"https://maps.google.com/maps?q={encoded}&hl=en"


def generate_bing_map_url(address: str) -> str:
    """Generate a standard Bing Maps link for the given address."""
    encoded = urllib.parse.quote(address)
    return f"https://www.bing.com/maps?q={encoded}"
