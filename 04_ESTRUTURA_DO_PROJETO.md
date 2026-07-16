# 📁 Estrutura Completa do Projeto — Personal RAG Assistant V1

> Layout `src/`-based (recomendado para pacotes Python profissionais), com camadas espelhando
> o SDD. Cada arquivo tem uma responsabilidade única. `📄` = arquivo, `📂` = pasta.

---

## Árvore completa

```
personal-rag-assistant/
│
├── 📄 README.md                      # apresentação do projeto (doc 02)
├── 📄 pyproject.toml                 # deps, metadados, config de ruff/pytest (uv)
├── 📄 uv.lock                        # lockfile de dependências (reprodutibilidade)
├── 📄 .env.example                   # template de variáveis (SEM segredos)
├── 📄 .env                           # segredos reais (GIT-IGNORED)
├── 📄 .gitignore                     # ignora data/, .env, __pycache__, .venv...
├── 📄 .pre-commit-config.yaml        # hooks: ruff, format, checagens
├── 📄 LICENSE                        # MIT
├── 📄 Makefile                       # atalhos: make ingest / test / run / eval
│
├── 📂 src/
│   └── 📂 rag_assistant/             # pacote principal
│       │
│       ├── 📄 __init__.py
│       ├── 📄 __main__.py            # ponto de entrada CLI (rag ...)
│       ├── 📄 cli.py                 # comandos typer: ingest, ask, eval
│       │
│       ├── 📂 config/
│       │   ├── 📄 __init__.py
│       │   └── 📄 settings.py        # pydantic-settings: lê .env, valida config
│       │
│       ├── 📂 common/                # utilidades transversais
│       │   ├── 📄 __init__.py
│       │   ├── 📄 cache.py           # cache de embedding/resposta (SQLite/disco) — economiza quota
│       │   └── 📄 ratelimit.py       # throttle de RPM + backoff/retry em 429 (free tier)
│       │
│       ├── 📂 domain/                # DOMÍNIO — tipos e contratos (Ports). Sem I/O.
│       │   ├── 📄 __init__.py
│       │   ├── 📄 models.py          # RawDocument, Chunk, EmbeddedChunk, RetrievedChunk, Answer
│       │   ├── 📄 ports.py           # Protocols: EmbeddingProvider, LLMProvider, VectorStore
│       │   └── 📄 exceptions.py      # erros de domínio (DocumentLoadError, etc.)
│       │
│       ├── 📂 ingestion/             # INGESTÃO — arquivo → chunks
│       │   ├── 📄 __init__.py
│       │   ├── 📄 loaders.py         # PDF, DOCX, MD, TXT → RawDocument (+ doc_hash)
│       │   ├── 📄 chunker.py         # RecursiveCharacterTextSplitter (tamanho/overlap)
│       │   └── 📄 pipeline.py        # orquestra load → chunk → embed → upsert (incremental)
│       │
│       ├── 📂 embeddings/            # ADAPTADORES de embedding
│       │   ├── 📄 __init__.py
│       │   ├── 📄 gemini_embeddings.py   # text-embedding-004 (free tier)
│       │   ├── 📄 ollama_embeddings.py   # nomic-embed-text (local)
│       │   ├── 📄 openai_embeddings.py   # OPCIONAL (pago)
│       │   └── 📄 factory.py         # devolve o provider certo conforme config
│       │
│       ├── 📂 llm/                   # ADAPTADORES de LLM
│       │   ├── 📄 __init__.py
│       │   ├── 📄 gemini_llm.py      # Gemini free tier (principal cloud)
│       │   ├── 📄 groq_llm.py        # Groq free (fallback, OpenAI-compat)
│       │   ├── 📄 ollama_llm.py      # Llama 3.2 local
│       │   ├── 📄 openai_llm.py      # OPCIONAL (pago)
│       │   ├── 📄 anthropic_llm.py   # OPCIONAL (pago)
│       │   └── 📄 factory.py
│       │
│       ├── 📂 vectorstore/           # ADAPTADORES de vector store
│       │   ├── 📄 __init__.py
│       │   ├── 📄 chroma_store.py    # implementação V1
│       │   ├── 📄 pgvector_store.py  # STUB p/ V2 (ponto de extensão)
│       │   └── 📄 factory.py
│       │
│       ├── 📂 retrieval/
│       │   ├── 📄 __init__.py
│       │   └── 📄 retriever.py       # embed_query → store.query(k) → RetrievedChunk[]
│       │
│       ├── 📂 rag/                   # APLICAÇÃO — o coração
│       │   ├── 📄 __init__.py
│       │   ├── 📄 pipeline.py        # RAGPipeline.ask(): retrieve → prompt → gerar → citar
│       │   ├── 📄 prompts.py         # templates (regras anti-alucinação, citação)
│       │   └── 📄 citations.py       # extrai/formata fontes a partir dos chunks
│       │
│       ├── 📂 evaluation/
│       │   ├── 📄 __init__.py
│       │   ├── 📄 evaluator.py       # roda golden set: Recall@5, latência, custo
│       │   ├── 📄 metrics.py         # cálculo de recall, custo por tokens, agregações
│       │   └── 📄 report.py          # gera report.md + report.json
│       │
│       ├── 📂 observability/
│       │   ├── 📄 __init__.py
│       │   ├── 📄 tracer.py          # Langfuse (opcional) OU trace JSON local se sem keys
│       │   └── 📄 logging.py         # logging estruturado
│       │
│       └── 📂 app/
│           ├── 📄 __init__.py
│           └── 📄 streamlit_app.py   # UI: abas Chat / Ingestão / Métricas
│
├── 📂 data/                          # GIT-IGNORED
│   ├── 📂 documents/                 # seus arquivos de entrada
│   ├── 📂 chroma/                    # persistência do vector store (coleção por modelo de embedding)
│   ├── 📂 cache/                     # cache de embedding/resposta (economia de quota)
│   └── 📂 traces/                    # traces JSON locais (fallback quando sem Langfuse)
│
├── 📂 evaluation/
│   ├── 📄 golden_set.json            # 30 perguntas + fonte esperada
│   └── 📂 reports/                   # relatórios gerados (report.md/json)
│
├── 📂 tests/
│   ├── 📄 __init__.py
│   ├── 📄 conftest.py                # fixtures (fakes de provider/store, docs de exemplo)
│   ├── 📂 unit/
│   │   ├── 📄 test_chunker.py
│   │   ├── 📄 test_loaders.py
│   │   ├── 📄 test_metrics.py
│   │   └── 📄 test_prompts.py
│   ├── 📂 contract/
│   │   ├── 📄 test_embedding_provider.py
│   │   ├── 📄 test_llm_provider.py
│   │   └── 📄 test_vectorstore.py
│   └── 📂 integration/
│       └── 📄 test_rag_pipeline.py   # ingest→ask ponta a ponta (store em memória)
│
├── 📂 docs/
│   ├── 📄 SDD.md                     # doc 01
│   ├── 📄 DIAGRAMS.md                # doc 03
│   ├── 📄 PROJECT_STRUCTURE.md       # este doc
│   ├── 📄 EVALUATION.md              # metodologia do golden set / métricas
│   ├── 📄 PROJECT_PLAN.md            # doc 05
│   └── 📂 assets/
│       └── 📄 demo.gif               # gif de uso p/ README
│
├── 📂 scripts/
│   ├── 📄 build_golden_set.py        # helper p/ montar o golden_set.json
│   └── 📄 benchmark.py               # roda comparação nuvem vs local
│
└── 📂 .github/
    └── 📂 workflows/
        └── 📄 ci.yml                 # lint + testes em cada push/PR
```

