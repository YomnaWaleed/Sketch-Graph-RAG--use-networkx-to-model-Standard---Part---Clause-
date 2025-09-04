# src/parse_headings.py
import re, uuid
from pathlib import Path
from typing import List, Dict

# flexible regexes (you can extend them)
numbered_header_re = re.compile(
    r"^\s*(\d+(?:\.\d+){0,3})\s*\.?\s+(?P<title>[A-Z][^\n]{3,200})$", re.M
)
code_header_re = re.compile(r"^(?P<code>[A-Z]{2,6}\.\d+)\s+(?P<title>.+)$", re.M)
allcaps_re = re.compile(r"^[A-Z0-9 \-]{3,200}$", re.M)


def parse_numbered_headings(text: str) -> List[Dict]:
    """
    Return list of chunks: {id, level, title, parent_id, parent_num, content}
    Slices content from end(header_i) -> start(header_{i+1})
    """
    matches = list(numbered_header_re.finditer(text))
    if not matches:
        matches = list(code_header_re.finditer(text))
    # fallback: any ALL-CAPS lines as headings (best-effort)
    if not matches:
        matches = list(allcaps_re.finditer(text))

    if not matches:
        return [
            {
                "id": str(uuid.uuid4()),
                "level": 1,
                "title": "Document",
                "parent_id": None,
                "parent_num": None,
                "content": text.strip(),
            }
        ]

    chunks = []
    boundaries = [
        (
            m.start(),
            m.end(),
            m.group(0),
            (m.groupdict().get("title") or m.group(0)).strip(),
        )
        for m in matches
    ]
    boundaries.append((len(text), len(text), "", ""))

    for i in range(len(boundaries) - 1):
        header_line = boundaries[i][2]
        title = boundaries[i][3].strip()
        content = text[boundaries[i][1] : boundaries[i + 1][0]].strip()
        num_match = re.match(r"^\s*(\d+(?:\.\d+)*)", header_line)
        level = num_match.group(1).count(".") + 1 if num_match else 2
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "level": level,
                "title": title,
                "parent_num": num_match.group(1) if num_match else None,
                "parent_id": None,  # fill later
                "content": content,
            }
        )

    # link parents by numeric prefix
    for c in chunks:
        pnum = c.get("parent_num")
        if pnum:
            parts = pnum.split(".")
            found_parent = None
            for candidate in reversed(chunks):
                cp = candidate.get("parent_num")
                if cp and cp == ".".join(parts[:-1]):
                    found_parent = candidate["id"]
                    break
            c["parent_id"] = found_parent
        else:
            c["parent_id"] = None
    return chunks


def save_markdown(chunks, out_md_path):
    out_md_path = Path(out_md_path)
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for c in chunks:
        header_prefix = "#" * max(1, c["level"])
        lines.append(f"{header_prefix} {c['title']}\n")
        lines.append(c["content"] + "\n\n")
    out_md_path.write_text("\n".join(lines), encoding="utf-8")
