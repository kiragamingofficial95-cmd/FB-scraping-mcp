import logging
import random
import re
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Set

from .utils import (
    clean_facebook_url,
    clean_text,
    create_http_session,
    fetch_url,
    generate_bing_map_url,
    generate_map_url,
    get_random_user_agent,
    parse_count_metric,
)

logger = logging.getLogger("facebook_search_scraper")


class FacebookSearchScraper:
    """
    Standalone Facebook Search Scraper engine.
    Extracts Facebook pages, profiles, posts, and reels with deep contact info,
    follower metrics, ratings, ad status, and metadata without requiring login or API keys.
    """

    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.session = create_http_session(proxy)

    def search_candidate_urls(
        self,
        query: str,
        location: Optional[str] = None,
        search_type: str = "pages-google",
        limit: int = 20,
    ) -> List[str]:
        """
        Discover candidate Facebook URLs using search engine discovery and public directory indexing.
        """
        combined_query = query.strip()
        if location and location.strip():
            combined_query += f" {location.strip()}"

        candidates: List[str] = []
        seen_urls: Set[str] = set()

        # Direct URL or single alphanumeric handle
        if query.startswith("http://") or query.startswith("https://"):
            if "facebook.com" in query:
                cleaned = clean_facebook_url(query)
                candidates.append(cleaned)
                seen_urls.add(cleaned)
        elif re.match(r"^[a-zA-Z0-9\._\-]{3,50}$", query) and not location:
            direct_candidate = f"https://www.facebook.com/{query}/"
            candidates.append(direct_candidate)
            seen_urls.add(direct_candidate)

        # Search queries
        search_queries = []
        if search_type in ("pages-google", "pages"):
            search_queries.append(f"site:facebook.com {combined_query}")
            search_queries.append(f'site:facebook.com "{combined_query}"')
        elif search_type == "profiles":
            search_queries.append(f"site:facebook.com/people {combined_query}")
            search_queries.append(f"site:facebook.com {combined_query} profile")
        elif search_type == "posts":
            search_queries.append(f"site:facebook.com {combined_query} posts")
            search_queries.append(f'site:facebook.com inurl:posts "{combined_query}"')
        elif search_type == "reels":
            search_queries.append(f"site:facebook.com {combined_query} reel")
            search_queries.append(f'site:facebook.com inurl:reel "{combined_query}"')

        for q in search_queries:
            if len(candidates) >= limit:
                break
            found = self._query_search_engine(q)
            for u in found:
                filtered = self._filter_and_clean_url(u, search_type)
                if filtered and filtered not in seen_urls:
                    seen_urls.add(filtered)
                    candidates.append(filtered)
                    if len(candidates) >= limit:
                        break
            time.sleep(random.uniform(0.6, 1.2))

        # Fallback to Facebook Public Directory if needed
        if len(candidates) < limit and search_type in ("pages-google", "pages", "profiles"):
            fb_dir_slug = re.sub(r"[^a-zA-Z0-9]+", "-", combined_query).strip("-")
            dir_url = f"https://www.facebook.com/public/{fb_dir_slug}"
            content, status, _ = fetch_url(self.session, dir_url)
            if content and status == 200:
                raw_links = re.findall(r'href="(https://[a-z0-9\.]*facebook\.com/[^"?#/]+)', content)
                for l in raw_links:
                    filtered = self._filter_and_clean_url(l, search_type)
                    if filtered and filtered not in seen_urls:
                        seen_urls.add(filtered)
                        candidates.append(filtered)
                        if len(candidates) >= limit:
                            break

        return candidates[:limit]

    def _query_search_engine(self, query: str) -> List[str]:
        """Query public search endpoints with rotating User-Agent and headers."""
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        content, status, _ = fetch_url(self.session, url, headers=headers)
        urls: List[str] = []
        if content and status == 200:
            matches = re.findall(r'href="[^"]*uddg=([^"&]+)', content)
            for m in matches:
                decoded = urllib.parse.unquote(m)
                if "facebook.com" in decoded and decoded not in urls:
                    urls.append(decoded)
        return urls

    def _filter_and_clean_url(self, raw_url: str, search_type: str) -> Optional[str]:
        """Filter out Facebook system endpoints and validate target type."""
        exclude_paths = [
            "/login",
            "/recover",
            "/help",
            "/reg",
            "/policies",
            "/privacy",
            "/legal",
            "/l.php",
            "/sharer",
            "/share",
            "/dialog",
            "/tr",
            "/ads",
            "/public",
            "/watch",
            "/marketplace",
            "/gaming",
            "/checkpoint",
            "/settings",
            "/messages",
            "/me",
            "/home.php",
            "/index.php",
        ]
        lowered = raw_url.lower()
        if any(p in lowered for p in exclude_paths):
            return None

        clean = clean_facebook_url(raw_url)
        path = urllib.parse.urlparse(clean).path.strip("/")
        if not path:
            return None

        parts = path.split("/")
        first_segment = parts[0]

        if search_type in ("pages-google", "pages"):
            if first_segment in ("photo", "photos", "photo.php", "watch", "live", "media", "story.php"):
                return None
            return clean
        elif search_type == "profiles":
            if "people" in path or "profile.php" in path or len(parts) == 1:
                return clean
        elif search_type == "posts":
            if "posts" in path or "story" in path or "permalink" in path:
                return clean
        elif search_type == "reels":
            if "reel" in path or "videos" in path:
                return clean
        return clean

    def scrape_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a public Facebook page and extract complete record-level details."""
        clean_url = clean_facebook_url(url)
        content, status, _ = fetch_url(self.session, clean_url)
        
        parsed_path = urllib.parse.urlparse(clean_url).path.strip("/").split("/")
        page_name = parsed_path[0] if parsed_path and parsed_path[0] != "profile.php" else None

        has_login = False
        if content:
            has_login = "URL=/login/" in content or "login_form" in content

        # If primary fetch hit a login wall or returned no content, use embed plugin fallback
        if not content or status != 200 or has_login:
            embed_url = f"https://www.facebook.com/plugins/page.php?href={urllib.parse.quote(clean_url)}&tabs=timeline"
            embed_content, embed_status, _ = fetch_url(self.session, embed_url)
            if embed_content and embed_status == 200:
                return self._parse_embed_page(clean_url, page_name, embed_content)
            elif not content or status != 200:
                logger.warning(f"Failed to fetch {clean_url} (HTTP {status})")
                return None

        # Context items from embedded SSR scripts
        intro_items: Dict[str, str] = {}
        context_matches = set(re.findall(r'"timeline_context_list_item_type":\s*"([^"]+)"', content))
        for item_type in context_matches:
            pattern = rf'"timeline_context_list_item_type":\s*"{item_type}"'
            for m in re.finditer(pattern, content):
                start = max(0, m.start() - 600)
                end = min(len(content), m.end() + 300)
                snippet = content[start:end]
                texts = re.findall(r'"text":\s*"([^"]+)"', snippet)
                if texts:
                    val = clean_text(texts[-1])
                    if val:
                        intro_items[item_type] = val

        # Categories
        categories: List[str] = ["Page"]
        raw_cat = intro_items.get("INTRO_CARD_INFLUENCER_CATEGORY")
        if raw_cat:
            parts = [clean_text(p) for p in re.split(r"[·•|]", raw_cat) if p.strip()]
            for p in parts:
                if p and p not in categories:
                    categories.append(p)
        else:
            cat_matches = re.findall(r'"category_name":\s*"([^"]+)"', content)
            for c in cat_matches:
                clean_c = clean_text(c)
                if clean_c and clean_c not in categories:
                    categories.append(clean_c)

        # Contact Details
        email = intro_items.get("INTRO_CARD_PROFILE_EMAIL")
        if not email:
            email_m = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', content)
            if email_m and not email_m.group(1).endswith(("facebook.com", "fb.com")):
                email = email_m.group(1)

        phone = intro_items.get("INTRO_CARD_PROFILE_PHONE")
        if not phone:
            phone_m = re.search(r'"phone_number":\s*"([^"]+)"', content)
            if phone_m:
                phone = clean_text(phone_m.group(1))

        website = intro_items.get("INTRO_CARD_WEBSITE")
        websites: List[str] = []
        if website:
            websites.append(website)
        for w_match in re.findall(r'"external_url":\s*"([^"]+)"', content):
            cw = clean_text(w_match)
            if cw and cw not in websites and "facebook.com" not in cw:
                websites.append(cw)

        # Address & Maps
        address_text = intro_items.get("INTRO_CARD_ADDRESS")
        address = None
        address_url = None
        if address_text:
            address = f"{address_text} {generate_map_url(address_text)}"
            address_url = generate_bing_map_url(address_text)

        # Pricing
        price_range = None
        raw_price = intro_items.get("INTRO_CARD_BUSINESS_PRICE")
        if raw_price:
            m_price = re.search(r"([$£€¥]+)", raw_price)
            price_range = m_price.group(1) if m_price else raw_price

        # Ratings
        raw_rating = intro_items.get("INTRO_CARD_RATING")
        rating_overall = None
        rating_count = None
        if raw_rating:
            r_num = re.search(r"([\d.]+)\s*(?:stars?|\/|out of|\()", raw_rating, re.IGNORECASE)
            if r_num:
                try:
                    rating_overall = float(r_num.group(1))
                except ValueError:
                    pass
            c_num = re.search(r"\((\d+[\d,]*)\s*(?:reviews?|ratings?)", raw_rating, re.IGNORECASE)
            if c_num:
                try:
                    rating_count = int(c_num.group(1).replace(",", ""))
                except ValueError:
                    pass

        # Page & Ad Library identifiers
        page_id = al_android.group(1) if al_android else None
        if not page_id:
            pid_m = re.search(r'"pageID":"(\d+)"', content) or re.search(r'"userID":"(\d{8,})"', content)
            if pid_m:
                page_id = pid_m.group(1)

        delegate_page_id = None
        is_business_page_active = False
        del_m = re.search(r'"delegate_page":\{[^}]*"id":"(\d+)"', content)
        if del_m:
            delegate_page_id = del_m.group(1)
        active_m = re.search(r'"is_business_page_active":\s*(true|false)', content)
        if active_m:
            is_business_page_active = active_m.group(1) == "true"

        ad_status = (
            "This Page is currently running ads."
            if is_business_page_active
            else "This Page is not currently running ads."
        )

        page_ad_library = {
            "is_business_page_active": is_business_page_active,
            "id": delegate_page_id or page_id,
        }

        # Follower & Like Metrics
        description_text = clean_text(og_desc.group(1)) if og_desc else clean_text(meta_desc.group(1)) if meta_desc else ""
        likes = parse_count_metric(description_text, "likes")
        followers = parse_count_metric(description_text, "followers")
        if followers is None:
            followers_m = re.findall(r"(\d+[\d,.]*\s*(?:followers|following))", content, re.IGNORECASE)
            if followers_m:
                followers = parse_count_metric(followers_m[0], "followers")

        info = [description_text] if description_text else []
        messenger = f"https://m.me/{page_name}" if page_name else None

        # Social Accounts
        other_acc = intro_items.get("INTRO_CARD_OTHER_ACCOUNT")
        social_media: Dict[str, Any] = {}
        if other_acc:
            social_media["instagram"] = [{"username": other_acc, "url": f"https://www.instagram.com/{other_acc}/"}]

        # Creation date
        creation_date = None
        cd_m = re.search(r'"creation_date":\s*"([^"]+)"', content) or re.search(
            r"(?:Page created|Founded)[^\w\d]*([A-Za-z]+\s+\d{1,2},\s+\d{4})", content
        )
        if cd_m:
            creation_date = cd_m.group(1)

        about_text = intro_items.get("INTRO_CARD_BIO") or description_text
        about_me = {"text": about_text, "urls": websites}

        return {
            "facebookUrl": clean_url,
            "pageUrl": clean_url,
            "title": title or page_name or "Facebook Page",
            "pageName": page_name or (title or "").replace(" ", ""),
            "pageId": page_id,
            "facebookId": page_id,
            "categories": categories,
            "info": info,
            "likes": likes,
            "followers": followers,
            "messenger": messenger,
            "priceRange": price_range,
            "address": address,
            "addressUrl": address_url,
            "phone": phone,
            "email": email,
            "website": website or (websites[0] if websites else None),
            "websites": websites,
            "rating": raw_rating,
            "ratingOverall": rating_overall,
            "ratingCount": rating_count,
            "creation_date": creation_date,
            "ad_status": ad_status,
            "pageAdLibrary": page_ad_library,
            "about_me": about_me,
            "socialMedia": social_media,
        }

    def _parse_embed_page(self, clean_url: str, page_name: Optional[str], embed_content: str) -> Dict[str, Any]:
        """Extract page info from Facebook's public embed page plugin when desktop web serves a login redirect."""
        # Find page ID from embed link (e.g. https://www.facebook.com/1449158455201923?ref=embed_page)
        pids = re.findall(r'facebook\.com/(\d{10,})', embed_content)
        page_id = pids[0] if pids else None

        # Title from link text
        title_matches = re.findall(r'<a[^>]+href="https://www\.facebook\.com/\d+[^"]*"[^>]*>([^<]+)</a>', embed_content)
        title = clean_text(title_matches[0]) if title_matches else (page_name or "Facebook Page")

        # Followers
        followers = None
        followers_m = re.findall(r'(\d+[\d,.]*\s*(?:followers|likes))', embed_content, re.IGNORECASE)
        if followers_m:
            followers = parse_count_metric(followers_m[0], "followers") or parse_count_metric(followers_m[0], "likes")

        info_texts = re.findall(r'<div[^>]*class="[^"]*userContent[^"]*"[^>]*>(.*?)</div>', embed_content, re.DOTALL)
        info = [clean_text(t) for t in info_texts if t.strip()]

        messenger = f"https://m.me/{page_name}" if page_name else None

        return {
            "facebookUrl": clean_url,
            "pageUrl": clean_url,
            "title": title,
            "pageName": page_name or (title or "").replace(" ", ""),
            "pageId": page_id,
            "facebookId": page_id,
            "categories": ["Page"],
            "info": info,
            "likes": None,
            "followers": followers,
            "messenger": messenger,
            "priceRange": None,
            "address": None,
            "addressUrl": None,
            "phone": None,
            "email": None,
            "website": None,
            "websites": [],
            "rating": None,
            "ratingOverall": None,
            "ratingCount": None,
            "creation_date": None,
            "ad_status": "This Page is not currently running ads.",
            "pageAdLibrary": {
                "is_business_page_active": False,
                "id": page_id,
            },
            "about_me": {
                "text": " | ".join(info) if info else "",
                "urls": [],
            },
            "socialMedia": {},
        }

    def scrape_post(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a Facebook post."""
        clean_url = clean_facebook_url(url)
        content, status, _ = fetch_url(self.session, clean_url)
        if not content or status != 200:
            return None

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', content)
        og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', content)
        og_image = re.search(r'<meta property="og:image" content="([^"]+)"', content)

        author_name = clean_text(og_title.group(1)) if og_title else "Facebook User"
        text = clean_text(og_desc.group(1)) if og_desc else ""
        image_url = clean_text(og_image.group(1)) if og_image else None

        pid_m = re.search(r"posts/(\d+)", clean_url) or re.search(r"fbid=(\d+)", clean_url)
        post_id = pid_m.group(1) if pid_m else None

        likes = parse_count_metric(content, "likes")
        comments = parse_count_metric(content, "comments")
        shares = parse_count_metric(content, "shares")

        return {
            "postId": post_id,
            "postUrl": clean_url,
            "facebookUrl": clean_url,
            "title": author_name,
            "author": {"name": author_name},
            "text": text,
            "likes": likes,
            "commentsCount": comments,
            "sharesCount": shares,
            "media": [image_url] if image_url else [],
        }

    def scrape_reel(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a Facebook reel."""
        clean_url = clean_facebook_url(url)
        content, status, _ = fetch_url(self.session, clean_url)
        if not content or status != 200:
            return None

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', content)
        og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', content)
        og_video = re.search(r'<meta property="og:video" content="([^"]+)"', content)

        author_name = clean_text(og_title.group(1)) if og_title else "Facebook User"
        caption = clean_text(og_desc.group(1)) if og_desc else ""
        video_url = clean_text(og_video.group(1)) if og_video else None

        rid_m = re.search(r"reel/(\d+)", clean_url) or re.search(r"videos/(\d+)", clean_url)
        reel_id = rid_m.group(1) if rid_m else None

        views = parse_count_metric(content, "views")
        likes = parse_count_metric(content, "likes")

        return {
            "reelId": reel_id,
            "reelUrl": clean_url,
            "facebookUrl": clean_url,
            "title": author_name,
            "author": {"name": author_name},
            "caption": caption,
            "viewsCount": views,
            "likesCount": likes,
            "videoUrl": video_url,
        }

    def scrape_profile(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a Facebook profile."""
        clean_url = clean_facebook_url(url)
        content, status, _ = fetch_url(self.session, clean_url)
        if not content or status != 200:
            return None

        og_title = re.search(r'<meta property="og:title" content="([^"]+)"', content)
        og_desc = re.search(r'<meta property="og:description" content="([^"]+)"', content)
        name = clean_text(og_title.group(1)) if og_title else "Facebook Profile"
        bio = clean_text(og_desc.group(1)) if og_desc else ""

        al_android = re.search(r'<meta property="al:android:url" content="fb://profile/(\d+)"', content)
        profile_id = al_android.group(1) if al_android else None
        followers = parse_count_metric(bio, "followers")

        return {
            "profileId": profile_id,
            "facebookId": profile_id,
            "name": name,
            "title": name,
            "profileUrl": clean_url,
            "facebookUrl": clean_url,
            "bio": bio,
            "followers": followers,
        }

    def run(
        self,
        categories: List[str],
        locations: Optional[List[str]] = None,
        search_type: str = "pages-google",
        results_limit: int = 20,
        item_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute full search and extraction workflow.
        """
        if not categories:
            logger.warning("No search categories provided.")
            return []

        locations = locations or [""]
        total_items: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        for category in categories:
            for location in locations:
                if len(total_items) >= results_limit:
                    break

                loc_str = location or "None"
                logger.info(f"Searching for '{category}' (location: '{loc_str}', type: '{search_type}')")

                candidate_urls = self.search_candidate_urls(
                    query=category,
                    location=location,
                    search_type=search_type,
                    limit=results_limit - len(total_items),
                )
                logger.info(f"Discovered {len(candidate_urls)} candidate URLs")

                for u in candidate_urls:
                    if len(total_items) >= results_limit:
                        break
                    if u in seen_urls:
                        continue
                    seen_urls.add(u)

                    logger.info(f"Scraping: {u}")
                    item = None
                    if search_type in ("pages-google", "pages"):
                        item = self.scrape_page(u)
                    elif search_type == "posts":
                        item = self.scrape_post(u)
                    elif search_type == "reels":
                        item = self.scrape_reel(u)
                    elif search_type == "profiles":
                        item = self.scrape_profile(u)

                    if item:
                        total_items.append(item)
                        if item_callback:
                            item_callback(item)

                    time.sleep(random.uniform(0.5, 1.2))

        logger.info(f"Completed run. Extracted {len(total_items)} items.")
        return total_items
