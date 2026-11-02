import csv
import json
from typing import Any, Dict, List


def export_to_json(items: List[Dict[str, Any]], filepath: str, indent: int = 2) -> None:
    """Export items to a formatted JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=indent, ensure_ascii=False)


def export_to_jsonl(items: List[Dict[str, Any]], filepath: str) -> None:
    """Export items to a JSON Lines (JSONL) file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def export_to_csv(items: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export items to a CSV file.
    Flattens nested objects (like about_me, pageAdLibrary, categories) for clean spreadsheet viewing.
    """
    if not items:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            pass
        return

    # Determine all fieldnames
    fieldnames = [
        "title",
        "pageName",
        "pageId",
        "categories",
        "email",
        "phone",
        "website",
        "address",
        "addressUrl",
        "likes",
        "followers",
        "rating",
        "ratingOverall",
        "ratingCount",
        "priceRange",
        "messenger",
        "ad_status",
        "creation_date",
        "facebookUrl",
        "pageUrl",
        "info",
        "adLibraryId",
        "adLibraryActive",
        "aboutText",
        "instagram",
    ]

    # Include any extra keys from items
    for item in items:
        for k in item.keys():
            if k not in fieldnames and k not in ("pageAdLibrary", "about_me", "socialMedia", "websites"):
                fieldnames.append(k)

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            row: Dict[str, Any] = {}
            for k in fieldnames:
                row[k] = item.get(k, "")

            # Flatten specific structured fields
            if isinstance(item.get("categories"), list):
                row["categories"] = ", ".join(str(c) for c in item["categories"])

            if isinstance(item.get("info"), list):
                row["info"] = " | ".join(str(i) for i in item["info"])

            ad_lib = item.get("pageAdLibrary")
            if isinstance(ad_lib, dict):
                row["adLibraryId"] = ad_lib.get("id", "")
                row["adLibraryActive"] = ad_lib.get("is_business_page_active", "")

            about = item.get("about_me")
            if isinstance(about, dict):
                row["aboutText"] = about.get("text", "")

            sm = item.get("socialMedia")
            if isinstance(sm, dict) and "instagram" in sm:
                ig_list = sm["instagram"]
                if isinstance(ig_list, list) and ig_list:
                    row["instagram"] = ig_list[0].get("url", "")

            writer.writerow(row)
