# 📐 Software Design Document (SDD) — Personal RAG Assistant V1

| Campo | Valor |
|-------|-------|
| **Projeto** | Personal RAG Assistant V1 |
| **Autor** | Matheus |
| **Versão** | 1.0 |
| **Status** | Draft → Baseline |
| **Contexto** | Projeto bandeira do 1º semestre — Roadmap AI Engineering (Univesp) |
| **Padrão base** | IEEE 1016 (Software Design Descriptions) + arc42, adaptados |

> **Como ler:** este SDD descreve *como* o sistema é projetado e *por que* cada decisão foi tomada.
> Ele é o contrato entre a intenção e a implementação. Se o código divergir do SDD, um dos dois está errado.

---

## 1. Introdução

### 1.1 Propósito
Descrever a arquitetura, o design de dados, os componentes e as decisões de projeto do **Personal RAG Assistant V1**, um sistema de *Retrieval-Augmented Generation* local que responde perguntas sobre documentos pessoais do usuário, com rastreabilidade de fontes e métricas de qualidade/custo/latência.

### 1.2 Escopo
O V1 cobre: ingestão de documentos, indexação vetorial, recuperação semântica, geração ancorada com citação, interface de chat e um harness mínimo de avaliação. **Não** cobre hybrid search, reranking, eval avançado, multiusuário ou deploy em produção (ver §12 e doc 00).

### 1.3 Definições e siglas

| Termo | Significado |
|-------|-------------|
| **RAG** | Retrieval-Augmented Generation — recuperar contexto e usá-lo para gerar a resposta |
| **Chunk** | Fragmento de um documento (ex.: ~800 tokens) tratado como unidade de indexação |
| **Embedding** | Vetor numérico que representa o significado de um texto |
| **Vector store** | Banco especializado em busca por similaridade de vetores |
| **Top-k** | Os *k* chunks mais similares recuperados para uma query |
| **Recall@k** | Fração das perguntas em que ao menos um chunk relevante aparece no top-k |
| **Golden set** | Conjunto curado de perguntas com resposta/fonte esperada, usado para avaliação |
| **LLM** | Large Language Model |

### 1.4 Referências
- *AI Engineering* (Chip Huyen), caps. 1–4.
- Paper *RAG* (Lewis et al., 2020).
- Documentação LangChain, ChromaDB, Ollama, Langfuse.
- Roadmap Semestre a Semestre (Notion — Central da Minha Vida).

---

## 2. Visão Geral e Contexto

### 2.1 Descrição do sistema
Aplicação Python de linha única de responsabilidade: **transformar uma coleção de documentos pessoais em um assistente que responde com base neles**. A interação principal é um chat; a interação secundária é a ingestão (indexar novos documentos) e a avaliação (rodar o golden set).

### 2.2 Atores e stakeholders

| Ator | Papel |
|------|-------|
| **Usuário (Matheus)** | Ingere documentos, faz perguntas, lê métricas |
| **Provedores de LLM/embedding** | Google Gemini (free tier), Groq (free, fallback), Ollama (local). OpenAI/Anthropic = adapters opcionais |
| **Vector store** | ChromaDB (local) |
| **Observabilidade** | Langfuse (traces) — **opcional**; fallback para traces JSON locais |

### 2.3 Restrições
- **Hardware local:** GPU RTX 5060 8GB → modelos locais precisam caber (Llama 3.2 3B, nomic-embed-text).
- **Custo:** projeto roda a **$0** — nuvem via free tiers (Gemini, Groq). A restrição real não é dinheiro, é **quota** (RPD/RPM/TPM do free tier) → precisa de throttle, backoff e cache.
- **Tempo:** projeto de 1 semestre, feito em paralelo à faculdade e ao trabalho → escopo apertado.
- **Privacidade:** documentos podem ser pessoais → modo 100% local obrigatório.

### 2.4 Premissas
- Volume de documentos na casa de dezenas a poucas centenas de arquivos (não milhões).
- Uso single-user, local (localhost).
- Idiomas dos documentos: PT-BR e EN.

---

## 3. Requisitos

