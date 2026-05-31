from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Iterable

import discord

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".toml",
    ".csv",
    ".log",
    ".xml",
    ".html",
    ".css",
    ".sql",
}


def _safe_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", " ")).strip() or "file"


def _decode_bytes(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _trim_text(text: str, max_chars: int = 5000) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]..."


def _csv_preview(text: str, max_rows: int = 30) -> str:
    reader = csv.reader(io.StringIO(text))
    rows: list[list[str]] = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        rows.append(row)
    preview = "\n".join(", ".join(col[:120] for col in row) for row in rows)
    return _trim_text(preview, max_chars=5000)


def _extract_zip_text(zip_path: Path, extracted_dir: Path) -> list[str]:
    snippets: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extracted_dir)
        for info in archive.infolist():
            if info.is_dir():
                continue
            internal_path = extracted_dir / info.filename
            suffix = internal_path.suffix.lower()
            if suffix not in TEXT_EXTENSIONS:
                continue
            try:
                text = _decode_bytes(internal_path.read_bytes())
                if suffix == ".csv":
                    text = _csv_preview(text)
                else:
                    text = _trim_text(text)
                snippets.append(f"[ZIP:{info.filename}]\n{text}")
            except Exception:
                continue
    return snippets


async def ingest_attachments(
    attachments: Iterable[discord.Attachment], storage_dir: Path
) -> tuple[list[str], list[Path]]:
    storage_dir.mkdir(parents=True, exist_ok=True)
    extracted_root = storage_dir / "unzipped"
    extracted_root.mkdir(parents=True, exist_ok=True)

    prompt_snippets: list[str] = []
    stored_paths: list[Path] = []

    for attachment in attachments:
        file_name = _safe_name(attachment.filename)
        saved_path = storage_dir / file_name
        await attachment.save(saved_path)
        stored_paths.append(saved_path)

        suffix = saved_path.suffix.lower()
        if suffix == ".zip":
            zip_extract_dir = extracted_root / saved_path.stem
            zip_extract_dir.mkdir(parents=True, exist_ok=True)
            try:
                zip_snippets = _extract_zip_text(saved_path, zip_extract_dir)
                if zip_snippets:
                    prompt_snippets.append("\n".join(zip_snippets[:8]))
                else:
                    prompt_snippets.append(
                        f"[ZIP:{attachment.filename}] Extracted to disk, but no supported text files were found."
                    )
            except zipfile.BadZipFile:
                prompt_snippets.append(f"[ZIP:{attachment.filename}] Invalid zip file.")
            continue

        try:
            raw = saved_path.read_bytes()
            if suffix in TEXT_EXTENSIONS:
                text = _decode_bytes(raw)
                if suffix == ".csv":
                    preview = _csv_preview(text)
                elif suffix == ".json":
                    parsed = json.loads(text)
                    preview = _trim_text(json.dumps(parsed, indent=2))
                else:
                    preview = _trim_text(text)
                prompt_snippets.append(f"[FILE:{attachment.filename}]\n{preview}")
            else:
                prompt_snippets.append(
                    f"[FILE:{attachment.filename}] Stored on disk at `{saved_path.as_posix()}`. "
                    "Binary/non-text file, cannot deeply parse without extra libraries."
                )
        except Exception as exc:
            prompt_snippets.append(f"[FILE:{attachment.filename}] Failed to read file: {exc}")

    return prompt_snippets, stored_paths
