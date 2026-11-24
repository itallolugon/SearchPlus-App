<div align="center">

# 🔍 Search+ — Relatório Técnico do Projeto

**Busca semântica de imagens e documentos locais com IA**

![Status](https://img.shields.io/badge/status-protótipo_funcional-success)
![Stack](https://img.shields.io/badge/stack-Flask_·_JS_·_Postgres-blue)
![IA](https://img.shields.io/badge/IA-Claude_·_SBERT_·_CLIP-purple)
![DB](https://img.shields.io/badge/banco-Supabase_+_pgvector-3ECF8E)

</div>

> **Repositório:** [github.com/itallolugon/SearchPlus-App](https://github.com/itallolugon/SearchPlus-App) · **Branch:** `main`
> **Data do relatório:** 2026-10-21 · **Base:** commit `66f4052` e as correções desta revisão

Documentação técnica completa, no modelo da disciplina:
[`docs/PDF_Preenchido_Projeto.pdf`](docs/PDF_Preenchido_Projeto.pdf). Contrato da
API: [`docs/API.md`](docs/API.md). Testes e CI: [`docs/TESTING.md`](docs/TESTING.md).

---

## 📑 Índice

1. [O que é o Search+](#1-o-que-é-o-search)
2. [Stack técnico](#2-stack-técnico)
3. [Indexação lazy e pipeline de busca](#3-indexação-lazy-e-pipeline-de-busca)
4. [Descrição de imagens](#4-descrição-de-imagens)
5. [Banco de dados](#5-banco-de-dados)
6. [API](#6-api)
7. [Segurança aplicada](#7-segurança-aplicada)
8. [Qualidade: testes, carga e CI](#8-qualidade-testes-carga-e-ci)
9. [Análise heurística de Nielsen](#9-análise-heurística-de-nielsen)
10. [Histórico](#10-histórico)
11. [Experimentos que não deram certo](#11-experimentos-que-não-deram-certo)
12. [Pendências e próximos passos](#12-pendências-e-próximos-passos)
13. [Limitações conhecidas](#13-limitações-conhecidas)

---

## 1. O que é o Search+

Aplicativo de **busca semântica para arquivos locais** — imagens (PNG, JPG, GIF,
WEBP, BMP) e documentos (PDF, DOCX, TXT, CSV). O usuário aponta pastas do PC e
pesquisa em **linguagem natural** em vez de procurar por nome de arquivo:

> 🗣️ *"cachorro brincando"* · *"prato de comida com kebab"* · *"festa noturna"*

O servidor roda na máquina do usuário (`http://127.0.0.1:5000`). Os embeddings
(SBERT e CLIP) rodam localmente; a descrição de imagens e o julgamento de
relevância usam a API do Claude; o banco é PostgreSQL com pgvector no Supabase.

---

## 2. Stack técnico

| Camada | Tecnologia | Onde roda |
|---|---|---|
| Frontend | HTML/CSS/JS puro (`index.html`, `script.js`, `style.css`) — sem framework nem build | Navegador |
| Backend | Flask (Python ≥ 3.11) em `backend/app.py`: API REST, worker de indexação, jobs de exportação, entrega do front | Local |
| Embeddings de texto | SBERT `paraphrase-multilingual-MiniLM-L12-v2` (384 dim) | Local |
| Embeddings visuais | CLIP `clip-ViT-B-32` + `clip-ViT-B-32-multilingual-v1` (512 dim) | Local |
| Descrição de imagens e re-rank | Claude Haiku 5.5 (`claude-haiku-5-5`), effort `high` — ambos ajustáveis na tela | Assinatura via Claude Code, ou API (nuvem) |
| Banco de dados | PostgreSQL + pgvector, índices HNSW | Supabase (nuvem) |
| Desenvolvimento do front | `backend/mock_server.py` — mesma API, dados fixos | Local (porta 5001) |

Os modelos locais (~1,6 GB) são baixados sozinhos na primeira execução e, depois,
carregados do cache sem rede.

---

## 3. Indexação lazy e pipeline de busca

**Indexar não chama o Claude.** Ao adicionar uma pasta, o worker gera só o
embedding CLIP de cada imagem e extrai o texto dos documentos (com o embedding
SBERT). É rápido e não custa nada. Uma imagem sem descrição é estado normal.

**Na busca:**

| # | Etapa | O que faz |
|---|---|---|
| 1 | **Análise da consulta** | Tokenização, stopwords, sinônimos PT-BR, variantes singular↔plural, exclusão com `-palavra` |
| 2 | **Candidatos** | pgvector devolve os 100 mais próximos por SBERT; uma segunda consulta traz até 40 imagens só com CLIP |
| 3 | **Descrição sob demanda** | O Claude descreve as até 5 imagens visualmente mais próximas que ainda não têm descrição, no modo e foco da pasta, e a descrição fica em cache |
| 4 | **Blend** | Imagens `0,45·SBERT + 0,25·BM25 + 0,30·CLIP`; documentos `0,65·SBERT + 0,35·BM25`. O CLIP é reescalado antes, porque o cosseno texto↔imagem vive em ~[0,15; 0,30] |
| 5 | **Regras** | `_ajustar_score` rejeita o impossível (busca por pessoa em imagem sem pessoas, gênero oposto) e reforça nome, palavra-chave e estilo |
| 6 | **Re-rank** | O Claude julga, com saída estruturada, quais dos 15 primeiros correspondem; imagens e documentos têm réguas diferentes |
| 7 | **Corte** | Só fica `score > 0,25`; até 60 resultados, cada um com a origem do acerto |

Se a API falhar, a ordem do motor é mantida. O custo por busca é limitado: no
máximo 5 descrições e 1 re-rank, e cada imagem é descrita uma única vez.

---

## 4. Descrição de imagens

O prompt (`_build_prompt_visao`) produz campos fixos que a busca, o embedding e a
galeria leem:

```
- Estilo: · O que é: · Pessoas: · Animais: · Objetos: · Ambiente: · Ações: · Texto: · Tags:
```

- **Desenhos contam pelo que representam**: um cachorro de desenho animado vai
  em `Animais: cachorro`. Sem essa regra, todo desenho caía nas rejeições.
- **Anti-alucinação**: o prompt proíbe inventar pessoas, animais ou objetos não
  visíveis.
- **Modo da pasta**: *Relâmpago* (`fast`) gera descrições econômicas; *Profundo*
  (`deep`) é mais minucioso (espécies, marcas, texto visível). O foco escolhido
  (pessoas, animais, paisagens…) entra no prompt.
- A imagem é reduzida para no máximo 768 px e recodificada em JPEG antes do envio.

---

## 5. Banco de dados

Nove tabelas em [`backend/schema.sql`](backend/schema.sql), aplicado de forma
idempotente a cada inicialização: `users`, `folders`, `files`, `collections`,
`collection_files`, `collection_folders`, `exportacoes`, `lixeira` e
`resumos_indexacao`. DER em [`docs/04-der.puml`](docs/04-der.puml) e camada de
acesso em [`docs/05-modelagem-dados-DER-ORM.md`](docs/05-modelagem-dados-DER-ORM.md).

| Índice | Tipo | Uso |
|---|---|---|
| `files_embedding_idx` | HNSW `vector_cosine_ops` | busca SBERT |
| `files_embedding_clip_idx` | HNSW `vector_cosine_ops` | busca CLIP |
| `files_user_processado_idx` | B-tree `(user_id, processado)` | filtro por usuário |
| demais `*_user_idx` | B-tree | listas por usuário, em ordem de data |

---

## 6. API

**54 rotas** `/api/*`, com sessão por cookie (`HttpOnly`, `SameSite=Lax`).
Grupos: sessão, configuração, pastas, indexação, busca, home, favoritos,
coleções, exportação, lixeira, histórico, arquivos/sistema e diagnóstico
(`/api/health`, pública). Contrato completo, com payloads e erros, em
[`docs/API.md`](docs/API.md). `app.py`, `mock_server.py` e `API.md` são mantidos
em sincronia e conferidos por `tests/integration/test_paridade_mock.py`.

---

## 7. Segurança aplicada

| ✅ | Item |
|:---:|---|
| ✅ | Senhas com **bcrypt** (limite de 72 bytes); hashes SHA-256 antigos migram no login |
| ✅ | Toda rota de dados filtra por `user_id`; sem sessão → 401 (5 rotas de pré-login devolvem só valores vazios/padrão) |
| ✅ | `/api/file`, `/api/open_location` e `/api/open_folder` só abrem caminhos dentro das pastas do usuário, com `realpath` e recusa de byte nulo |
| ✅ | Arquivos estáticos por **allowlist**: `.env`, `.git/`, `backend/` e `docs/` nunca são servidos |
| ✅ | SQL sempre parametrizado; CORS com lista fechada de origens |
| ✅ | Mensagens de erro ao usuário sem detalhe interno; o detalhe vai só para o log |
| ✅ | Nomes de arquivo escapados antes de entrar no HTML |
| ✅ | Credenciais em `backend/.env` e chave de sessão em `backend/.secret_key`, ambos fora do Git |
| ✅ | A única operação destrutiva (apagar pastas geradas) exige `confirmar: true` e caminho registrado |

---

## 8. Qualidade: testes, carga e CI

- **852 testes** (unitários + integração contra o mock) em ~10 s, sem banco, sem
  modelos e sem chave da API; cobertura do backend **~67%** (piso de 64% no CI).
- **Carga (Locust)** contra o mock em 30/08/2026: `smoke`, `load` e `stress` (até
  150 usuários) com **0 falhas** e p95 ≤ 280 ms.
- **CI (GitHub Actions)**: lint de testes e backend, testes com cobertura,
  integração com Postgres efêmero, build e smoke de carga, agregados num portão.

Detalhes e comandos em [`docs/TESTING.md`](docs/TESTING.md).

---

## 9. Análise heurística de Nielsen

Avaliação das 10 heurísticas feita em maio/2026, com as correções aplicadas
desde então.

| # | Heurística | Situação |
|---|---|---|
| 1 | Visibilidade do status do sistema | ✅ barra de indexação com tempo restante; aviso enquanto os modelos carregam |
| 2 | Correspondência com o mundo real | ✅ |
| 3 | Controle e liberdade | ✅ cancelar análise; lixeira para desfazer exclusões |
| 4 | Consistência e padrões | ✅ feedback só por toast e modais próprios — nenhum `alert()` nativo |
| 5 | Prevenção de erros | ✅ confirmação em duas etapas para apagar pastas |
| 6 | Reconhecimento em vez de memorização | ✅ histórico de buscas |
| 7 | Flexibilidade e eficiência | ✅ atalhos `/` e `Esc`; busca avançada com filtros |
| 8 | Estética e design minimalista | ✅ |
| 9 | Recuperação de erros | ✅ mensagens que dizem o que aconteceu e o que fazer |
| 10 | Ajuda e documentação | ✅ modal de ajuda no app |

---

## 10. Histórico

| Quando | Marco |
|---|---|
| até 05/2026 | Protótipo com IA local (LLaVA + Llama 3.2 via Ollama); migração de SQLite para Supabase/pgvector; correções das heurísticas de Nielsen |
| entre 05 e 10/2026 | IA de visão e re-rank migram para a API do Claude; indexação lazy |
| 31/08/2026 | Coleções com exportação, pasta vinculada, lixeira, refinamento da busca, resumo de indexação ([relatório](docs/SearchPlus_Implementacoes_2026-08-31.pdf)) |
| 10/10/2026 | Linha de base limpa do repositório atual (`ad669d7`) |
| 19/10/2026 | Modelo padrão trocado para o Claude Sonnet 5.5 (`66f4052`) |
| 24/11/2026 | Tela "Conexão com o Claude": modo assinatura (Claude Code + `claude setup-token`) ou chave de API, indicador no dock, Haiku 5.5 com effort high como padrão |
| 21/10/2026 | Documentação técnica da PMI IV; correções desta revisão (ver abaixo) |

**Correções de 21/10/2026:**
- A descrição sob demanda passou a respeitar o modo (Relâmpago/Profundo) e o foco
  da pasta. Desde a indexação lazy as duas escolhas eram gravadas e ignoradas.
- O download dos modelos na primeira execução passou a ser automático, o que
  dispensou o `rodar.bat`.
- O cadastro e os seletores nativos deixaram de devolver o texto da exceção ao usuário.
- Os cards de resultado e de favoritos passaram a escapar o nome do arquivo.
- O lint do backend foi zerado e passou a barrar o CI.

---

## 11. Experimentos que não deram certo

### 🧪 Qwen 2.5 VL — testado e revertido em 2026-05-22

Na fase da IA local, o `qwen2.5vl` (7b e 3b) foi testado no lugar do LLaVA. Numa
RTX 4060 de 8 GB levava de 7 a 12 min por imagem, porque o llama.cpp/Ollama ainda
processava o vision encoder dele na CPU. O LLaVA levava ~1 min por imagem.

### 📦 Pacote portátil com instalador

Um ZIP com scripts `.bat` foi testado e removido: dependia do Ollama local (~12 GB
para o usuário final). Esse peso, somado ao tempo por imagem, motivou a troca da IA
local pela API — instalação menor e descrições melhores, ao custo de enviar as
imagens candidatas a um serviço externo e de pagar por uso.

---

## 12. Pendências e próximos passos

**Já resolvido** (estava pendente no relatório de maio): bcrypt, testes
automatizados, CLIP ligado, busca avançada (data, tamanho, pasta), salvar
resultados em coleções e indicador de progresso da indexação.

**Para produção:**
- [ ] HTTPS e limite de tentativas de login (hoje o servidor só escuta em `127.0.0.1`)
- [ ] Hospedar o backend num servidor (não há infraestrutura de deploy definida)
- [ ] Logging estruturado no lugar dos `print`
- [ ] Rotacionar periodicamente a senha do banco e a chave da API

**Para a busca e a qualidade:**
- [ ] Teste de ponta a ponta do `api_search` com Postgres semeado
- [ ] Testes de comportamento do frontend
- [ ] Conjunto fixo de consultas para medir regressão de ranking
- [ ] Calibrar as metas de desempenho contra o backend real (hoje medidas no mock)

---

## 13. Limitações conhecidas

- 🪟 Seletores nativos (tkinter) e "abrir no Explorer" só funcionam no **Windows**
- 📡 **Sem internet não há app**: o banco e a IA de visão estão na nuvem
- ⏱️ A primeira busca por um assunto novo pode levar dezenas de segundos (o Claude
  descreve as candidatas); com o cache quente, 2 a 4 s
- 🔒 As imagens candidatas (reduzidas) são enviadas à API da Anthropic
- 📄 Vídeo, áudio, XLSX e ODT são indexados só pelo nome; `.doc` legado não é lido
- 🔑 Sem a chave da Anthropic, a busca perde o re-rank e falsos positivos (gato numa
  busca por cachorro) voltam a aparecer

---

<div align="center">

*Search+ · busca semântica de imagens e documentos*

</div>
