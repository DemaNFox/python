#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bundle.py – собирает проект в текстовые дампы для ChatGPT/LLM.

Особенности:
• Чтение .gitignore (Git wildmatch через pathspec) для фильтрации.
• Пропуск бинарных файлов и явно бинарных расширений.
• Разбиение больших файлов по строкам, без порчи UTF-8 (header+chunk+footer ≤ лимит).
• Один параметр --limit: 3500t (токены, *4 символа) или 14000c (символы).
• Вывод в ./bundles/<project>_<YYYYMMDD-HHMMSS>/build_{part}.txt.

Пример:
  python3 bundle.py /path/to/project --limit 3500t
"""

from __future__ import annotations
import argparse
import os
import sys
import datetime as dt
from pathlib import Path
from typing import Iterable, List, Tuple

# ───────────────────────────── зависимость: pathspec ─────────────────────────
print("[debug] python:", sys.executable)
print("[debug] sys.path[0]:", (sys.path[0] if sys.path else None))
try:
    from pathspec import PathSpec
    from pathspec.patterns.gitwildmatch import GitWildMatchPattern
except Exception:
    sys.stderr.write("❌ Требуется библиотека 'pathspec' (pip install pathspec)\n")
    raise

# ────────────────────────────── настройки/константы ──────────────────────────
DEFAULT_CHARS_PER_TOKEN = 4  # множитель для 't'
BINARY_EXTS = {
    ".png",".jpg",".jpeg",".gif",".bmp",".webp",".ico",
    ".pdf",".zip",".gz",".bz2",".xz",".7z",".rar",
    ".mp3",".wav",".flac",".ogg",".mp4",".mkv",".avi",".mov",
    ".woff",".woff2",".ttf",".otf",
    ".exe",".dll",".so",".dylib",".class",
}
MARKDOWN_LANG = {
    ".py": "python",".json":"json",".js":"javascript",".ts":"typescript",
    ".html":"html",".css":"css",".md":"markdown",".ini":"ini",".toml":"toml",
    ".yml":"yaml",".yaml":"yaml",".sql":"sql",".txt":"text",
}
FOOTER = "```\n\n"

# ──────────────────────────────── утилиты ────────────────────────────────────
def parse_limit(arg: str) -> int:
    """Парсит --limit: '3500t' → символы по множителю, '14000c' → символы."""
    arg = arg.strip().lower()
    if not arg or arg[-1] not in ("t","c"):
        raise argparse.ArgumentTypeError("Ожидается вид 3500t или 14000c")
    try:
        n = int(arg[:-1])
    except ValueError:
        raise argparse.ArgumentTypeError("Число до суффикса t/c должно быть целым")
    return n * DEFAULT_CHARS_PER_TOKEN if arg.endswith("t") else n

def load_gitignore_spec(root: Path) -> PathSpec:
    gi = root / ".gitignore"
    if gi.exists():
        patterns = gi.read_text(encoding="utf-8", errors="ignore").splitlines()
        return PathSpec.from_lines(GitWildMatchPattern, patterns)
    return PathSpec.from_lines(GitWildMatchPattern, [])

def should_skip(path: Path) -> bool:
    """Жёстко исключаем репозиторные внутренности и сам .gitignore из сборки."""
    if path.is_dir() and path.name == ".git":
        return True
    return False  # .gitignore фильтруем не здесь, чтобы уметь логировать причину

def is_binary_file(path: Path, sniff_bytes: int = 4096) -> bool:
    # По расширению
    if path.suffix.lower() in BINARY_EXTS:
        return True
    # Файлы с известным текстовым расширением (см. MARKDOWN_LANG) всегда считаем текстовыми
    if path.suffix.lower() in MARKDOWN_LANG:
        return False
    try:
        with path.open("rb") as fh:
            chunk = fh.read(sniff_bytes)
        if b"\x00" in chunk:
            return True
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError:
            return True
        return False
    except Exception:
        return True  # нечитаемый файл — безопаснее пропустить

def md_lang_for(path: Path) -> str:
    return MARKDOWN_LANG.get(path.suffix.lower(), "")

def iter_all_files(root: Path) -> Iterable[Path]:
    """Идём по всем файлам, НЕ применяя .gitignore на этом этапе.
    Это позволяет позже корректно залогировать, что и почему исключили.
    """
    for r, dirs, files in os.walk(root):
        rpath = Path(r)
        # исключаем .git, но не .gitignore — его логируем отдельно
        dirs[:] = [d for d in dirs if not should_skip(rpath / d)]
        for f in files:
            p = rpath / f
            if not should_skip(p):
                yield p

def now_tag() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")

def project_name(p: Path) -> str:
    return p.name or "project"

def ensure_out_dir(root: Path, project: str) -> Path:
    out = Path("bundles") / f"{project}_{now_tag()}"
    out.mkdir(parents=True, exist_ok=True)
    return out

def header_len(rel: str, lang: str, idx: Tuple[int,int]|None) -> int:
    if idx:
        i, n = idx
        hdr = f"# FILE: {rel} (chunk {i}/{n})\n```{lang}\n"
    else:
        hdr = f"# FILE: {rel}\n```{lang}\n"
    return len(hdr)

def write_part_file(out_dir: Path, part_idx: int) -> Path:
    return out_dir / f"build_{part_idx}.txt"

def split_by_lines(code: str, limit: int, rel: str, lang: str) -> List[Tuple[str,Tuple[int,int]]]:
    """
    Возвращает список (chunk_text, (i, n)), где каждый chunk влезает в лимит
    вместе с соответствующим заголовком и FOOTER.
    """
    lines = code.splitlines(keepends=True)
    chunks: List[str] = []
    cur: List[str] = []
    worst_head = header_len(rel, lang, (9_999, 9_999))
    for ln in lines:
        candidate = "".join(cur) + ln
        if len(candidate) + worst_head + len(FOOTER) <= limit:
            cur.append(ln)
        else:
            if cur:
                chunks.append("".join(cur)); cur = [ln]
            else:
                s = ln
                max_payload = max(1, limit - worst_head - len(FOOTER))
                while len(s) > max_payload:
                    chunks.append(s[:max_payload])
                    s = s[max_payload:]
                cur = [s]
    if cur:
        chunks.append("".join(cur))
    result: List[Tuple[str,Tuple[int,int]]] = []
    total = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        head = header_len(rel, lang, (i, total))
        if len(chunk) + head + len(FOOTER) <= limit:
            result.append((chunk, (i, total)))
            continue
        lines = chunk.splitlines(keepends=True)
        buf: List[str] = []
        for ln in lines:
            if len("".join(buf)+ln) + head + len(FOOTER) <= limit:
                buf.append(ln)
            else:
                break
        if not buf:
            max_payload = max(1, limit - head - len(FOOTER))
            buf = [chunk[:max_payload]]
        result.append(("".join(buf), (i, total)))
    return result

# ─────────────────────────────── основная логика ─────────────────────────────
def bundle(src_dir: Path, char_limit: int) -> None:
    src_dir = src_dir.resolve()
    if not src_dir.is_dir():
        print(f"❌ Нет директории: {src_dir}")
        return

    spec = load_gitignore_spec(src_dir)

    # Соберём все файлы (без применения .gitignore) для корректной отчётности
    all_files = list(iter_all_files(src_dir))
    if not all_files:
        print("❌ В директории нет файлов.")
        return

    included: List[Tuple[str, str, str]] = []  # (rel, code, lang)
    skipped_bin: List[str] = []
    skipped_decode: List[str] = []
    skipped_gitignore: List[str] = []

    for p in all_files:
        rel = p.relative_to(src_dir).as_posix()

        # Явно исключаем .gitignore и всё, что попало под pathspec (.gitignore)
        if p.name == ".gitignore" or spec.match_file(rel):
            skipped_gitignore.append(rel)
            continue

        # Бинарные
        if is_binary_file(p):
            skipped_bin.append(rel)
            continue

        # Текст/код (UTF-8)
        try:
            code = p.read_text(encoding="utf-8")  # strict
        except UnicodeDecodeError:
            # Попробуем прочитать с заменой символов — файл всё равно считаем текстовым
            code = p.read_text(encoding="utf-8", errors="replace")

        lang = md_lang_for(p)
        included.append((rel, code, lang))

    if not included:
        print("❌ Подходящих текстовых файлов (после фильтров) не осталось.")
        # Печатаем отчёт по исключениям, чтобы было понятно, что произошло
        if skipped_gitignore:
            print("ℹ️ Исключены по .gitignore:")
            for f in skipped_gitignore:
                print("   •", f)
        if skipped_bin:
            print("ℹ️ Пропущены бинарные:")
            for f in skipped_bin:
                print("   •", f)
        if skipped_decode:
            print("ℹ️ Пропущены (не UTF-8):")
            for f in skipped_decode:
                print("   •", f)
        return

    out_dir = ensure_out_dir(src_dir, project_name(src_dir))
    part_idx = 1
    out_path = write_part_file(out_dir, part_idx)
    fh = out_path.open("w", encoding="utf-8")

    # индекс проекта (ТОЛЬКО реально включаемые файлы)
    fh.write("## PROJECT OVERVIEW\n")
    for rel, _, _ in included:
        fh.write(f"{rel}\n")
    fh.write("\n")
    cur_size = fh.tell()

    kept = 0
    for rel, code, lang in included:
        base_header = f"# FILE: {rel}\n```{lang}\n"
        if len(code) + len(base_header) + len(FOOTER) > char_limit:
            chunks = split_by_lines(code, char_limit, rel, lang)
            for chunk, (i, n) in chunks:
                head = f"# FILE: {rel} (chunk {i}/{n})\n```{lang}\n"
                need = len(head) + len(chunk) + len(FOOTER)
                if cur_size + need > char_limit and cur_size:
                    fh.close()
                    part_idx += 1
                    fh = write_part_file(out_dir, part_idx).open("w", encoding="utf-8")
                    cur_size = 0
                fh.write(head); fh.write(chunk); fh.write(FOOTER)
                cur_size = fh.tell()
        else:
            head = base_header
            need = len(head) + len(code) + len(FOOTER)
            if cur_size + need > char_limit and cur_size:
                fh.close()
                part_idx += 1
                fh = write_part_file(out_dir, part_idx).open("w", encoding="utf-8")
                cur_size = 0
            fh.write(head); fh.write(code); fh.write(FOOTER)
            cur_size = fh.tell()
        kept += 1

    fh.close()
    print(f"✅ Bundled {kept} file(s) → {part_idx} part(s) in {out_dir}")
    if skipped_bin:
        print("ℹ️ Пропущены бинарные файлы:")
        for f in skipped_bin:
            print("   •", f)
    if skipped_decode:
        print("ℹ️ Пропущены файлы (не UTF-8):")
        for f in skipped_decode:
            print("   •", f)
    if skipped_gitignore:
        # Показываем только верхний уровень (корень или первая папка)
        top_level = set(f.split("/", 1)[0] for f in skipped_gitignore)
        print("ℹ️ Исключены по .gitignore (только верхний уровень):")
        for f in sorted(top_level):
            print("   •", f)

# ──────────────────────────────── CLI ────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Bundle project into text dumps.")
    ap.add_argument("source_dir", help="Project directory")
    ap.add_argument("--limit", required=True, help="3500t (tokens) или 14000c (chars)")
    args = ap.parse_args()
    char_limit = parse_limit(args.limit)
    bundle(Path(args.source_dir), char_limit)

if __name__ == "__main__":
    main()
