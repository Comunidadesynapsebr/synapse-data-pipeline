# Synapse Data Pipeline

Pipeline profissional, reproduzível e auditável para coletar **fontes públicas autorizadas**, limpar texto, remover duplicatas e publicar datasets no Hugging Face. O projeto é licenciado sob Apache-2.0.

> **Uso responsável:** “público” não significa automaticamente “livre para redistribuição”. O pipeline exige metadados de origem/licença, respeita `robots.txt`, usa HTTPS por padrão, limita concorrência e velocidade e não contorna paywalls, CAPTCHAs, autenticação ou controles técnicos. Verifique os termos e direitos de cada fonte antes de publicar.

## Fluxo em três etapas

1. **Coleta:** URLs fornecidas pelo usuário ou manifestos licenciados; `robots.txt`, limites, retries e `User-Agent` identificável.
2. **Limpeza profunda:** extração de texto, remoção de HTML/boilerplate, Unicode, espaços, documentos muito curtos/longos e desduplicação exata + MinHash.
3. **Normalização/publicação:** esquema estável (`id`, `text`, `source_url`, `source_title`, `license`, `language`, `content_sha256`, `collected_at`), exportação para JSONL/Parquet/CSV/TXT e upload opcional ao Hugging Face.

## Instalação

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
cp configs/config.example.yaml configs/config.yaml
cp .env.example .env
```

Edite `configs/config.yaml`. O nome do dataset, o formato e a quantidade máxima de tokens ficam nessa configuração. O token **não** é gravado no YAML: use `HF_TOKEN` no ambiente ou um secret manager.

## Uso

Manifesto mínimo (`examples/manifest.jsonl`):

```json
{"url":"https://pt.wikipedia.org/wiki/Apache_Software_Foundation","license":"CC BY-SA 4.0","title":"Apache Software Foundation"}
```

```bash
# Coletar (sem burlar restrições)
python -m synapse_pipeline.cli collect --manifest examples/manifest.jsonl --out data/raw/raw.jsonl --config configs/config.yaml

# Limpar + deduplicar + normalizar
python -m synapse_pipeline.cli clean --input data/raw/raw.jsonl --out data/clean/dataset.jsonl --config configs/config.yaml

# Validar esquema, hashes e estatísticas
python -m synapse_pipeline.cli validate --input data/clean/dataset.jsonl --config configs/config.yaml

# Publicar; requer HF_TOKEN e revisão final das licenças
python -m synapse_pipeline.cli publish --input data/clean/dataset.jsonl --config configs/config.yaml
```

Para livros, use apenas obras em domínio público ou com licença que permita redistribuição, e registre a licença por documento. Para grandes volumes, use fontes oficiais/arquivos licenciados em vez de scraping indiscriminado.

## Segurança e governança

- Nenhum token, cookie, dado bruto ou dataset é versionado.
- O publisher falha se `HF_TOKEN` estiver ausente e não imprime o segredo.
- Faça revisão humana de licenças, PII, takedown e qualidade antes de marcar o dataset como público.
- Registre `source_url`, `license`, timestamp, hash e versão do pipeline para auditoria.