### 3.1 Requisitos funcionais (RF)

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-01 | Ingerir documentos em PDF, Markdown, TXT e DOCX | Alta |
| RF-02 | Fragmentar (chunk) documentos com sobreposição configurável | Alta |
| RF-03 | Gerar embeddings de cada chunk e persistir no vector store | Alta |
| RF-04 | Recuperar top-k chunks por similaridade para uma query | Alta |
| RF-05 | Gerar resposta ancorada nos chunks recuperados | Alta |
| RF-06 | Citar a fonte (arquivo + trecho) de cada resposta | Alta |
| RF-07 | Suportar modo nuvem (Gemini free; Groq de fallback) e modo local (Ollama) via config | Alta |
| RF-08 | Interface de chat com histórico da sessão | Alta |
| RF-09 | Streaming da resposta (token a token) | Média |
| RF-10 | Reindexar / atualizar a base sem reprocessar o que não mudou (hash) | Média |
| RF-11 | Rodar avaliação sobre um golden set de 30 perguntas | Alta |
| RF-12 | Exibir/registrar métricas: latência, custo, Recall@5 | Alta |

### 3.2 Requisitos não-funcionais (RNF)

| ID | Requisito | Meta V1 |
|----|-----------|---------|
| RNF-01 | **Latência** de query (retrieval + geração) | < 5 s (nuvem), medir local |
| RNF-02 | **Custo** por query | Real = **$0** (free tier); reportar custo *calculado* (USD equivalente no tier pago) + tokens/query |
| RNF-03 | **Qualidade** de recuperação | Recall@5 ≥ 0,80 no golden set |
| RNF-04 | **Privacidade** | Modo local não faz nenhuma chamada externa |
| RNF-05 | **Manutenibilidade** | Componentes desacoplados, provider-agnostic |
| RNF-06 | **Observabilidade** | Todo query rastreável (trace ponta a ponta); Langfuse opcional |
| RNF-07 | **Reprodutibilidade** | Setup em 1 comando; deps pinadas; eval determinístico (temperature=0, modelo pinado) |
| RNF-08 | **Segurança** | Nenhum segredo em código; `.env` fora do Git |
| RNF-09 | **Resiliência de quota** | Free tier: backoff/retry em 429, throttle de RPM e cache de embedding/resposta para não estourar RPD |

---

## 4. Arquitetura

### 4.1 Estilo arquitetural
**Arquitetura em camadas + portas/adaptadores (ports & adapters, "hexagonal light")**. O núcleo (chunking, orquestração RAG, avaliação) não conhece *qual* provedor concreto de embedding/LLM/vector store está por trás — ele fala com **interfaces**. Adaptadores concretos (Gemini, Groq, Ollama, Chroma) implementam essas interfaces. Isso é o que torna a migração para o V2 uma troca de plugue.

### 4.2 Camadas

```
┌───────────────────────────────────────────────┐
│  Interface (Streamlit UI + CLI)                │  ← entrada do usuário
├───────────────────────────────────────────────┤
│  Aplicação / Orquestração (RAG pipeline)       │  ← casos de uso
├───────────────────────────────────────────────┤
│  Domínio (chunking, prompt, tipos, contratos)  │  ← regras, interfaces (Ports)
├───────────────────────────────────────────────┤
│  Adaptadores (embeddings, LLM, vector store)   │  ← implementações (Adapters)
├───────────────────────────────────────────────┤
│  Infra (config, logging, tracing, storage)     │  ← detalhes técnicos
└───────────────────────────────────────────────┘
```

### 4.3 Componentes principais

| Componente | Responsabilidade | Depende de (interface) |
|------------|------------------|------------------------|
| **Loader** | Ler arquivos e extrair texto + metadados | — |
| **Chunker** | Fragmentar texto em chunks com overlap | — |
| **EmbeddingProvider** (Port) | Transformar texto em vetor | Adaptador Gemini/Ollama |
| **VectorStore** (Port) | Persistir e buscar vetores | Adaptador Chroma/pgvector |
| **Retriever** | Buscar top-k chunks para uma query | VectorStore + EmbeddingProvider |
| **LLMProvider** (Port) | Gerar texto a partir de um prompt | Adaptador Gemini/Groq/Ollama |
| **Cache** | Memorizar embeddings (por hash do chunk) e respostas do eval → não gastar quota do free tier em reruns | — (disk/SQLite local) |
| **RateLimiter/Retry** | Throttle de RPM + backoff em 429 nos adaptadores de nuvem | envolve os adapters Gemini/Groq |
| **RAGPipeline** | Orquestrar retrieve → montar prompt → gerar → citar | Retriever + LLMProvider |
| **Evaluator** | Rodar golden set e calcular métricas | RAGPipeline + Cache |
| **Tracer** | Registrar traces/latência/custo | Langfuse (opcional) ou JSON local |
| **UI (Streamlit)** | Chat + ingestão + painel de métricas | RAGPipeline + Evaluator |

