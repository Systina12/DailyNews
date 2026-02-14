import re


def normalize_title(title: str) -> str:
    if not title:
        return ""

    title = title.lower().strip()

    title = re.sub(r"【.*?】", "", title)
    title = re.sub(r"\[.*?]", "", title)

    title = re.sub(
        r"^\s*(突发|更新|快讯|breaking|update)\s*[:：-]?\s*",
        "",
        title,
        flags=re.I,
    )

    title = re.sub(r"[-–—|]", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title


def dedupe_items(data: dict):
    all_items = data.get("items", [])

    seen = set()
    deduped = []

    for item in all_items:
        norm = normalize_title(item.get("title"))

        if norm not in seen:
            seen.add(norm)
            deduped.append(item)

    data["items"] = deduped

    return data