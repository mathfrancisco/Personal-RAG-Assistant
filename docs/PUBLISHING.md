# 🚦 Publicação — Checklist do que falta (parte manual)

O código das Fases 0–7 está implementado, testado (CI verde, só fakes) e commitado.
O que resta **exige a sua máquina, o seu corpus e ações humanas** — não dá para automatizar
aqui. Este é o roteiro para fechar o gate do semestre (Fase 7).

> Legenda: 🟥 bloqueia a publicação · 🟨 recomendado · ⬜ opcional.

---

## 1. Provar o ambiente local (Fase 0 — risco em aberto)

- [ ] 🟥 Subir o Ollama e baixar modelos:
  ```bash
  make ollama-up && make ollama-pull
  uv run python scripts/hello.py     # 3 respostas (Ollama + Gemini se houver key)
  ```
- [ ] 🟥 **Medir VRAM** e confirmar que `llama3.2:3b` cabe na **RTX 5060 8GB**.
  Se estourar, cair para `llama3.2:1b` / `qwen2.5:1.5b` (ajustar `OLLAMA_LLM_MODEL` no `.env`).

## 2. Smoke ponta a ponta com serviços reais (DoD manual das Fases 1–5)

Os testes cobrem tudo com fakes/Chroma local. Falta rodar de verdade uma vez:

- [ ] 🟥 `uv run rag ingest ./data/documents` (colocar PDFs/MD/TXT/DOCX reais primeiro).
- [ ] 🟥 Rerun do ingest → confirmar que **pula os inalterados** (incremental).
- [ ] 🟥 `uv run rag search "..."` → trechos coerentes com score/fonte.
- [ ] 🟥 `uv run rag ask "..." --stream` → resposta **com fonte citada**; pergunta fora do corpus → "não encontrei".
- [ ] 🟨 Testar `RAG_MODE=hybrid` (com `GEMINI_API_KEY`): derrubar o Ollama e ver o **fallback Gemini**.
- [ ] 🟨 Conferir um trace gerado em `data/traces/traces.jsonl` (ou no Langfuse, se configurado).

## 3. Golden set + métricas reais (Fase 5)

- [ ] 🟥 Montar **≥ 30 perguntas** sobre o seu corpus em `evaluation/golden_set.json`
  (incluir paráfrases e perguntas `out_of_corpus`). Validar:
  ```bash
  uv run python scripts/build_golden_set.py
  ```
- [ ] 🟥 Rodar e gerar relatório:
  ```bash
  uv run rag eval                    # local (Ollama)
  RAG_MODE=hybrid uv run rag eval    # fallback Gemini
  ```
- [ ] 🟥 **Recall@5 ≥ 0,80** — se abaixo, iterar `CHUNK_SIZE` / `TOP_K` e rodar de novo.
- [ ] 🟥 Colar os números reais nas tabelas de métricas do **`README.md` e `README.en.md`**
  (hoje estão com `_preencher_` / `_fill_`).

## 4. Mídia do README (Fase 7)

- [ ] 🟥 Gravar `docs/assets/demo.gif` (pergunta → streaming → fonte expandida na UI Streamlit).
  Sugestão: [ScreenToGif](https://www.screentogif.com/). Ver [`assets/README.md`](assets/README.md).
- [ ] 🟨 Screenshots: aba **Métricas**, `rag ask` no terminal, um trace.

## 5. Revisão de texto e links

- [ ] 🟨 Rodar o verificador de links relativos:
  ```bash
  uv run python scripts/check_links.py
  ```
  > Vai apontar `docs/assets/demo.gif` como quebrado até você gravar o GIF — esperado.
- [ ] 🟨 Revisar o **README EN** (tradução automática — passar o olho humano antes de publicar).

## 6. Divulgação (gate do semestre)

- [ ] 🟥 Tornar o repositório **público**.
- [ ] 🟨 Post técnico no **LinkedIn**: o que construiu, decisões (Ports & Adapters, local-first
  com Ollama, custo $0), e as métricas reais da seção 3.
- [ ] ⬜ Atualizar headline do LinkedIn: "AI Engineer | Building with LLMs".

---

## ✅ Definição de pronto (espelha o DoD da Fase 7)

- [ ] Repo público com README (PT + EN) + **GIF de demo**.
- [ ] Métricas reais publicadas (Gemini vs Ollama).
- [ ] Funciona em `local` e `hybrid`, custo **$0**.
- [ ] CI verde + cobertura.
- [ ] Post de divulgação feito.
