#!/usr/bin/env python3
"""
bundle.py – формирует текстовые дампы проекта, пригодные для ChatGPT.

• Part 1 содержит индекс «PROJECT OVERVIEW».
• Каждый файл начинается строкой «# FILE: <path>» и открывается тройным
  бэктиком с языком: ```python, ```json, … .
• Дамп делится на части, каждая ≈ TOKEN_LIMIT токенов (≈ CHAR_LIMIT симв.).
• Если ОДИН файл превышает лимит, он режется на Chunk N/M – без обрезки кода.
"""

from __future__ import annotations
import os
import fnmatch
import argparse
from pathlib import Path
from tqdm import tqdm

# ──────────────────────────── базовые настройки ────────────────────────────
TOKEN_LIMIT      = 3_500
CHARS_PER_TOKEN  = 4
CHAR_LIMIT       = TOKEN_LIMIT * CHARS_PER_TOKEN     # ≈ 14 000 симв.

LANG_MAP = {  # расширение → язык для markdown‑подсветки
    ".py": "python", ".json": "json", ".js": "javascript", ".ts": "typescript",
    ".html": "html", ".css": "css", ".md": "markdown", ".ini": "ini",
    ".toml": "toml", ".yml": "yaml", ".yaml": "yaml", ".sql": "sql",
    ".txt": "text",
}

# ──────────────────────────── ignore helpers ────────────────────────────────
def load_ignore(base: Path) -> set[str]:
    ignore = {".bundleignore"}
    f = base / ".bundleignore"
    if f.exists():
        for ln in f.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                ignore.add(ln)
    return ignore

def hidden(p: Path) -> bool:
    return any(seg.startswith(".") for seg in p.parts)

def skip(p: Path, ignore: set[str]) -> bool:
    if hidden(p):
        return True
    s = str(p)
    return any(fnmatch.fnmatch(s, pat) or fnmatch.fnmatch(p.name, pat) for pat in ignore)

# ──────────────────────────── сбор файлов ───────────────────────────────────
def collect(src: Path, ignore: set[str]):
    files = []
    for root, dirs, fls in os.walk(src):
        dirs[:] = [d for d in dirs if not skip(Path(root, d), ignore)]
        for f in fls:
            p = Path(root, f)
            if not skip(p, ignore):
                files.append(p)
    return sorted(files)

# ──────────────────────────── служебные функции ────────────────────────────
def lang(p: Path) -> str:
    return LANG_MAP.get(p.suffix.lower(), "")

def unique(out_dir: Path, idx: int) -> Path:
    return out_dir / f"build_{idx}.txt"

def write_index(fh, files, src):
    fh.write("## PROJECT OVERVIEW\n")
    for p in files:
        fh.write(f"{p.relative_to(src).as_posix()}\n")
    fh.write("\n")

def split_code(raw: str, header_len: int, footer_len: int, limit: int):
    """Разбивает код на куски так, чтобы <chunk> + header + footer ≤ limit."""
    chunk_size = limit - header_len - footer_len
    for i in range(0, len(raw), chunk_size):
        yield raw[i : i + chunk_size]

def write_chunk(fh, rel: str, code: str, language: str,
                idx: int | None = None, total: int | None = None):
    hdr = f"# FILE: {rel}"
    if idx is not None:
        hdr += f" (chunk {idx}/{total})"
    fh.write(hdr + "\n")
    fh.write(f"```{language}\n{code}\n```\n\n")

# ──────────────────────────── основная логика ───────────────────────────────
def bundle(src_dir: Path, char_limit: int = CHAR_LIMIT):
    src_dir = src_dir.resolve()
    ignore  = load_ignore(src_dir)
    files   = collect(src_dir, ignore)

    if not files:
        print("❌ No files to bundle."); return

    out_dir = Path(__file__).resolve().parent
    part_idx = 1
    fh = unique(out_dir, part_idx).open("w", encoding="utf-8")
    write_index(fh, files, src_dir)
    cur_size = fh.tell()

    with tqdm(total=len(files), desc="📦 Bundling", unit="file") as bar:
        for p in files:
            rel = p.relative_to(src_dir).as_posix()
            code = p.read_text(encoding="utf-8", errors="ignore")
            language = lang(p)
            footer_len = len("```\n\n")

            # длинный файл: делим на чанки
            head_template = f"# FILE: {rel} (chunk X/Y)\n```{language}\n"
            head_len = len(head_template.replace("X", "1").replace("Y", "1"))

            if len(code) + len(f"# FILE: {rel}\n```{language}\n") + footer_len > char_limit:
                chunks = list(split_code(code, head_len, footer_len, char_limit))
                total  = len(chunks)
                for idx, chunk in enumerate(chunks, 1):
                    header_len = len(
                        f"# FILE: {rel} (chunk {idx}/{total})\n```{language}\n"
                    )
                    if cur_size + len(chunk) + header_len + footer_len > char_limit and cur_size:
                        fh.close()
                        part_idx += 1
                        fh = unique(out_dir, part_idx).open("w", encoding="utf-8")
                        cur_size = 0
                    write_chunk(fh, rel, chunk, language, idx, total)
                    cur_size = fh.tell()
            else:
                header_len = len(f"# FILE: {rel}\n```{language}\n")
                if cur_size + len(code) + header_len + footer_len > char_limit and cur_size:
                    fh.close()
                    part_idx += 1
                    fh = unique(out_dir, part_idx).open("w", encoding="utf-8")
                    cur_size = 0
                write_chunk(fh, rel, code, language)
                cur_size = fh.tell()

            bar.update(1)

    fh.close()
    print(f"✅ Bundled into {part_idx} file(s) in {out_dir}")

# ──────────────────────────── CLI ───────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Bundle project for ChatGPT.")
    ap.add_argument("source_dir", help="Project directory")
    ap.add_argument("--token-limit", type=int, default=TOKEN_LIMIT,
                    help="Max tokens per part (default 3500).")
    args = ap.parse_args()

    global CHAR_LIMIT
    CHAR_LIMIT = args.token_limit * CHARS_PER_TOKEN
    bundle(Path(args.source_dir), CHAR_LIMIT)

if __name__ == "__main__":
    main()
