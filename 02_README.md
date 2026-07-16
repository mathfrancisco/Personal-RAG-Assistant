# 🧠 Personal RAG Assistant

> Um assistente de IA local que **responde perguntas sobre os seus próprios documentos** —
> com citação de fontes, modo 100% offline e métricas reais de qualidade, custo e latência.

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11+-blue">
  <img alt="LangChain" src="https://img.shields.io/badge/framework-LangChain-green">
  <img alt="Vector Store" src="https://img.shields.io/badge/vectorstore-ChromaDB-orange">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
  <img alt="CI" src="https://img.shields.io/badge/CI-GitHub_Actions-black">
</p>

> 🇬🇧 **Nota estratégica:** para o portfólio público (alvo: mercado US), considere manter este README
> em **inglês**. Este arquivo está em PT-BR para o planejamento; posso gerar a versão EN quando quiser.

---

## ✨ O que é

**Personal RAG Assistant** indexa uma pasta de documentos seus (PDF, Markdown, TXT, DOCX) e
permite conversar com eles. Cada resposta é **ancorada nos seus arquivos** e vem com a **fonte
citada** — nada de alucinação sem rastro. Roda com modelos na nuvem **de graça** (Google Gemini
free tier, Groq de fallback) ou **100% localmente** (Ollama + Llama 3.2), sem enviar nada para fora.
Custo do projeto: **$0**.

Projeto construído seguindo um **SDD completo** ([`docs/SDD.md`](docs/SDD.md)) com arquitetura
provider-agnostic — trocar embedding, LLM ou vector store é uma mudança de configuração.

---

## 🎬 Demo

> _(inserir GIF de uso: fazer uma pergunta e receber resposta com fonte citada)_

![demo](docs/assets/demo.gif)

---

## 🚀 Features

- 📄 **Ingestão multi-formato** — PDF, Markdown, TXT, DOCX.
- 🔍 **Busca semântica** — recupera os trechos mais relevantes (top-k).
- 💬 **Respostas com citação** — toda resposta aponta arquivo + trecho de origem.
- 🔒 **Modo local** — Ollama + Llama 3.2, zero chamadas externas.
- ☁️ **Modo nuvem grátis** — Google Gemini (free tier); Groq como fallback quando a quota do dia acaba.
- 💸 **Custo $0** — roda inteiro em free tiers; custo em USD é *calculado* para referência.
- ♻️ **Reindexação incremental** — só reprocessa o que mudou (hash de arquivo).
- 📊 **Métricas embutidas** — latência, tokens/query, custo calculado e Recall@5 num golden set de 30 perguntas.
- 🔭 **Observabilidade** — trace ponta a ponta via Langfuse.
- 🧩 **Provider-agnostic** — arquitetura Ports & Adapters.

---

## 🏗️ Arquitetura (visão rápida)

```mermaid
flowchart LR
    U([Usuário]) -->|pergunta| UI[Streamlit UI]
    UI --> RAG[RAG Pipeline]
    RAG -->|embed query| EMB[Embedding Provider]
    RAG -->|top-k| VS[(Vector Store<br/>ChromaDB)]
    RAG -->|prompt + contexto| LLM[LLM Provider<br/>Gemini / Groq / Ollama]
    LLM -->|resposta + fontes| UI
    subgraph Ingestão
      DOCS[/Seus documentos/] --> LD[Loader] --> CH[Chunker] --> EMB --> VS
    end
```

> Diagramas completos (sequência, dados, classes) em [`docs/DIAGRAMS.md`](docs/DIAGRAMS.md).

---

## 🧰 Stack

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.11+ |
| Orquestração | LangChain |
| Vector store | ChromaDB (local) |
| Embeddings | Google `text-embedding-004` (free) / `nomic-embed-text` (Ollama) |
| LLM | Gemini (free) · Groq (free, fallback) · Llama 3.2 (Ollama) |
| Frontend | Streamlit |
| Observabilidade | Langfuse |
| Qualidade | pytest · ruff · pre-commit |
| Deps | uv |

---

## ⚡ Quickstart

