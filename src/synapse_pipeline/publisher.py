from __future__ import annotations

from pathlib import Path

from huggingface_hub import HfApi

from .config import Config


def publish(input_path: str | Path, cfg: Config) -> str:
    token = cfg.hf_token
    if not token:
        raise RuntimeError("HF_TOKEN não encontrado; configure o secret no ambiente.")
    dataset_id = cfg.project.get("dataset_name")
    if not dataset_id or "/" not in dataset_id:
        raise ValueError("project.dataset_name deve ser 'usuario-ou-org/nome-do-dataset'")
    api = HfApi(token=token)
    api.create_repo(repo_id=dataset_id, repo_type="dataset", private=bool(cfg.publishing.get("private", False)), exist_ok=True)
    api.upload_file(
        path_or_fileobj=str(input_path),
        path_in_repo=Path(input_path).name,
        repo_id=dataset_id,
        repo_type="dataset",
        commit_message=cfg.publishing.get("commit_message", "Atualiza dataset processado"),
    )
    return f"https://huggingface.co/datasets/{dataset_id}"
