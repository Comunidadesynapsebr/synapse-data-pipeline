from __future__ import annotations

import hashlib
import json
from pathlib import Path

REQUIRED = {"id", "text", "source_url", "license", "content_sha256"}


def validate_jsonl(path: str | Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    ids: set[str] = set()
    with Path(path).open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"linha {line_no}: JSON inválido ({exc.msg})")
                continue
            missing = REQUIRED - row.keys()
            if missing:
                errors.append(f"linha {line_no}: campos ausentes {sorted(missing)}")
            if row.get("id") in ids:
                errors.append(f"linha {line_no}: id duplicado {row.get('id')}")
            ids.add(row.get("id"))
            actual = hashlib.sha256(str(row.get("text", "")).encode()).hexdigest()
            if row.get("content_sha256") != actual:
                errors.append(f"linha {line_no}: content_sha256 não confere")
            if not row.get("license") or row.get("license") == "unknown":
                errors.append(f"linha {line_no}: licença ausente/desconhecida")
    return not errors, errors
