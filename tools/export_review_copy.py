#!/usr/bin/env python3
"""Export Pharos user-facing copy with enough context for editorial review."""

from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "review" / "pharos-text-review.json"


class HtmlCopyParser(HTMLParser):
    copy_attributes = {"aria-label", "placeholder", "title"}

    def __init__(self, source: Path):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.stack: list[dict[str, str]] = []
        self.entries: list[dict[str, object]] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.stack.append({"tag": tag, "id": values.get("id", ""), "class": values.get("class", "")})
        for name in self.copy_attributes:
            if values.get(name):
                self.add(values[name], f"attribute:{name}")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        text = " ".join(data.split())
        if text:
            self.add(text, "element-text")

    def add(self, text: str, kind: str):
        node = self.stack[-1] if self.stack else {"tag": "document", "id": "", "class": ""}
        ancestors = [part for part in self.stack if part["id"]][-3:]
        self.entries.append(
            {
                "text": text,
                "source_kind": "static-html",
                "ui_context": {
                    "element": node["tag"],
                    "id": node["id"] or None,
                    "class": node["class"] or None,
                    "ancestor_ids": [part["id"] for part in ancestors],
                    "copy_location": kind,
                },
                "source": str(self.source.relative_to(ROOT)),
                "line": self.getpos()[0],
            }
        )


def enclosing_js_function(lines: list[str], line_number: int) -> str | None:
    for line in reversed(lines[:line_number]):
        match = re.search(r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", line)
        if match:
            return match.group(1)
    return None


def js_entries(source: Path) -> list[dict[str, object]]:
    raw = source.read_text(encoding="utf-8")
    lines = raw.splitlines()
    pattern = re.compile(r"(?P<quote>['\"`])(?P<body>(?:\\.|(?!\1)[\s\S])*?)(?P=quote)")
    entries = []
    for match in pattern.finditer(raw):
        text = match.group("body").replace("\\'", "'").replace('\\"', '"').strip()
        if not text or (len(text) < 3 and not text.isalpha()):
            continue
        line = raw.count("\n", 0, match.start()) + 1
        function = enclosing_js_function(lines, line)
        entries.append(
            {
                "text": text,
                "source_kind": "dynamic-javascript",
                "ui_context": {
                    "function": function,
                    "template": match.group("quote") == "`",
                    "contains_placeholders": "${" in text,
                },
                "source": str(source.relative_to(ROOT)),
                "line": line,
            }
        )
    return entries


def python_entries(source: Path) -> list[dict[str, object]]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    entries = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = " ".join(node.value.split())
        if len(text) < 4:
            continue
        cursor: ast.AST | None = node
        function = None
        while cursor in parents:
            cursor = parents[cursor]
            if isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function = cursor.name
                break
        entries.append(
            {
                "text": text,
                "source_kind": "server-generated-python",
                "ui_context": {"function": function},
                "source": str(source.relative_to(ROOT)),
                "line": node.lineno,
            }
        )
    return entries


def markdown_entries(source: Path) -> list[dict[str, object]]:
    entries, heading, paragraph = [], "Document", []
    for line_number, raw in enumerate(source.read_text(encoding="utf-8").splitlines() + [""], 1):
        line = raw.strip()
        if line.startswith("#"):
            if paragraph:
                entries.append(markdown_entry(source, heading, paragraph, line_number - len(paragraph)))
                paragraph = []
            heading = line.lstrip("#").strip()
        elif not line:
            if paragraph:
                entries.append(markdown_entry(source, heading, paragraph, line_number - len(paragraph)))
                paragraph = []
        else:
            paragraph.append(line)
    return entries


def markdown_entry(source: Path, heading: str, lines: list[str], line: int) -> dict[str, object]:
    return {
        "text": " ".join(lines),
        "source_kind": "methodology-documentation",
        "ui_context": {"section": heading},
        "source": str(source.relative_to(ROOT)),
        "line": line,
    }


def main() -> None:
    html = ROOT / "src/pharos/web/index.html"
    parser = HtmlCopyParser(html)
    parser.feed(html.read_text(encoding="utf-8"))
    entries = parser.entries
    entries.extend(js_entries(ROOT / "src/pharos/web/app.js"))
    for name in ("overview.py", "server.py", "report_exports.py"):
        entries.extend(python_entries(ROOT / "src/pharos" / name))
    entries.extend(markdown_entries(ROOT / "docs/methodology.md"))
    entries.sort(key=lambda item: (item["source"], item["line"], item["text"]))
    for index, entry in enumerate(entries, 1):
        entry["id"] = f"copy-{index:04d}"
    payload = {
        "artifact": "Pharos copy review inventory",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": [
            "Static interface text and accessibility labels",
            "Dynamically composed browser copy, with template placeholders preserved",
            "Server-generated report language",
            "Methodology text linked to the report",
        ],
        "review_guidance": [
            "Values inside ${...} are runtime placeholders, not hard-coded institutional claims.",
            "Technical strings are retained when extraction cannot safely distinguish them from visible copy; source_kind and function identify their context.",
            "Review OpenAlex terminology, factual claims, tone, consistency, accessibility labels, and whether each caveat appears near the claim it qualifies.",
        ],
        "entry_count": len(entries),
        "entries": entries,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {OUTPUT}")


if __name__ == "__main__":
    main()