> Diagramas completos em [`DIAGRAMS.md`](DIAGRAMS.md).

---

## 5. Design de Dados

### 5.1 Fluxo do dado
`arquivo → texto extraído → chunks → (chunk + metadados + vetor) no vector store`

### 5.2 Estratégia de chunking
- **Splitter:** `RecursiveCharacterTextSplitter` (respeita parágrafos/sentenças antes de cortar no meio).
- **Tamanho:** ~800 tokens por chunk.
- **Overlap:** ~120 tokens (preserva contexto na fronteira).
- **Configurável** via `.env` (permite experimentar no eval).

### 5.3 Modelo do "documento indexado" (registro no vector store)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string (uuid) | Identificador único do chunk |
| `embedding` | float[] | Vetor do chunk |
| `text` | string | Conteúdo textual do chunk |
| `source` | string | Caminho/nome do arquivo de origem |
| `chunk_index` | int | Posição do chunk dentro do documento |
| `doc_hash` | string | Hash do arquivo (detecta mudança → reindex incremental) |
| `page` | int? | Página (quando PDF) |
| `created_at` | datetime | Timestamp da indexação |

### 5.4 Modelo conceitual (relacional, para leitura/ER)
Mesmo usando ChromaDB (não-relacional), o modelo mental é:

```
Document (1) ──< (N) Chunk
Chunk (1) ──── (1) Embedding
```

> Diagrama ER em [`DIAGRAMS.md`](DIAGRAMS.md).

### 5.5 Reindexação incremental
Antes de reprocessar um arquivo, compara-se `doc_hash`. Se inalterado, pula. Se mudou, remove chunks antigos daquele `source` e reindexa. Evita reembeddar a base inteira toda vez.

### 5.6 ⚠️ O modelo de embedding faz parte da identidade do índice
Vetores de modelos diferentes vivem em **espaços vetoriais incompatíveis** e têm dimensões diferentes (Gemini `text-embedding-004` = 768, `nomic-embed-text` via Ollama = 768, OpenAI `text-embedding-3-small` = 1536). **Não dá para misturar** embeddings de modelos diferentes na mesma coleção, nem consultar com um embedder diferente do que indexou — o resultado é lixo silencioso (sem erro).

Decisões de projeto:
- O nome da coleção Chroma inclui o id do modelo de embedding (ex.: `chunks__text-embedding-004`). Trocar de embedder cria/usa **outra** coleção.
- Persistir o `model` do embedding junto do chunk (ver §5.3 e ER em doc 03).
- No boot do Retriever, **validar** que o embedder configurado bate com o da coleção; se não bater, erro claro pedindo reindexação.
- Trocar `EMBEDDING_PROVIDER` ⇒ reindexar. Isso é esperado e documentado — não é bug.

### 5.7 Cache (economia de quota)
- **Cache de embedding:** chave = `hash(text) + model`. Reingestão e reruns de eval não re-embeddam o mesmo conteúdo. Persistente (SQLite/disco em `data/cache/`).
- **Cache de resposta (só no eval):** chave = `hash(prompt) + model + temperature`. Permite reprocessar o golden set sem re-gastar RPD do free tier. Desligado no chat interativo.

---

## 6. Design de Componentes (detalhado)

### 6.1 Loader (`ingestion/loaders.py`)
- Entrada: caminho de arquivo.
- Saída: `RawDocument(text, metadata)`.
- Um loader por formato (PDF via `pypdf`, DOCX via `python-docx`, MD/TXT nativo).
- Registra `source`, `page` (PDF) e `doc_hash`.

### 6.2 Chunker (`ingestion/chunker.py`)
- Entrada: `RawDocument`. Saída: `list[Chunk]`.
- Parâmetros de tamanho/overlap injetados via config.

