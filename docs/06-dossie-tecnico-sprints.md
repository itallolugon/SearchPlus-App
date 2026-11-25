# Dossiê Técnico de Sprint — Search+

Projeto: **Search+** — busca semântica de imagens e documentos com IA.
Abordagem: **SQL** (PostgreSQL/Supabase + pgvector).
Repositório atual: https://github.com/itallolugon/SearchPlus-App
(os commits citados nas sprints são do repositório anterior,
`itallolugon/SearchPlus_Prototipo`).

> **Registro histórico.** As Sprints 1 e 2 descrevem o projeto como era na
> época: a descrição de imagens usava LLaVA e o re-rank usava Llama 3.2, ambos
> locais via Ollama. Depois disso a IA de visão e o julgamento de relevância
> passaram para o Claude, com indexação lazy (a descrição só acontece na busca).
> As tabelas foram mantidas como aconteceram. As Sprints 3 a 5 chegam ao estado
> atual, descrito também no [`README.md`](../README.md) e no
> [`RELATORIO.md`](../RELATORIO.md).

---

## Visão geral do produto (estado atual)

Aplicação web que indexa pastas do computador gerando embeddings locais (CLIP
para imagens, SBERT para o texto dos documentos) e permite buscar os arquivos em
linguagem natural ("cachorro na grama") ou por imagem (achar parecidas). Na
busca, o Claude descreve as imagens candidatas que ainda não têm descrição e
julga quais resultados correspondem de verdade.

**Stack:** Frontend (HTML/CSS/JS puro) · Backend (Flask/Python) ·
Banco (PostgreSQL/Supabase + pgvector) · Embeddings locais (SBERT, CLIP) ·
IA de visão e re-rank pelo Claude Haiku 5.5 (assinatura via Claude Code, ou API).

---

## SPRINT 1 — Núcleo de busca semântica e indexação

**Objetivo:** ter o motor de busca funcionando — indexar arquivos, descrever com
IA e buscar por significado.

| História de usuário | Tarefas técnicas | Commits | Status |
|---|---|---|---|
| Como usuário, quero **fazer login/cadastro** para ter minha conta | Auth com sessão Flask, hash de senha, tabela `users` | `63c8ab0`, `e8c03fb` | ✅ Concluída |
| Como usuário, quero **cadastrar pastas** para a IA monitorar | CRUD de `folders`, worker de scan em background | `39068c4`, `63c8ab0` | ✅ Concluída |
| Como usuário, quero que a IA **descreva minhas imagens** | Integração Ollama/LLaVA, pipeline `_analyze_image`, anti-alucinação | `d3ad884`, `fa92125` | ✅ Concluída |
| Como usuário, quero **buscar por texto em linguagem natural** | Embeddings SBERT, busca híbrida (SBERT+BM25), sinônimos, re-rank LLM | `41a7db2`, `81356e4`, `b6916c5`, `d3ad884` | ✅ Concluída |
| Como usuário, quero **resultados precisos** (sem falso-positivo) | Calibração de thresholds, detecção de gênero, correção do bug "kevin" | `657adf7`, `2bad7b3`, `f3539c7` | ✅ Concluída |

**Resultado da Sprint 1:** motor de busca semântica funcional, com indexação
automática e re-ranking por IA.

---

## SPRINT 2 — Banco em nuvem, organização e experiência

**Objetivo:** evoluir a arquitetura (banco na nuvem), enriquecer a organização do
acervo e refinar a experiência do usuário.

| História de usuário | Tarefas técnicas | Commits | Status |
|---|---|---|---|
| Como equipe, queremos **banco em nuvem** acessível de qualquer máquina | Migração SQLite → PostgreSQL/Supabase com pgvector, pool de conexões | `aff9614` | ✅ Concluída |
| Como usuário, quero **buscar por imagem** (achar parecidas) | Endpoint `/api/search_by_image`, embeddings CLIP, drag&drop | `2091a8b` | ✅ Concluída |
| Como usuário, quero **organizar em coleções** | Tabelas `collections`/`collection_files`, CRUD, capas em mosaico | `cb463be`, `0d527c6`, `7668b12` | ✅ Concluída |
| Como usuário, quero **favoritar** e **ver galeria por categoria** | Favoritos, `/api/gallery`, classificação por campos da IA | `5769480`, `f36cef2` | ✅ Concluída |
| Como usuário, quero **filtrar buscas** (data, tamanho, pasta) | Busca avançada com filtros no SQL | `e5fcdb3` | ✅ Concluída |
| Como usuário, quero **personalizar e compartilhar o tema** | Exportar/importar tema (JSON), cores, fundo | `8f8d275` | ✅ Concluída |
| Como usuário, quero uma **interface organizada** | Menu lateral (hambúrguer), toasts, modal de ajuda, atalhos | `0d527c6`, `79e2518`, `ce8ae60` | ✅ Concluída |
| Como usuário, quero **configurações que funcionem** | Blacklist de pastas, notificações, modo privado | `22e8c2d` | ✅ Concluída |

