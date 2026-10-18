import json
from pathlib import Path

from synapse_pipeline.cleaner import process
from synapse_pipeline.config import Config
from synapse_pipeline.validate import validate_jsonl


def cfg():
    return Config({
        "project": {"output_format": "jsonl", "language": "pt"},
        "cleaning": {"min_chars": 10, "max_chars": 10000, "minhash_threshold": 0.9},
    })


def test_clean_deduplicates_and_hashes(tmp_path: Path):
    text = "Este é um documento público suficientemente longo para o teste." * 3
    source = tmp_path / "raw.jsonl"
    source.write_text("\n".join(json.dumps({"text": text, "source_url": "https://example.org", "license": "CC BY 4.0"}) for _ in range(2)), encoding="utf-8")
    output = tmp_path / "clean.jsonl"
    assert process(source, output, cfg()) == 1
    ok, errors = validate_jsonl(output)
    assert ok, errors
