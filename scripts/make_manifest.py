#!/usr/bin/env python3
"""
Собирает templates/manifest.json по содержимому папки templates.

Запуск из корня репозитория:
    python3 scripts/make_manifest.py

Для каждого .docx записывает имя файла, название (имя без расширения,
подчёркивания заменены пробелами) и список найденных тегов [[...]].
Уже существующие в manifest.json поля title и description сохраняются.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
MANIFEST = TEMPLATES / "manifest.json"
TAG_RE = re.compile(r"\[\[\s*([^\[\]]+?)\s*\]\]")
PART_RE = re.compile(r"^word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")


def tags_of(docx: Path) -> list[str]:
    found: list[str] = []
    with zipfile.ZipFile(docx) as z:
        for name in z.namelist():
            if not PART_RE.match(name):
                continue
            xml = z.read(name).decode("utf-8", "ignore")
            for para in xml.split("</w:p>"):
                text = "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", para))
                for m in TAG_RE.finditer(text):
                    tag = m.group(1).strip().split("|")[0].strip()
                    if tag and not tag.startswith(("#", "/", "^")) and tag not in found:
                        found.append(tag)
    return found


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"Папка не найдена: {TEMPLATES}", file=sys.stderr)
        return 1
    old: dict[str, dict] = {}
    if MANIFEST.exists():
        try:
            data = json.loads(MANIFEST.read_text("utf-8"))
            for item in data.get("templates", []):
                old[item.get("file", "")] = item
        except Exception as exc:  # noqa: BLE001
            print(f"Старый manifest.json не прочитан ({exc}), создаю заново", file=sys.stderr)

    items = []
    for docx in sorted(TEMPLATES.glob("*.docx")):
        if docx.name.startswith("~$"):
            continue
        prev = old.get(docx.name, {})
        items.append({
            "file": docx.name,
            "title": prev.get("title") or docx.stem.replace("_", " "),
            "description": prev.get("description", ""),
            "tags": tags_of(docx),
        })

    MANIFEST.write_text(json.dumps({"templates": items}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Записано {len(items)} шаблонов → {MANIFEST.relative_to(ROOT)}")
    for it in items:
        print(f"  {it['file']}: {', '.join(it['tags']) or 'тегов нет'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