**Resultado da Sprint 2:** banco em nuvem, busca visual, coleções, galeria,
personalização e UX refinada — com várias correções de bugs validadas.

---

## SPRINT 3 — Organização do acervo e exportação (13/08 a 31/08/2026)

**Objetivo:** transformar o resultado da busca em trabalho organizado — selecionar,
agrupar em coleções e levar os arquivos para pastas do computador — e corrigir a
conexão com o banco e a busca visual.

| História de usuário | Tarefas técnicas | Evidência | Status |
|---|---|---|---|
| Como usuário, quero que o app **conecte ao banco em qualquer rede** | Troca do host direto do Supabase (só IPv6) pelo *session pooler*; correção da busca visual (CLIP) | [`08-correcoes-conexao-e-busca.md`](08-correcoes-conexao-e-busca.md) (13/08) | ✅ Concluída |
| Como usuário, quero **limpar a busca** com um clique | Botão `×` acessível, sem recarregar resultados | [`features/11-limpar-busca.md`](features/11-limpar-busca.md) (25/08), branch `feature/limpar-busca-e-colecoes` | ✅ Concluída |
| Como usuário, quero **selecionar imagens e montar coleções** | Seleção múltipla, adição em lote idempotente, capa e ordem | [`features/12-colecoes-exportacao.md`](features/12-colecoes-exportacao.md) (25/08) | ✅ Concluída |
| Como usuário, quero **exportar uma coleção** para uma pasta | Job em segundo plano com progresso, cancelamento e histórico; cópia que nunca sobrescreve | [`features/12-colecoes-exportacao.md`](features/12-colecoes-exportacao.md), [`features/13-selecao-em-massa.md`](features/13-selecao-em-massa.md) (25/08) | ✅ Concluída |
| Como usuário, quero uma **pasta vinculada** que se mantenha sozinha | Sincronia automática, sob pergunta ou manual; várias pastas de destino; exclusão com confirmação | [`features/14-pasta-vinculada.md`](features/14-pasta-vinculada.md) (29/08) | ✅ Concluída |
| Como equipe, queremos **requisitos verificáveis** | Especificação de requisitos funcionais e não funcionais antes do código; testes de carga | [`09-requisitos-funcionais.md`](09-requisitos-funcionais.md), [`10-requisitos-nao-funcionais.md`](10-requisitos-nao-funcionais.md) (25 e 30/08) | ✅ Concluída |

**Resultado da Sprint 3:** relatório de implementação de 31/08/2026 com 338
requisitos entregues e 799 testes automatizados
([`SearchPlus_Implementacoes_2026-08-31.pdf`](SearchPlus_Implementacoes_2026-08-31.pdf));
carga com até 150 usuários simultâneos sem falhas, medida contra o servidor mock.

---

## SPRINT 4 — Visual, IA via API e qualidade (01/09 a 21/10/2026)

**Objetivo:** amadurecer o produto para a N1 da PMI IV — interface nova, IA de
visão na nuvem e uma revisão de qualidade completa.

| História de usuário | Tarefas técnicas | Evidência | Status |
|---|---|---|---|
| Como usuário, quero uma **interface mais clara e moderna** | Camada visual "liquid glass", sem alterar o backend | [`features/15-visual-liquid-glass.md`](features/15-visual-liquid-glass.md) (14/09), branch `feature/visual-liquid-glass` | ✅ Concluída |
| Como usuário, quero **descrições de imagem melhores e sem instalar 12 GB** | Descrição e re-rank migrados do Ollama/LLaVA para o Claude, com indexação lazy (migração concluída antes da linha de base); ajustes posteriores no cliente e no modelo | Commits `57fef34` (10/10) e `66f4052` (19/10) | ✅ Concluída |
| Como equipe, queremos **um repositório limpo e publicável** | Nova linha de base, sem credenciais no histórico | Commit `ad669d7` (10/10) | ✅ Concluída |
| Como usuário, quero que o **modo Relâmpago/Profundo funcione** | Descrição sob demanda passa a usar o modo e o foco da pasta | Commit `ba737c9` (21/10) | ✅ Concluída |
| Como usuário, quero **ligar o app com um comando só** | Download automático dos modelos na 1ª execução; remoção dos `.bat`; mensagem clara quando o banco recusa a conexão | Commit `ba737c9` (21/10) | ✅ Concluída |
| Como equipe, queremos **documentação técnica para a N1** | Documento de 24 seções no modelo da disciplina; atualização de README, RELATORIO e diagramas | Commit `a9b60fc` (21/10), [`PDF_Preenchido_Projeto.pdf`](PDF_Preenchido_Projeto.pdf) | ✅ Concluída |

