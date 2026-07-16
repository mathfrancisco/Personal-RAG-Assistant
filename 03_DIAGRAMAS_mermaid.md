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

    gemini[(Google Gemini<br/>free tier · embeddings/LLM)]
    groq[(Groq<br/>free · LLM fallback)]
    ollama[(Ollama<br/>modelos locais)]
    langfuse[(Langfuse<br/>observabilidade · opcional)]

    user -->|faz perguntas / ingere docs| app
    app -->|embeddings + geração| gemini
    app -->|geração fallback| groq
    app -->|embeddings + geração local| ollama
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

    subgraph ADAPTERS[Adaptadores]
        gemini_emb[Gemini Embeddings]
        ollama_emb[Ollama Embeddings]
        gemini_llm[Gemini LLM]
        groq_llm[Groq LLM - fallback]
        ollama_llm[Ollama LLM]
        chroma[Chroma Store]
    end

    subgraph INFRA[Infra]
        config[Config / Settings]
        tracer[Tracer - Langfuse]
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

    iemb -.implementado por.-> gemini_emb
    iemb -.implementado por.-> ollama_emb
    illm -.implementado por.-> gemini_llm
    illm -.implementado por.-> groq_llm
    illm -.implementado por.-> ollama_llm
    ivs -.implementado por.-> chroma

    pipeline --> tracer
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
            CLI->>E: embed_documents([chunks])
            E-->>CLI: [vetores]
            CLI->>VS: upsert(chunks + vetores + metadados)
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
    participant LLM as LLMProvider
    participant T as Tracer

    U->>UI: "Qual o prazo do contrato X?"
    UI->>P: ask(query)
    P->>T: iniciar trace
    P->>E: embed_query(query)
    E-->>P: vetor da query
    P->>VS: query(vetor, k=5)
    VS-->>P: top-5 chunks + scores
    P->>PR: montar prompt (contexto numerado + regras)
    PR-->>P: prompt final
    P->>LLM: generate(prompt, stream=true)
    LLM-->>UI: tokens (streaming)
    LLM-->>P: resposta + tokens usados
    P->>P: anexar citações (source, chunk_index)
    P->>T: registrar latência + custo
    P-->>UI: resposta + fontes
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

    class GeminiEmbeddings
    class OllamaEmbeddings
    class GeminiLLM
    class GroqLLM
    class OllamaLLM
    class ChromaVectorStore

    class RAGPipeline {
        -retriever
        -llm
        +ask(query) Answer
    }
    class Retriever {
        -embeddings
        -store
        +retrieve(query, k) list~RetrievedChunk~
    }
    class Evaluator {
        -pipeline
        +run(golden_set) Report
    }

    EmbeddingProvider <|.. GeminiEmbeddings
    EmbeddingProvider <|.. OllamaEmbeddings
    LLMProvider <|.. GeminiLLM
    LLMProvider <|.. GroqLLM
    LLMProvider <|.. OllamaLLM
    VectorStore <|.. ChromaVectorStore

    RAGPipeline --> Retriever
    RAGPipeline --> LLMProvider
    Retriever --> EmbeddingProvider
    Retriever --> VectorStore
    Evaluator --> RAGPipeline
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
    ComContexto --> Gerando: montar prompt + LLM
    Gerando --> Respondida: resposta + citações
    Respondida --> Rastreada: registrar latência + custo
    Rastreada --> [*]
```

---

## 9. Diagrama de Fases (Gantt do 1º semestre)
*Planejamento temporal — detalhe em `05_PLANO_DE_FASES.md`.*

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
      Modo local e nuvem
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

*Dica: cole qualquer bloco em [mermaid.live](https://mermaid.live) para editar visualmente.*
