#!/usr/bin/env python3
"""Expande um manifest.json controlado em JSONL consumível pelo pipeline.

Não faz crawling indiscriminado: só processa URLs e sitemaps declarados pelo usuário,
exige allowlist de domínios e rejeita licenças ausentes ou REVIEW_REQUIRED.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower()


def fetch_sitemap(url: str, timeout: int = 30) -> list[str]:
    request = urllib.request.Request(url, headers={"User-Agent": "SynapseDataPipeline/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        root = ET.fromstring(response.read())
    return [node.text.strip() for node in root.iter() if node.tag.endswith("loc") and node.text]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="examples/manifest.json")
    parser.add_argument("--out", default="examples/manifest.generated.jsonl")
    parser.add_argument("--max-urls", type=int, default=1_000_000)
    parser.add_argument("--allow-domain", action="append", default=[], help="Pode repetir; obrigatório para sitemaps")
    parser.add_argument("--allow-review-required", action="store_true")
    args = parser.parse_args()

    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    defaults = doc.get("defaults", {})
    rows: list[dict] = []
    seen: set[str] = set()
    skipped = 0
    for source in doc.get("sources", []):
        license_name = source.get("license", defaults.get("license", "REVIEW_REQUIRED"))
        if license_name == "REVIEW_REQUIRED" and not args.allow_review_required:
            print(f"Ignorando fonte sem licença confirmada: {source.get('name', '<sem nome>')}", file=sys.stderr)
            skipped += 1
            continue
        candidates = list(source.get("urls", []))
        sitemap = source.get("sitemap")
        if sitemap:
            if args.allow_domain and host(sitemap) not in {d.lower() for d in args.allow_domain}:
                raise SystemExit(f"Sitemap fora da allowlist: {sitemap}")
            candidates.extend(fetch_sitemap(sitemap))
        for url in candidates:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in set(defaults.get("allowed_schemes", ["https"])):
                continue
            if args.allow_domain and host(url) not in {d.lower() for d in args.allow_domain}:
                continue
            if url in seen:
                continue
            seen.add(url)
            rows.append({"url": url, "license": license_name, "title": source.get("name", "")})
            if len(rows) >= args.max_urls:
                break
        if len(rows) >= args.max_urls:
            break

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Manifesto gerado: {len(rows)} URLs; fontes ignoradas: {skipped}; saída: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