**Resultado da Sprint 4:** 852 testes, lint do backend zerado e bloqueante no CI,
cobertura de 67%, documentação técnica da N1 entregue.

---

## SPRINT 5 — Claude pela assinatura e preparação da banca (22/10 a 25/11/2026)

**Objetivo:** permitir usar a assinatura do Claude no protótipo, adotar o
Claude Haiku 5.5 e deixar o projeto pronto para a banca.

| História de usuário | Tarefas técnicas | Evidência | Status |
|---|---|---|---|
| Como usuário, quero **conectar o Claude pela minha assinatura** | Modo assinatura via Claude Code (`claude setup-token`), isolado e sem acesso a arquivos; modo chave de API como alternativa | Commit `80fd181` (24/11) | ✅ Concluída |
| Como usuário, quero **ver se o Claude está funcionando** | Indicador no dock, painel com teste, uso do plano e erros com orientação | Commit `80fd181` | ✅ Concluída |
| Como usuário, quero **buscas mais rápidas** | Descrições sob demanda em paralelo (4 fotos em 6,7 s, antes ~15 s) | Commit `80fd181` | ✅ Concluída |
| Como usuário, quero **resultados certos com o modelo novo** | Haiku 5.5 com effort high; correção da leitura dos campos em Markdown, que descartava fotos de animais | Commit `80fd181` | ✅ Concluída |
| Como equipe, queremos **chegar à banca com tudo coerente** | Diagramas de sequência atualizados, dossiê de sprints, fluxo Git e adendo 1.2 da documentação técnica | Commit desta preparação | ✅ Concluída |

**Resultado da Sprint 5:** Claude Haiku 5.5 rodando pela assinatura, 921 testes,
cobertura de ~70%, CI verde.

---

## Papéis na equipe

| Integrante | Papel |
|---|---|
| Lorenzo Osorio | Líder; UI/UX Designer |
| Itallo Lugon | Desenvolvimento |
| Kevin Kuznier | Documentação e desenvolvimento |
| João Miguel | Documentação |

> **Sobre os registros.** As Sprints 3 a 5 foram consolidadas a partir dos
> artefatos versionados — datas das especificações, relatórios e commits. O
> repositório não registra as cerimônias (planning, daily, review e
> retrospectiva) nem estimativas por história; elas não são reconstruídas aqui
> para não registrar o que não está documentado.

### Aprendizados técnicos registrados

- **Especificar antes de codar funciona.** Os requisitos de 25/08 foram escritos
  como contrato e viraram testes; a Sprint 3 entregou 338 requisitos sem
  regressão nas buscas.
- **Testar com o modelo real pega o que o teste simulado não pega.** O Haiku 5.5
  escreve os campos em Markdown; com respostas simuladas tudo passava, e só a
  chamada real mostrou que fotos de cachorro sumiam da busca por "cachorro".
- **Medir antes de otimizar.** Cronometrar uma descrição (3,8 s) mostrou que o
  gargalo era fazer as 5 em fila — e não o modelo.

---

## Integração Modelagem ↔ Scrum ↔ Código

- **Cada história** acima tem commits rastreáveis no Git (coluna "Commits").
- **Modelagem e código evoluíram juntos:** o DER ([`04-der.puml`](04-der.puml))
  reflete exatamente o `schema.sql` implementado; o Diagrama de Sequência
  ([`03-sequencia-crud-colecoes.puml`](03-sequencia-crud-colecoes.puml)) descreve
  o fluxo real do CRUD de coleções.
- **Evolução de arquitetura documentada:** a migração SQLite → Supabase
  (commit `aff9614`) é um marco arquitetural registrado.

---

## Critérios de "pronto" (Definition of Done)

**Sprints 1 e 2.** Uma história só foi considerada concluída quando:
1. Código no `main` (via merge), funcionando ponta a ponta;
2. Backend + frontend integrados e testados manualmente/por API;
3. Sem regressão nas buscas existentes.

**A partir da Sprint 3**, além disso, o portão de qualidade do CI
([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) precisa estar verde:
1. Lint e formatação sem achados (testes e backend);
2. Testes unitários e de integração passando, cobertura do backend ≥ 64%;
3. Integração com Postgres efêmero e smoke de carga contra o mock;
4. `app.py`, `mock_server.py` e `docs/API.md` em paridade (rota nova entra nos três);
5. Documentação afetada atualizada no mesmo commit.