### 6.3 EmbeddingProvider (Port + adaptadores)
```python
class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
```
- Adaptadores: `GeminiEmbeddings` (`text-embedding-004`, free tier), `OllamaEmbeddings` (`nomic-embed-text`, local). `OpenAIEmbeddings` opcional.
- Envolvido pelo **Cache de embedding** (§5.7) e pelo **RateLimiter/Retry** (nuvem).

### 6.4 VectorStore (Port + adaptadores)
```python
class VectorStore(Protocol):
    def upsert(self, chunks: list[EmbeddedChunk]) -> None: ...
    def query(self, vector: list[float], k: int) -> list[RetrievedChunk]: ...
    def delete_by_source(self, source: str) -> None: ...
```
- Adaptador V1: `ChromaVectorStore`. Ponto de extensão V2: `PgVectorStore`.

### 6.5 Retriever (`retrieval/retriever.py`)
- Recebe a query em texto → `embed_query` → `vector_store.query(k)` → devolve chunks + score.

### 6.6 LLMProvider (Port + adaptadores)
```python
class LLMProvider(Protocol):
    def generate(self, prompt: str, *, stream: bool = False) -> LLMResponse: ...
```
- Adaptadores: `GeminiLLM` (`gemini-2.5-flash-lite`, free tier), `GroqLLM` (Llama via API OpenAI-compat, free — fallback), `OllamaLLM` (Llama 3.2, local). `AnthropicLLM`/`OpenAILLM` opcionais.
- Adaptadores de nuvem envolvidos por **RateLimiter/Retry**: throttle de RPM e backoff exponencial em `429`. Fallback opcional Gemini→Groq quando a quota diária (RPD) estoura.
- `LLMResponse` carrega `text`, `input_tokens`, `output_tokens`, `model` (para custo *calculado* e tokens/query).

### 6.7 RAGPipeline (`rag/pipeline.py`) — o coração
Passos:
1. `retriever.retrieve(query, k)`.
2. Montar prompt com template (contexto numerado + instrução de citar fontes + guarda contra alucinação).
3. `llm.generate(prompt, stream=…)`.
4. Anexar as **citações** (source + chunk_index) à resposta.
5. Emitir trace (latência de cada etapa + custo estimado).

### 6.8 Prompt template (`rag/prompts.py`)
Diretrizes embutidas no template:
- "Responda **apenas** com base no contexto abaixo."
- "Se a resposta não estiver no contexto, diga que não sabe."
- "Cite as fontes pelo número do trecho."
- Contexto injetado como blocos numerados `[1] … [2] …`.

### 6.9 Evaluator (`evaluation/evaluator.py`)
- Carrega `golden_set.json` (30 perguntas + fonte esperada).
- Para cada pergunta: roda retrieval, checa se a fonte esperada está no top-5 → **Recall@5**.
- Mede latência, tokens/query e custo *calculado*; agrega médias.
- **Determinístico:** `temperature=0` e modelo pinado (aliases do Gemini mudam) para o eval ser reproduzível.
- Usa o **Cache** (§5.7) para reruns não gastarem quota; loga quantas queries consumiram RPD.
- Exporta `report.md` + `report.json`.

### 6.10 UI (`app/streamlit_app.py`)
- Aba **Chat**: input + histórico + respostas com fontes expansíveis.
- Aba **Ingestão**: upload/seleção de pasta + botão "Indexar".
- Aba **Métricas**: rodar eval + gráficos (latência, custo, Recall@5).
- Seletor de **modo** (nuvem/local) no sidebar.

---

## 7. Design de Interfaces

### 7.1 Interface interna (contratos)
Já descritos como `Protocol`s em §6 (Ports). São o contrato estável; adaptadores são intercambiáveis.

### 7.2 Interface de usuário
- **CLI** (`typer`): `rag ingest ./docs`, `rag ask "pergunta"`, `rag eval`.
- **Web** (Streamlit): descrito em §6.10.

### 7.3 Interfaces externas
| Serviço | Protocolo | Autenticação | Custo |
|---------|-----------|--------------|-------|
| Google Gemini (AI Studio) | HTTPS/REST | API key (`.env`) | free tier (quota RPD/RPM) |
| Groq | HTTPS/REST (OpenAI-compat) | API key (`.env`) | free tier (fallback) |
| Ollama | HTTP local | nenhuma | $0, local |
| Langfuse (opcional) | HTTPS/REST | keys (`.env`) | free tier; ou trace JSON local |
| ChromaDB | in-process / local | nenhuma | $0, local |
| OpenAI/Anthropic (opcional) | HTTPS/REST | API key (`.env`) | pago |

