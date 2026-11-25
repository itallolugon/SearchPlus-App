# Organização do Git — Search+

Como a equipe versiona o código, em duas fases. A primeira seguiu o Git Flow
pedido na N2; a segunda, a partir da linha de base do repositório atual, trocou a
branch de integração por um portão de qualidade automático na `main`.

## Fase 1 — Git Flow (repositório anterior, até 09/2026)

No repositório `itallolugon/SearchPlus_Prototipo` a equipe usou o Git Flow
simplificado exigido na N2:

| Branch | Papel |
|---|---|
| **main** | Versão estável, sempre funcional. É o que se apresenta. |
| **develop** | Integração do trabalho em andamento. Recebia as `feature/*` antes da `main`. |
| **feature/\*** | Uma branch por funcionalidade nova. |

```
feature/nome  ──►  develop  ──►  main
   (desenvolve)    (integra)    (estável/release)
```

Branches de funcionalidade registradas nas especificações:

| Branch | Funcionalidade | Especificação |
|---|---|---|
| `feature/limpar-busca-e-colecoes` | Limpar a busca, seleção, coleções e exportação | [`features/11`](features/11-limpar-busca.md), [`features/12`](features/12-colecoes-exportacao.md) |
| `feature/selecionar-todas-e-exportacao-imediata` | Seleção em massa e pasta vinculada | [`features/13`](features/13-selecao-em-massa.md), [`features/14`](features/14-pasta-vinculada.md) |
| `feature/visual-liquid-glass` | Nova camada visual | [`features/15`](features/15-visual-liquid-glass.md) |

## Fase 2 — `main` com portão de qualidade (repositório atual, desde 10/10/2026)

O repositório atual, `itallolugon/SearchPlus-App`, nasceu de uma linha de base
limpa (commit `ad669d7`) e trabalha direto na `main`. O papel que a `develop`
cumpria — impedir que código quebrado chegue à versão estável — passou para o CI
([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)), que roda a cada push
e a cada pull request:

| Job | O que barra |
|---|---|
| Lint e formatação | Achado de lint ou formatação fora do padrão, nos testes e no backend |
| Testes e cobertura | Teste falhando ou cobertura do backend abaixo de 64% |
| Integração com Postgres | Falha contra um Postgres com pgvector descartável |
| Verificação de build | Módulo Python que não compila ou arquivo do frontend faltando |
| Smoke de carga | Erro acima de 1% ou p95 acima do limite contra o mock |
| **Portão de qualidade** | Qualquer um dos anteriores — é o check único exigido |

Por que a mudança: com a equipe trabalhando em partes diferentes do projeto, a
`develop` virava uma cópia da `main` com atraso, e o que de fato segurava
regressões eram os testes. Com o portão automático, a garantia ficou explícita
e verificável em cada commit, no histórico de execuções do GitHub Actions.

Funcionalidades grandes ou arriscadas continuam podendo nascer numa
`feature/*` e entrar por pull request — o portão roda nela antes do merge.

## Convenção de mensagens de commit

Prefixos semânticos, com escopo opcional entre parênteses:

| Prefixo | Uso | Exemplo real |
|---|---|---|
| `feat:` | Nova funcionalidade | `feat(ia): tela de conexão com o Claude, modo assinatura e Haiku 5.5` |
| `fix:` | Correção de defeito | `fix: respeita o modo da pasta na descrição e dispensa os .bat` |
| `refactor:` | Mudança interna sem alterar comportamento | `refactor(ia): troca o modelo para o Sonnet 5.5 e remove o experimento do Pool` |
| `test:` | Testes | `test: monta os caminhos de pasta com os.path.join` |
| `docs:` | Documentação | `docs: conexão com o Claude, modo assinatura e Haiku 5.5` |
| `chore:` | Manutenção e organização | `chore: initialize clean project baseline` |

O corpo da mensagem explica o **porquê** da mudança, não só o quê.

## Estado atual

- `main` — estável, com o portão de qualidade verde.
- Histórico completo das entregas: [Dossiê de Sprints](06-dossie-tecnico-sprints.md).
