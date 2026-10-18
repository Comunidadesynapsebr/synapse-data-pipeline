from __future__ import annotations

import argparse
import asyncio
import sys

from .cleaner import process
from .collector import collect
from .config import load_config
from .publisher import publish
from .validate import validate_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(prog="synapse-pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("collect", "clean"):
        p = sub.add_parser(name)
        p.add_argument("--config", required=True)
        p.add_argument("--out", required=True)
        if name == "collect": p.add_argument("--manifest", required=True)
        else: p.add_argument("--input", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--config", required=True); p.add_argument("--input", required=True)
    p = sub.add_parser("publish")
    p.add_argument("--config", required=True); p.add_argument("--input", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.command == "collect":
        count = asyncio.run(collect(args.manifest, args.out, cfg)); print(f"Coletados: {count}")
    elif args.command == "clean":
        count = process(args.input, args.out, cfg); print(f"Publicáveis após limpeza: {count}")
    elif args.command == "validate":
        ok, errors = validate_jsonl(args.input)
        if not ok:
            print("\n".join(errors), file=sys.stderr); raise SystemExit(1)
        print("Validação OK")
    elif args.command == "publish":
        print(publish(args.input, cfg))


if __name__ == "__main__":
    main()