---

## 8. Fluxos Principais

### 8.1 Fluxo de Ingestão
`selecionar arquivos → Loader → Chunker → EmbeddingProvider → VectorStore.upsert`
(com checagem de `doc_hash` para incremental).

### 8.2 Fluxo de Query (RAG)
`pergunta → embed_query → VectorStore.query(k) → montar prompt → LLM.generate → resposta + citações → trace`

> Diagramas de sequência dos dois fluxos em [`DIAGRAMS.md`](DIAGRAMS.md).

---

## 9. Decisões de Arquitetura (ADRs)

> Formato curto: **Contexto → Decisão → Consequência**.

### ADR-01 — LangChain como orquestrador
- **Contexto:** preciso de RAG rápido e de sinalizar fluência no framework mais pedido em vagas.
- **Decisão:** usar LangChain para loaders, splitters e integração de providers.
- **Consequência:** produtividade alta e legibilidade de mercado; risco de "abstração demais" mitigado mantendo a lógica RAG no meu próprio `RAGPipeline`, não escondida em chains mágicas. Alternativa considerada: LlamaIndex (mais RAG-first) — fica como estudo comparativo.

### ADR-02 — ChromaDB no V1, pgvector no V2
- **Contexto:** quero começar sem subir infraestrutura.
- **Decisão:** ChromaDB local (zero-config) atrás da interface `VectorStore`.
- **Consequência:** setup trivial; migração para pgvector no V2 é só um novo adaptador. Sem lock-in.

### ADR-03 — Provider-agnostic (Ports & Adapters)
- **Contexto:** preciso de modo nuvem (qualidade) e local (privacidade/custo zero).
- **Decisão:** interfaces `EmbeddingProvider`/`LLMProvider`; adaptadores concretos por config.
- **Consequência:** trocar Gemini ↔ Groq ↔ Llama (Ollama) é mudar `.env`. Custo de um pouco mais de código inicial. ⚠️ trocar o **embedder** exige reindexar (ver §5.6).

### ADR-04 — Métricas como cidadão de primeira classe
- **Contexto:** o diferencial do projeto é *medir*, não só funcionar.
- **Decisão:** Evaluator + golden set + tracing desde o início. Como roda no free tier, o custo real é $0 → a métrica de custo é **calculada** (USD equivalente no tier pago) e complementada por **tokens/query** e **consumo de quota (RPD)**.
- **Consequência:** README ganha números reais + a narrativa "RAG de produção a $0, medido"; base pronta para o eval avançado do V2 (Ragas).

### ADR-07 — Free-tier-first (Gemini + Ollama, Groq de fallback)
- **Contexto:** projeto de estudante, sem orçamento de API; precisa rodar indefinidamente sem gastar.
- **Decisão:** nuvem = **Google Gemini free tier**; local = **Ollama**; **Groq** free como fallback quando a quota diária do Gemini estoura. OpenAI/Anthropic ficam como adapters **opcionais** (mesma interface), fora do quickstart.
- **Consequência:** custo $0 e sem cartão de crédito. A restrição vira **quota** (RPD/RPM/TPM) → exige backoff/retry, throttle e cache (RNF-09, §5.7). Aliases de modelo do Gemini mudam → pinar versão no eval.

### ADR-08 — Langfuse opcional
- **Contexto:** observabilidade é importante, mas exigir uma 3ª conta/keys externas aumenta o atrito de um V1 gratuito e simples.
- **Decisão:** `Tracer` atrás de interface; se não houver keys Langfuse, cai para **trace JSON local** em `data/traces/`.
- **Consequência:** roda 100% offline sem Langfuse; quem quiser dashboard usa o free tier do Langfuse só ligando as keys.

### ADR-05 — Streamlit como frontend
- **Contexto:** foco do semestre é o RAG, não o front.
- **Decisão:** Streamlit (UI em Python puro).
- **Consequência:** velocidade máxima; se quiser "profissionalizar", Next.js entra no V2.

### ADR-06 — `uv` para gerência de dependências
- **Contexto:** quero reprodutibilidade e velocidade.
- **Decisão:** `uv` + `pyproject.toml` com versões pinadas.
- **Consequência:** setup em 1 comando; alternativa Poetry se preferir ecossistema mais maduro.

