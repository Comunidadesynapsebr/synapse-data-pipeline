#!/usr/bin/env python3
"""Atualiza config.yaml sem inserir tokens ou segredos no arquivo."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/config.yaml")
    p.add_argument("--dataset-name")
    p.add_argument("--output-format", choices=["jsonl", "parquet", "csv", "txt"])
    p.add_argument("--language")
    p.add_argument("--max-urls", type=int)
    p.add_argument("--concurrency", type=int)
    p.add_argument("--requests-per-second", type=float)
    p.add_argument("--min-chars", type=int)
    p.add_argument("--max-chars", type=int)
    p.add_argument("--minhash-threshold", type=float)
    p.add_argument("--hf-token-env", default="HF_TOKEN")
    p.add_argument("--private", action="store_true")
    args = p.parse_args()
    path = Path(args.config)
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    project = config.setdefault("project", {})
    collection = config.setdefault("collection", {})
    cleaning = config.setdefault("cleaning", {})
    publishing = config.setdefault("publishing", {})
    if args.dataset_name: project["dataset_name"] = args.dataset_name
    if args.output_format: project["output_format"] = args.output_format
    if args.language: project["language"] = args.language
    if args.concurrency is not None: collection["concurrency"] = max(1, args.concurrency)
    if args.requests_per_second is not None: collection["requests_per_second"] = max(0.01, args.requests_per_second)
    if args.min_chars is not None: cleaning["min_chars"] = max(1, args.min_chars)
    if args.max_chars is not None: cleaning["max_chars"] = max(cleaning.get("min_chars", 1), args.max_chars)
    if args.minhash_threshold is not None:
        if not 0 < args.minhash_threshold <= 1: raise SystemExit("--minhash-threshold deve estar em (0, 1]")
        cleaning["minhash_threshold"] = args.minhash_threshold
    publishing["hf_token_env"] = args.hf_token_env
    publishing["private"] = args.private
    path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Configuração atualizada: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