---

## Por que este layout

| Escolha | Motivo |
|---------|--------|
| **`src/`-based** | Evita import acidental do pacote não instalado; padrão de projetos sérios |
| **`domain/` isolado** | Tipos e contratos sem I/O → testável e estável; adaptadores dependem dele, não o contrário |
| **Pastas por adaptador** (`embeddings/`, `llm/`, `vectorstore/`) | Cada provider é plugável; adicionar um novo = novo arquivo, não refatoração |
| **`factory.py` em cada adaptador** | Um único lugar decide "qual implementação" a partir da config |
| **`pgvector_store.py` como stub** | Deixa o ponto de extensão do V2 **visível** no código |
| **`tests/` espelhando camadas** | unit / contract / integration separam velocidade e propósito |
| **`evaluation/` na raiz** | Golden set e relatórios são artefatos do projeto, versionáveis |
| **`data/` git-ignored** | Documentos pessoais e índice não vão pro repositório público |

---

## Convenções

- **Imports:** camadas de baixo (domínio) nunca importam de cima (app/adaptadores).
- **Config:** tudo que muda entre ambientes vive em `settings.py` + `.env`.
- **Nomes:** arquivos e módulos em `snake_case`; classes em `PascalCase`.
- **Um Protocol por capacidade** (embedding, LLM, store) — só cria abstração onde há 2+ implementações reais.

---

## `.env.example` (versionado, sem segredos)

```env
RAG_MODE=cloud
LLM_PROVIDER=gemini          # gemini | groq | ollama | (opcional: openai | anthropic)
EMBEDDING_PROVIDER=gemini    # gemini | ollama | (opcional: openai)

GEMINI_API_KEY=
GROQ_API_KEY=                # opcional (fallback)
OLLAMA_BASE_URL=http://localhost:11434

GEMINI_LLM_MODEL=gemini-2.5-flash-lite
GEMINI_EMBED_MODEL=text-embedding-004
OLLAMA_LLM_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text

CHUNK_SIZE=800
CHUNK_OVERLAP=120
TOP_K=5
CHROMA_PATH=./data/chroma
CACHE_PATH=./data/cache

# Observabilidade OPCIONAL (vazio → trace JSON local em ./data/traces)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

---

*A estrutura reflete diretamente as camadas do [SDD](01_SDD_Personal_RAG_V1.md) §4 e os componentes §6.*
