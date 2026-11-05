# Índice de especificações e decisões

- **Trilha:** Comum
- **Tarefa:** C-101 (`specs/tarefas-iniciais.md`)
- **Atualizado em:** 2026-11-04

Este índice é atualizado na mesma mudança que cria ou altera uma spec, um ADR ou uma pergunta.

Status de spec: `Rascunho` → `Em revisão` → `Aprovada` → `Implementada` → `Obsoleta`.
Status de ADR: `Proposta` → `Aceita` → `Substituída`.

---

## 1. Documentos base

| Documento | Trilha | Status |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) — como trabalhar | Comum | Vigente |
| [`AMBIENTE.md`](../AMBIENTE.md) — o quê e com quê | Comum | Vigente |
| [`CONVENCOES.md`](../CONVENCOES.md) — nomes e pastas | Comum | Aprovado (2026-10-29) |
| [`tarefas-iniciais.md`](tarefas-iniciais.md) — tarefas por trilha | Comum | Vigente |
| [`glossario.md`](glossario.md) — termos do domínio | Comum | Em revisão |
| [`requisitos.md`](requisitos.md) — RF/RNF/RN | Comum | Aprovada (2026-10-29) |
| [`docs/artigo/artigo-tcc.pdf`](../docs/artigo/artigo-tcc.pdf) — artigo do TCC | Comum | Referência [ARTIGO] |
| [`docs/modelo-dados/schema.sql`](../docs/modelo-dados/schema.sql) — esquema de referência PostgreSQL | Comum | Referência [PROPOSTA] (C-002) |

## 2. Especificações de feature

| Nº | Slug | Trilha | Status | Tarefa |
|---|---|---|---|---|
| 001 | [esqueleto-backend](features/001-esqueleto-backend/spec.md) | Backend | Implementada | BE-101, BE-102 |
| 002 | [regras-pesagem](features/002-regras-pesagem/spec.md) | Backend | Implementada | BE-202, BE-212 |
| 003 | [normalizacao-placa](features/003-normalizacao-placa/spec.md) | Backend | Implementada | BE-203, BE-211 |
| 004 | [camada-dispositivos](features/004-camada-dispositivos/spec.md) | Backend | Implementada | BE-301, BE-302 |
| 005 | [pipeline-lpr](features/005-pipeline-lpr/spec.md) | Backend | Implementada | BE-401, BE-402 |
| 006 | [maquina-estados-operacao](features/006-maquina-estados-operacao/spec.md) | Backend | Implementada | BE-201, BE-213 |
| 007 | [contrato-api-cadastros](features/007-contrato-api-cadastros/spec.md) | Contrato | Aprovada | CT-101 |
| 008 | [contrato-api-agendamentos](features/008-contrato-api-agendamentos/spec.md) | Contrato | Aprovada | CT-102 |

## 3. ADRs (`docs/decisoes/`)

| ADR | Título | Trilha | Status | Tarefa |
|---|---|---|---|---|
| [ADR-0001](../docs/decisoes/ADR-0001-banco-de-dados.md) | Banco de dados (PostgreSQL) | Comum | Aceita | C-201 |
| [ADR-0002](../docs/decisoes/ADR-0002-monolito-modular.md) | Monólito modular vs. serviços | Comum | Aceita | C-202 |
| [ADR-0003](../docs/decisoes/ADR-0003-ferramentas-backend.md) | Ferramentas do backend | Backend | Aceita | BE-001 |
| [ADR-0004](../docs/decisoes/ADR-0004-autenticacao-perfis.md) | Autenticação, sessão e perfis | Contrato | Aceita | CT-001 |
| [ADR-0005](../docs/decisoes/ADR-0005-atualizacao-tempo-real.md) | Atualização em tempo real | Contrato | Aceita | CT-002 |

## 4. Perguntas em aberto

Perguntas do `AMBIENTE.md` §17 sem resposta completa, apresentadas ao autor na C-103 (2026-10-29 e 2026-11-04):

| ID | Tema | Bloqueia |
|---|---|---|
| Q-01 | Equipamentos reais e protocolos (parcial, spec 004) | `BalancaSerial` e `CancelaSerial` (modo `REAL`) |
| Q-07 | SO e equipamento de execução; GPU | BE-801, INT-001 |
| Q-06 | Câmeras: tipo, resolução e uso das câmeras da frente e de trás (parcial, 2026-11-04) | Fontes de câmera real; BE-601 |
| Q-08 | Imagens: adequação à LGPD (parcial, 2026-11-04; RN-022) | BE-502 |
| Q-09 | Autorização e restrições de publicação do acervo (parcial, spec 005) | Avaliação do LPR com o acervo |
| Q-03 | Significado de "documentos" (parcial, `codigo_nota`; inclui nota fiscal, C-002 item 18) | Escopo |
| Q-12 | Volume esperado (parcial, 2026-11-04: uma balança por enquanto) | Pode esperar |

Respondidas em 2026-10-29: Q-14 (produtos e tipos de veículo no escopo), Q-15 (cancelas de entrada e saída; RN-012), Q-16 (só administrador edita/cancela agendamento; RN-013), Q-02 (fórmula do líquido; RN-006), Q-04 (só o administrador libera manualmente; RN-016), Q-10 (placas BR antigo e Mercosul; RN-017), Q-13 (faixas de horário; RF-028, RF-029, RN-014, RN-015).

Respondidas em 2026-11-04: Q-05 (orientação fora do protótipo; RF-012), Q-11 (`ADMINISTRADOR`, `OPERADOR` e `AUDITOR`, com novos perfis possíveis; RF-031) e Q-17 (câmera superior identifica a posição, podendo combinar todas as câmeras; RF-027, RN-012).

Outras pendências:

| ID | Pergunta | Origem | Bloqueia |
|---|---|---|---|
| — | Licença: `LICENSE` MIT já existe, mas D-12 consta como pendente | C-001 | INT-003 |
| — | Arquivos vazios `backend/app/*`: exclusão preparada no Git, ainda sem commit | C-001 | — |
| — | Aceite do autor da BE-102 (spec 001) não registrado | BE-102 | — |
| — | `glossario.md` continua `Em revisão` desde a C-101 | C-101 | — |
