# 📊 Diagramas — Personal RAG Assistant V1

> Todos os diagramas em **Mermaid**. Renderizam direto no GitHub, Notion e VS Code
> (extensão *Markdown Preview Mermaid*). Cada diagrama tem uma frase explicando o que mostra.

---

## 1. Diagrama de Contexto (C4 — Nível 1)
*Quem usa o sistema e com quais serviços externos ele fala.*

```mermaid
flowchart TB
    user([👤 Usuário<br/>Matheus])

    subgraph sys[Personal RAG Assistant]
        app[Aplicação RAG]
    end

    ollama[(Ollama · Docker<br/>primário · LLM + embeddings · local $0)]
    gemini[(Google Gemini<br/>free tier · fallback de geração · opcional)]
    langfuse[(Langfuse<br/>observabilidade · opcional)]

    user -->|faz perguntas / ingere docs| app
    app -->|embeddings + geração local| ollama
    app -.->|fallback de geração opcional| gemini
    app -.->|traces opcionais| langfuse
```

---

## 2. Diagrama de Componentes (C4 — Nível 2/3)
*As camadas internas e como o núcleo depende de interfaces, não de implementações.*

```mermaid
flowchart TB
    subgraph UI[Camada de Interface]
        streamlit[Streamlit UI]
        cli[CLI - typer]
    end

    subgraph APP[Camada de Aplicação]
        pipeline[RAG Pipeline]
        evaluator[Evaluator]
    end

    subgraph DOMAIN[Domínio / Ports]
        iemb{{EmbeddingProvider}}
        illm{{LLMProvider}}
        ivs{{VectorStore}}
        chunker[Chunker]
        prompts[Prompt Templates]
    end

    subgraph COMMON[Common / resiliência]
        cache[Cache<br/>embedding + resposta]
        rl[RateLimiter + Retry<br/>throttle RPM · backoff 429]
    end

    subgraph ADAPTERS[Adaptadores]
        ollama_emb[Ollama Embeddings - primário]
        gemini_emb[Gemini Embeddings - opcional]
        ollama_llm[Ollama LLM - primário]
        gemini_llm[Gemini LLM - fallback]
        chroma[Chroma Store<br/>coleção por modelo de embedding]
    end

    subgraph INFRA[Infra]
        config[Config / Settings]
        tracer[Tracer<br/>Langfuse OU JSON local]
        logging[Logging]
    end

    streamlit --> pipeline
    cli --> pipeline
    streamlit --> evaluator
    pipeline --> chunker
    pipeline --> prompts
    pipeline --> iemb
    pipeline --> illm
    pipeline --> ivs
    evaluator --> pipeline

    iemb -.implementado por.-> ollama_emb
    iemb -.implementado por.-> gemini_emb
    illm -.implementado por.-> ollama_llm
    illm -.implementado por.-> gemini_llm
    ivs -.implementado por.-> chroma

    ollama_emb --> cache
    gemini_emb --> cache
    gemini_emb --> rl
    gemini_llm --> rl
    ollama_llm -. fallback .-> gemini_llm

    pipeline -.trace opcional.-> tracer
    config --> ADAPTERS
```

---

## 3. Sequência — Fluxo de Ingestão
*O que acontece quando você indexa uma pasta de documentos.*

```mermaid
sequenceDiagram
    actor U as Usuário
    participant CLI as CLI / UI
    participant L as Loader
    participant CH as Chunker
    participant C as Cache
    participant E as EmbeddingProvider
    participant VS as VectorStore

    U->>CLI: rag ingest ./data/documents
    loop para cada arquivo
        CLI->>L: carregar(arquivo)
        L-->>CLI: RawDocument(texto, metadados, doc_hash)
        alt doc_hash inalterado
            CLI-->>CLI: pular (já indexado)
        else novo ou modificado
            CLI->>VS: delete_by_source(source)
            CLI->>CH: fragmentar(RawDocument)
            CH-->>CLI: [chunks]
            loop para cada chunk
                CLI->>C: get(hash(text)+model)
                alt cache hit
                    C-->>CLI: vetor (sem gastar quota)
                else cache miss
                    CLI->>E: embed_documents([chunk])
                    E-->>CLI: vetor
                    CLI->>C: put(hash+model, vetor)
                end
            end
            CLI->>VS: upsert(chunks + vetores + metadados) [coleção do model]
        end
    end
    CLI-->>U: N documentos indexados (M chunks)
```

---

## 4. Sequência — Fluxo de Query (RAG)
*O caminho de uma pergunta até a resposta com fontes.*