---

## 10. Qualidade, Métricas e Observabilidade

### 10.1 Métricas do produto
- **Latência:** medir separadamente retrieval vs geração (identificar gargalo).
- **Tokens/query:** `input_tokens` + `output_tokens` (métrica operacional real no free tier).
- **Custo/query (calculado):** `input_tokens * preço_in + output_tokens * preço_out` usando a tabela de preços do tier pago — mostra quanto *custaria*; o custo real é **$0**.
- **Consumo de quota:** quantas queries por dia dentro do RPD do free tier (quando o eval bate o limite, é sinal para usar cache/fallback Groq).
- **Recall@5:** sobre o golden set de 30 perguntas.

### 10.2 Observabilidade
- **Langfuse (opcional)** captura cada trace: query, chunks recuperados, prompt final, resposta, tempos e tokens. Sem keys → **trace JSON local** em `data/traces/` (mesma interface `Tracer`).
- Logging estruturado (`structlog` ou `logging` + JSON) para depuração local.

### 10.3 Métricas de engenharia
- Cobertura de testes das camadas de domínio e pipeline.
- CI verde (lint + testes) obrigatório para merge.

---

## 11. Segurança e Privacidade

- **Segredos:** somente em `.env` (git-ignored); `.env.example` versionado sem valores.
- **Modo local:** garante que nenhuma chamada externa ocorra (útil para documentos sensíveis).
- **Dados:** o vector store e os documentos ficam locais; `data/` é git-ignored.
- **Prompt injection (consciência V1):** o template instrui o modelo a usar só o contexto; tratamento robusto de conteúdo malicioso em documentos fica sinalizado para o track de AI Safety (6º sem).

---

## 12. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Escopo inflar (querer V2 no V1) | Projeto não termina | Escopo congelado (doc 00 §Escopo); extras viram issues do V2 |
| Modelo local não caber na GPU 8GB | Modo local quebra | Usar 3B quantizado / nomic-embed; testar cedo (Fase 0) |
| **Quota do free tier estourar (RPD/RPM)** | Chat/eval param no meio | Backoff/retry em 429 + throttle RPM + **cache** (§5.7); **fallback Gemini→Groq**; modo local (Ollama) sempre disponível |
| **Trocar embedder invalida o índice** (dims/espaço incompatíveis) | Retrieval retorna lixo silencioso | Coleção por modelo de embedding + validação no boot + reindex ao trocar (§5.6) |
| **Aliases de modelo do Gemini mudam** | Eval não reproduzível | Pinar a versão do modelo; `temperature=0` no eval |
| Chunking ruim → Recall baixo | Meta RNF-03 não atingida | Tornar chunking configurável e iterar via eval |
| Over-engineering das abstrações | Atraso | Ports só onde há 2+ implementações reais (embedding, LLM, store) |

---

## 13. Estratégia de Testes

| Nível | O que testa | Ferramenta |
|-------|-------------|------------|
| **Unitário** | Chunker (tamanho/overlap), parsing de metadados, cálculo de custo | pytest |
| **Contrato** | Cada adaptador cumpre seu Protocol (fakes/mocks) | pytest |
| **Integração** | Ingestão → retrieval ponta a ponta com store em memória | pytest |
| **Avaliação** | Recall@5 no golden set (roda no CI opcionalmente) | Evaluator |
| **Smoke manual** | Chat responde e cita fonte | checklist |

**Estratégia:** priorizar testes na **camada de domínio e no RAGPipeline** (onde mora o valor). Adaptadores externos usam fakes para não gastar API em CI.

---

## 14. Rastreabilidade (requisito → componente)

| Requisito | Atendido por |
|-----------|--------------|
| RF-01..03 | Loader, Chunker, EmbeddingProvider, VectorStore |
| RF-04..06 | Retriever, RAGPipeline, prompt template |
| RF-07 | Ports + adaptadores + config |
| RF-08..09 | UI Streamlit, streaming no LLMProvider |
| RF-10 | `doc_hash` + reindex incremental |
| RF-11..12 | Evaluator + Tracer |

---

*Fim do SDD. Próximos documentos: README (02), Diagramas (03), Estrutura (04), Plano de Fases (05).*
