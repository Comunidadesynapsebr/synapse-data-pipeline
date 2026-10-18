from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import ftfy
from datasketch import MinHash, MinHashLSH
from trafilatura import extract

from .config import Config

_WS = re.compile(r"\s+")


def clean_text(text: str, cfg: Config) -> str:
    if cfg.cleaning.get("normalize_unicode", True):
        text = unicodedata.normalize("NFKC", ftfy.fix_text(text))
    if cfg.cleaning.get("remove_html", True):
        extracted = extract(text, include_comments=False, include_tables=False)
        if extracted:
            text = extracted
    text = _WS.sub(" ", text).strip()
    return text


def _minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    tokens = text.lower().split()
    for i in range(max(0, len(tokens) - 4)):
        m.update(" ".join(tokens[i:i+5]).encode())
    return m


def process(input_path: str | Path, output_path: str | Path, cfg: Config) -> int:
    min_chars = int(cfg.cleaning.get("min_chars", 200))
    max_chars = int(cfg.cleaning.get("max_chars", 2_000_000))
    threshold = float(cfg.cleaning.get("minhash_threshold", 0.9))
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    seen_exact: set[str] = set()
    rows: list[dict] = []

    with Path(input_path).open(encoding="utf-8") as fh:
        for raw in fh:
            item = json.loads(raw)
            text = clean_text(str(item.get("text", "")), cfg)
            if not min_chars <= len(text) <= max_chars:
                continue
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest in seen_exact:
                continue
            mh = _minhash(text)
            key = f"doc-{len(rows)}"
            if lsh.query(mh):
                continue
            lsh.insert(key, mh)
            seen_exact.add(digest)
            rows.append({
                "id": key,
                "text": text,
                "source_url": item.get("source_url", ""),
                "source_title": item.get("source_title", ""),
                "license": item.get("license", "unknown"),
                "language": cfg.project.get("language", "und"),
                "content_sha256": digest,
                "collected_at": item.get("collected_at", ""),
                "pipeline_version": "0.1.0",
            })

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fmt = cfg.project.get("output_format", "jsonl")
    if fmt == "jsonl":
        with Path(output_path).open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    elif fmt == "txt":
        Path(output_path).write_text("\n\n".join(r["text"] for r in rows), encoding="utf-8")
    else:
        import pandas as pd
        frame = pd.DataFrame(rows)
        if fmt == "csv":
            frame.to_csv(output_path, index=False)
        elif fmt == "parquet":
            frame.to_parquet(output_path, index=False)
    return len(rows)