```mermaid
sequenceDiagram
    actor U as Usuário
    participant UI as Streamlit UI
    participant P as RAG Pipeline
    participant E as EmbeddingProvider
    participant VS as VectorStore
    participant PR as Prompt Builder
    participant O as Ollama (LLM primário)
    participant RL as RateLimiter/Retry
    participant G as Gemini (fallback · opcional)
    participant T as Tracer (opcional)

    U->>UI: "Qual o prazo do contrato X?"
    UI->>P: ask(query)
    P->>T: iniciar trace
    P->>E: embed_query(query)
    E-->>P: vetor da query
    P->>VS: query(vetor, k=5)
    VS-->>P: top-5 chunks + scores
    alt nenhum chunk relevante
        P-->>UI: "não encontrei nos documentos"
    else há contexto
        P->>PR: montar prompt (contexto numerado + regras)
        PR-->>P: prompt final
        P->>O: generate(prompt, stream=true)
        alt Ollama responde (primário · $0 · sem quota)
            O-->>UI: tokens (streaming)
            O-->>P: resposta + tokens usados
        else Ollama indisponível E modo hybrid + GEMINI_API_KEY
            P->>RL: fallback p/ Gemini (throttle RPM)
            RL->>G: chamada
            alt 429 / quota diária (RPD) do Gemini
                RL->>RL: backoff + retry
            end
            G-->>RL: resposta + tokens
            RL-->>UI: tokens (streaming)
            RL-->>P: resposta + tokens usados
        end
        P->>P: anexar citações (source, chunk_index)
        P-->>UI: resposta + fontes
    end
    P->>T: registrar latência + tokens + custo calculado
    UI-->>U: resposta com [1] fonte.pdf, p.3
```

---

## 5. Diagrama de Fluxo de Dados (DFD)
*Como o dado se transforma da entrada bruta até o vetor consultável.*

```mermaid
flowchart LR
    A[/Arquivo bruto<br/>PDF/MD/TXT/DOCX/] --> B[Extração de texto<br/>+ metadados]
    B --> C[Chunking<br/>800 tokens / overlap 120]
    C --> D[Embedding<br/>texto → vetor]
    D --> E[(Vector Store<br/>chunk + vetor + metadados)]
    F[/Pergunta/] --> G[Embedding da query]
    G --> H[Busca top-k]
    E --> H
    H --> I[Montagem do prompt]
    I --> J[LLM]
    J --> K[/Resposta + citações/]
```

---

## 6. Diagrama ER (modelo conceitual dos dados)
*Modelo mental relacional, mesmo o V1 usando ChromaDB.*

```mermaid
erDiagram
    DOCUMENT ||--o{ CHUNK : "é fragmentado em"
    CHUNK ||--|| EMBEDDING : "possui"

    DOCUMENT {
        string source PK "caminho/nome do arquivo"
        string doc_hash "hash p/ reindex incremental"
        datetime indexed_at
        string file_type
    }
    CHUNK {
        string id PK
        string source FK
        int chunk_index
        int page "quando PDF"
        string text
    }
    EMBEDDING {
        string chunk_id PK,FK
        float_array vector
        string model "ex: text-embedding-004 (parte da identidade do índice)"
    }
```

---

## 7. Diagrama de Classes (núcleo)
*As abstrações (Ports) e suas implementações concretas (Adapters).*

```mermaid
classDiagram
    class EmbeddingProvider {
        <<interface>>
        +embed_documents(texts) list~vector~
        +embed_query(text) vector
    }
    class LLMProvider {
        <<interface>>
        +generate(prompt, stream) LLMResponse
    }
    class VectorStore {
        <<interface>>
        +upsert(chunks) void
        +query(vector, k) list~RetrievedChunk~
        +delete_by_source(source) void
    }

    class Tracer {
        <<interface>>
        +start(name) Span
        +record(latency, tokens, cost)
    }

    class GeminiEmbeddings
    class OllamaEmbeddings
    class OllamaLLM
    class GeminiLLM
    class ChromaVectorStore
    class LangfuseTracer
    class JsonTracer

    class Cache {
        +get(key) Optional~T~
        +put(key, value) void
    }
    class RateLimiter {
        -rpm_budget
        +call(fn) T
        +on_429_backoff()
    }

    class RAGPipeline {
        -retriever
        -llm
        -tracer
        +ask(query) Answer
    }
    class Retriever {
        -embeddings
        -store
        +retrieve(query, k) list~RetrievedChunk~
    }
    class Evaluator {
        -pipeline
        -cache
        +run(golden_set) Report
    }

    EmbeddingProvider <|.. GeminiEmbeddings
    EmbeddingProvider <|.. OllamaEmbeddings
    LLMProvider <|.. OllamaLLM
    LLMProvider <|.. GeminiLLM
    VectorStore <|.. ChromaVectorStore
    Tracer <|.. LangfuseTracer
    Tracer <|.. JsonTracer

    RAGPipeline --> Retriever
    RAGPipeline --> LLMProvider
    RAGPipeline --> Tracer
    Retriever --> EmbeddingProvider
    Retriever --> VectorStore
    Evaluator --> RAGPipeline
    Evaluator --> Cache
    OllamaEmbeddings --> Cache
    GeminiEmbeddings --> Cache
    GeminiLLM --> RateLimiter
    OllamaLLM ..> GeminiLLM : fallback
```

