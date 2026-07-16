# 📊 Avaliação — Metodologia

Como o Personal RAG Assistant é medido, de forma **reproduzível** e a **custo real $0**.

## Golden set

- Arquivo: [`evaluation/golden_set.json`](../evaluation/golden_set.json).
- Cada item: `question`, `expected_source` (casa por **substring** com o caminho do
  arquivo esperado) e `out_of_corpus` (perguntas que **devem** dar "não encontrei").
- Recomendado: **≥ 30 perguntas** sobre o seu corpus (`data/documents/`), incluindo
  paráfrases e perguntas fora do corpus (controle de alucinação).
- Validar o schema:

  ```bash
  uv run python scripts/build_golden_set.py
  ```

> O golden set é **específico do seu corpus** — as 5 entradas versionadas são um
> exemplo de formato, não um benchmark. Edite o JSON apontando para os seus arquivos.

## Métricas

| Métrica | O que mede | O que **não** mede |
|---|---|---|
| **Recall@k** | Fração de perguntas em que a fonte esperada aparece nos top-k trechos recuperados. Para `out_of_corpus`, acerto = **nada** recuperado. | Se a *resposta* está correta — só se o trecho certo foi recuperado. |
| **Tokens/query** | Média de tokens de entrada/saída do LLM por pergunta. | — |
| **Custo calculado** | USD-equivalente **se rodasse no tier pago** (tabela em `evaluation/metrics.py`). | O custo real, que é **$0** (Ollama local / Gemini free tier). |
| **Latência** | Tempo médio de **retrieval** e de **geração**, medidos separadamente. | Cold start / download de modelo. |

## Reprodutibilidade

- `temperature=0` + **modelo pinado** → saída determinística.
- **Cache de respostas** (`ResponseCache`, chave = modelo + prompt): o **segundo run
  não faz nenhuma chamada nova** ao LLM → não gasta quota do free tier.
- O cache de **embeddings** (Fase 1) cobre a etapa de retrieval no rerun.

## Rodando

```bash
uv run rag eval                     # usa evaluation/golden_set.json e TOP_K da config
uv run rag eval --golden custom.json
uv run rag eval --no-cache          # força chamadas novas (ignora cache de respostas)
```

Saída: `evaluation/reports/report.md` (tabela p/ o README) e `report.json`
(consumido pela aba **Métricas** do Streamlit).

## Meta de qualidade (DoD Fase 5)

- **Recall@5 ≥ 0,80.** Abaixo disso, iterar `CHUNK_SIZE` / `TOP_K` — é para isso que
  a métrica existe (medir antes de otimizar).
