# 📦 Personal RAG Assistant V1 — Planejamento Completo do Projeto

> **Projeto bandeira do 1º semestre** do Roadmap Acadêmico + AI Engineering (Univesp).
> Sistema RAG local que indexa seus próprios documentos e responde perguntas sobre eles,
> com métricas de qualidade, custo e latência — pensado desde o dia 1 para virar
> **projeto público de portfólio** e base evolutiva para o V2 (2º semestre).

---

## 🎯 Por que este projeto existe

O marco que importa no 1º semestre é: **stack montada, inglês sem dicionário, 12+ papers lidos** e
**1 projeto público no GitHub com README detalhado**. O Personal RAG V1 é o veículo que amarra tudo isso:

- Te obriga a montar a stack de IA local + APIs de nuvem **de graça** (Ollama, Google Gemini free tier, Groq).
- Ensina o padrão arquitetural mais requisitado do mercado atual: **RAG** (Retrieval-Augmented Generation).
- Gera métricas reais (latência, custo/query, Recall@5) — o que separa "brinquei com LLM" de "sei medir e otimizar".
- É a **fundação técnica** que o V2 (hybrid search, reranker, eval suite completo) vai evoluir sem reescrever.

> 💡 **Princípio de design que guia tudo aqui:** *construir > consumir*. O código é modular e
> provider-agnostic de propósito, para que trocar embedding, LLM ou vector store no V2 seja
> uma troca de config, não uma reescrita.

---

## 🧭 Como navegar este planejamento

Este é um pacote de **6 documentos**. Leia na ordem sugerida:

| Documento | O que responde |
|-----------|----------------|
| **`OVERVIEW.md`** (este arquivo) | Visão geral e como tudo se conecta |
| [`SDD.md`](SDD.md) | **Como** o sistema é projetado (arquitetura, dados, componentes, decisões) |
| [`../README.md`](../README.md) | **O quê** é o projeto, para quem lê no GitHub (features, quickstart, uso) |
| [`DIAGRAMS.md`](DIAGRAMS.md) | Diagramas visuais (contexto, arquitetura, sequência, dados, classes, Gantt) |
| [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) | Árvore completa de pastas, subpastas e arquivos, com o papel de cada um |
| [`PROJECT_PLAN.md`](PROJECT_PLAN.md) | Execução por fases: tarefas, entregáveis, critério de pronto, cronograma |

---

## 🧱 O projeto em 30 segundos

**Personal RAG Assistant V1** é uma aplicação Python que:

1. **Ingere** seus documentos (PDF, Markdown, TXT, DOCX) → quebra em *chunks* → gera *embeddings* → guarda num *vector store* local.
2. **Recupera** os trechos mais relevantes para uma pergunta (busca por similaridade semântica, top-k).
3. **Gera** uma resposta ancorada nesses trechos, com **citação da fonte**, usando um LLM (Google Gemini na nuvem — **free tier** — ou Llama 3.2 local via Ollama; Groq como fallback quando a quota diária do Gemini acaba).
4. **Mede** a si mesmo: latência média, tokens/query, consumo de quota do free tier e Recall@5 num conjunto dourado de 30 perguntas. (Custo real = **$0**; o custo em USD é *calculado* para mostrar quanto custaria no tier pago.)
5. Tudo acessível por uma **interface de chat** (Streamlit).

### Stack recomendada (V1)

| Camada | Escolha V1 | Alternativa / por quê |
|--------|-----------|-----------------------|
| Linguagem | **Python 3.11+** | Padrão do ecossistema de IA |
| Orquestração | **LangChain** | Sinaliza fluência no framework mais usado; LlamaIndex é a alternativa mais "RAG-first" |
| Vector store | **ChromaDB** (local, zero-config) | Caminho de migração para **pgvector** documentado no SDD |
| Embeddings | **Google `text-embedding-004`** (free tier) | Grátis; `nomic-embed-text` via Ollama para modo 100% local. ⚠️ trocar de modelo invalida o índice (ver SDD §5.3) |
| LLM | **Gemini free** + **Ollama (Llama 3.2)** + **Groq** (fallback) | Todos free; provider-agnostic: troca por config. OpenAI/Anthropic viram adapter opcional |
| Frontend | **Streamlit** | Rápido de construir; foco é o RAG, não o front |
| Observabilidade | **Langfuse** | Tracing de cada etapa (retrieval + geração) |
| Gerência de deps | **uv** | Rápido e moderno; Poetry é a alternativa consagrada |
| Qualidade | **pytest + ruff + pre-commit** | Disciplina de engenharia desde o V1 |

---

## ✅ Definição de sucesso (gate de saída do 1º semestre)

O projeto está "pronto o suficiente" quando **todos** os itens abaixo forem verdade:

- [ ] Repositório público no GitHub com **README detalhado** (screenshots + GIF de uso).
- [ ] Pipeline de ingestão funciona para PDF, MD e TXT.
- [ ] Chat responde com **citação da fonte** (arquivo + trecho).
- [ ] Funciona em **dois modos**: nuvem (Gemini free tier) e **100% local** (Ollama). Groq disponível como fallback de nuvem.
- [ ] **Métricas publicadas** no README: latência média (ms), tokens/query, custo *calculado* (USD, com nota de que o real é $0 no free tier), Recall@5 sobre 30 perguntas.
- [ ] Testes automatizados passando + CI verde (GitHub Actions).
- [ ] Config por `.env` (nenhuma chave commitada).

> Ver critério de pronto detalhado por fase em [`PROJECT_PLAN.md`](PROJECT_PLAN.md).

---

## 🔭 Escopo — o que NÃO entra no V1 (fica pro V2)

Manter o escopo apertado é o que faz o V1 terminar. Explicitamente **fora**:

- ❌ Hybrid search (BM25 + dense) e Reciprocal Rank Fusion → **V2**
- ❌ Reranker (Cohere / cross-encoder) → **V2**
- ❌ Eval framework completo (Ragas/TruLens, LLM-as-judge, NDCG/MRR/faithfulness) → **V2**
- ❌ Multi-usuário / autenticação → fora do roadmap V1/V2
- ❌ Deploy público em produção → opcional, não obrigatório no V1

O SDD foi desenhado para que **cada um desses seja um ponto de extensão**, não uma refatoração.

---

*Documento gerado a partir do roadmap "01_faculdade_e_topicos → 🗓️ Roadmap Semestre a Semestre" (Central da Minha Vida). Este é um documento vivo — atualize conforme o projeto evolui.*