---

## 8. Diagrama de Estados — ciclo de vida de uma query
*Os estados por que uma pergunta passa, incluindo o caminho de "não sei".*

```mermaid
stateDiagram-v2
    [*] --> Recebida
    Recebida --> Embedada: embed_query
    Embedada --> Recuperando: buscar top-k
    Recuperando --> SemContexto: nenhum chunk relevante
    Recuperando --> ComContexto: chunks encontrados
    SemContexto --> Respondida: "não encontrei nos documentos"
    ComContexto --> Gerando: montar prompt + Ollama (primário)
    Gerando --> Respondida: resposta + citações
    Gerando --> Fallback: Ollama indisponível (hybrid + key)
    Fallback --> Backoff: 429 / quota (RPD) do Gemini
    Backoff --> Fallback: retry ok
    Fallback --> Respondida: resposta via Gemini
    Respondida --> Rastreada: registrar latência + tokens + custo calc.
    Rastreada --> [*]
```

---

## 9. Diagrama de Fases (Gantt do 1º semestre)
*Planejamento temporal — detalhe em `PROJECT_PLAN.md`.*

```mermaid
gantt
    title Personal RAG V1 — Execução por Fases
    dateFormat  YYYY-MM-DD
    axisFormat  %b

    section Fundação
    Fase 0 - Setup e stack        :f0, 2026-08-01, 14d
    section Núcleo
    Fase 1 - Ingestão             :f1, after f0, 14d
    Fase 2 - Retrieval            :f2, after f1, 10d
    Fase 3 - Geração + chat       :f3, after f2, 14d
    section Produto
    Fase 4 - Frontend Streamlit   :f4, after f3, 10d
    Fase 5 - Avaliação + métricas :f5, after f4, 14d
    section Acabamento
    Fase 6 - Observab. + polish   :f6, after f5, 10d
    Fase 7 - Docs + publicação    :f7, after f6, 10d
```

---

## 10. Mapa mental do escopo (V1 vs V2)
*O que entra agora e o que fica pontuado como extensão.*

```mermaid
mindmap
  root((Personal RAG))
    V1 (escopo agora)
      Ingestão multi-formato
      Busca semântica top-k
      Geração com citação
      Modo local e hybrid - fallback Gemini
      Resiliência de quota - cache, backoff no fallback
      Métricas essenciais
      Streamlit + CLI
    V2 (extensões)
      Hybrid search BM25+dense
      Reranker
      Eval suite Ragas/TruLens
      Dashboard trade-offs
      pgvector
      Next.js
```

---

## 11. Seleção de Provider & Fallback de Quota
*Como o modo e a quota do free tier decidem qual LLM responde — e o que garante custo $0.*

```mermaid
flowchart TD
    start([ask query]) --> mode{RAG_MODE?}
    mode -->|local| ollama[Ollama<br/>llama3.2:3b · $0 · sem quota]
    mode -->|hybrid| tryoll{Ollama<br/>disponível?}
    tryoll -->|sim| ollama
    tryoll -->|não| keycheck{GEMINI_API_KEY?}
    keycheck -->|sim| gem{Gemini free<br/>dentro da quota?}
    gem -->|sim| gemok[Gemini responde<br/>fallback · throttle RPM · $0]
    gem -->|429 transitório| backoff[backoff + retry]
    backoff --> gem
    gem -->|RPD esgotada| deg[degrada / avisa<br/>quota do fallback esgotada]
    keycheck -->|não| err[erro: Ollama off<br/>e sem fallback]
    gemok --> done([resposta + tokens])
    ollama --> done
    deg --> done
    err --> done
```

> Regra: nenhum caminho leva a provider pago. Custo real permanece **$0**; o primário Ollama roda offline, $0, sem quota — o pior caso é o fallback Gemini opcional esbarrar na quota diária.

---

*Dica: cole qualquer bloco em [mermaid.live](https://mermaid.live) para editar visualmente.*