### Pré-requisitos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) instalado
- **Modo nuvem (grátis):** chave da [Google AI Studio](https://aistudio.google.com/apikey) (Gemini free tier). Opcional: chave [Groq](https://console.groq.com) para fallback.
- **Modo local:** [Ollama](https://ollama.com) com `llama3.2` e `nomic-embed-text` baixados (`ollama pull llama3.2 && ollama pull nomic-embed-text`)

### 1. Clonar e instalar
```bash
git clone https://github.com/mathfrancisco/Personal-RAG-Assistant.git
cd Personal-RAG-Assistant
uv sync
```

### 2. Configurar
```bash
cp .env.example .env
# edite .env com suas chaves (ou deixe em modo local)
```

### 3. Indexar seus documentos
```bash
# coloque arquivos em ./data/documents/ e rode:
uv run rag ingest ./data/documents
```

### 4. Perguntar
```bash
# via CLI:
uv run rag ask "Qual o prazo de entrega descrito no contrato X?"

# ou via interface web:
uv run streamlit run src/rag_assistant/app/streamlit_app.py
```

---

## 🎛️ Configuração (`.env`)

```env
# Modo: "cloud" ou "local"
RAG_MODE=cloud

# Providers (todos free)
LLM_PROVIDER=gemini             # gemini | groq | ollama | (opcional: anthropic | openai)
EMBEDDING_PROVIDER=gemini       # gemini | ollama | (opcional: openai)

GEMINI_API_KEY=...              # Google AI Studio (free tier)
GROQ_API_KEY=...                # opcional, fallback quando a quota do Gemini acaba
OLLAMA_BASE_URL=http://localhost:11434

# Modelos (pinados p/ eval reproduzível)
GEMINI_LLM_MODEL=gemini-2.5-flash-lite
GEMINI_EMBED_MODEL=text-embedding-004
OLLAMA_LLM_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text

# Chunking
CHUNK_SIZE=800
CHUNK_OVERLAP=120
TOP_K=5

# Observabilidade (OPCIONAL — sem keys, cai p/ trace JSON local)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

> ⚠️ Trocar `EMBEDDING_PROVIDER` muda o espaço vetorial → **reindexe** (`rag ingest` de novo). Embeddings de modelos diferentes não são compatíveis.

---

## 📊 Métricas (exemplo — preencher com resultados reais)

Rode a avaliação sobre o golden set:
```bash
uv run rag eval
```

| Métrica | Modo nuvem (Gemini free) | Modo local (Llama 3.2) |
|---------|-------------------------:|-----------------------:|
| Latência média | _preencher_ ms | _preencher_ ms |
| Tokens médios/query | _preencher_ | _preencher_ |
| Custo real/query | **$0,00** (free tier) | **$0,00** (local) |
| Custo *calculado*/query | $ _preencher_ (equiv. tier pago) | — |
| Recall@5 (30 perguntas) | _preencher_ | _preencher_ |

> A metodologia de avaliação está em [`docs/EVALUATION.md`](docs/EVALUATION.md).

---

## 📁 Estrutura do projeto

```
personal-rag-assistant/
├── src/            # código (ingestão, retrieval, rag, eval, app)
├── data/           # documentos e vector store (git-ignored)
├── tests/          # testes automatizados
├── evaluation/     # golden set + relatórios
├── docs/           # SDD, diagramas, avaliação
└── ...             # config, CI, pyproject
```

> Árvore completa e comentada em [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md).

---

## 🗺️ Roadmap

- [x] **V1** — RAG básico, citação de fontes, modo local/nuvem, métricas essenciais.
- [ ] **V2** — Hybrid search (BM25 + dense), reranker, eval suite completo (Ragas/TruLens), dashboard.
- [ ] **V3** — migração para pgvector, deploy, frontend Next.js.

---

## 🧑‍💻 Motivação

Projeto bandeira do 1º semestre do meu roadmap de transição para **AI Engineering**. Serve tanto
como ferramenta pessoal quanto como demonstração pública de como projeto, meço e evoluo um
sistema RAG de ponta a ponta.

---

## 📄 Licença

MIT © Matheus
