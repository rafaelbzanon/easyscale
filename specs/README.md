# Índice de especificações e decisões

- **Trilha:** Comum
- **Tarefa:** C-101 (`specs/tarefas-iniciais.md`)
- **Atualizado em:** 2026-11-07

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
| 009 | [contrato-api-operacao](features/009-contrato-api-operacao/spec.md) | Contrato | Aprovada (delegada, 2026-11-07) | CT-103 |
| 010 | [contrato-api-historico](features/010-contrato-api-historico/spec.md) | Contrato | Aprovada (delegada, 2026-11-07) | CT-104 |
| 011 | [contrato-api-diagnostico](features/011-contrato-api-diagnostico/spec.md) | Contrato | Aprovada (delegada, 2026-11-07) | CT-105 |
| 012 | [contrato-api-autenticacao](features/012-contrato-api-autenticacao/spec.md) | Contrato | Aprovada (delegada, 2026-11-07) | CT-106 |
| 013 | [contrato-api-autoatendimento](features/013-contrato-api-autoatendimento/spec.md) | Contrato | Aprovada (delegada, 2026-11-07) | CT-107 |
| 014 | [persistencia](features/014-persistencia/spec.md) | Backend | Implementada (delegada, 2026-11-07; revisão final pendente) | BE-502, BE-503 |
| 015 | [orquestracao-operacao](features/015-orquestracao-operacao/spec.md) | Backend | Implementada (delegada, 2026-11-07; revisão final pendente) | BE-601, BE-602 |
| 016 | [esqueleto-frontend](features/016-esqueleto-frontend/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-101, FE-102 |
| 017 | [tela-login-usuarios](features/017-tela-login-usuarios/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-308 |
| 018 | [tela-cadastros](features/018-tela-cadastros/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-301 |
| 019 | [tela-agendamentos](features/019-tela-agendamentos/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-302 |
| 020 | [tela-autoatendimento](features/020-tela-autoatendimento/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-307 |
| 021 | [tela-historico](features/021-tela-historico/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-304 |
| 022 | [tela-operacao](features/022-tela-operacao/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-303 |
| 023 | [tela-diagnostico](features/023-tela-diagnostico/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-305 |
| 024 | [tela-dispositivos-intervencao](features/024-tela-dispositivos-intervencao/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-306 |
| 025 | [docker-backend](features/025-docker-backend/spec.md) | Backend | Implementada (delegada, 2026-11-07; revisão final pendente) | BE-801 |
| 026 | [docker-frontend](features/026-docker-frontend/spec.md) | Frontend | Implementada (delegada, 2026-11-07; revisão final pendente) | FE-401 |
| 027 | [compose](features/027-compose/spec.md) | Integração | Implementada (delegada, 2026-11-07; revisão final pendente) | INT-001 |
| 028 | [ponta-a-ponta](features/028-ponta-a-ponta/spec.md) | Integração | Implementada (delegada, 2026-11-07; revisão final pendente) | INT-002 |

## 3. ADRs (`docs/decisoes/`)

| ADR | Título | Trilha | Status | Tarefa |
|---|---|---|---|---|
| [ADR-0001](../docs/decisoes/ADR-0001-banco-de-dados.md) | Banco de dados (PostgreSQL) | Comum | Aceita | C-201 |
| [ADR-0002](../docs/decisoes/ADR-0002-monolito-modular.md) | Monólito modular vs. serviços | Comum | Aceita | C-202 |
| [ADR-0003](../docs/decisoes/ADR-0003-ferramentas-backend.md) | Ferramentas do backend | Backend | Aceita | BE-001 |
| [ADR-0004](../docs/decisoes/ADR-0004-autenticacao-perfis.md) | Autenticação, sessão e perfis | Contrato | Aceita | CT-001 |
| [ADR-0005](../docs/decisoes/ADR-0005-atualizacao-tempo-real.md) | Atualização em tempo real | Contrato | Aceita | CT-002 |
| [ADR-0006](../docs/decisoes/ADR-0006-orm-migracoes.md) | Acesso ao banco e migrações | Backend | Aceita (delegada, 2026-11-07) | BE-501 |
| [ADR-0007](../docs/decisoes/ADR-0007-framework-frontend.md) | Framework do frontend (React + Vite) | Frontend | Aceita (delegada, 2026-11-07) | FE-001 |
| [ADR-0008](../docs/decisoes/ADR-0008-ferramentas-frontend.md) | Ferramentas do frontend | Frontend | Aceita (delegada, 2026-11-07) | FE-002 |

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

Perguntas da spec 015 §14 (2026-11-07), com comportamento seguro provisório: Q-A (confirmação manual da balança vazia na liberação de caminhão cancelado), Q-B (como a câmera superior distingue o caminhão; ligada à Q-17), Q-C (qual câmera lê a placa e nomes das câmeras; ligada à Q-06). Q-D (revisão de segurança, 2026-11-07): ao cancelar com a cancela de entrada aberta ou desconhecida, a liberação deve fechar a entrada? Hoje a fila para até a cancela voltar a FECHADA (seguro).

Perguntas dos contratos 009 e 011 (2026-11-07): 009 P-1 (limite de tempo da leitura na liberação manual de entrada), 009 P-2 (liberação de caminhão sem a câmera confirmar a balança vazia; mesma da 015 Q-A), 011 P-1 (LGPD, Q-08), 011 P-2 (câmeras, Q-06).

Perguntas das telas (2026-11-07): Q-F1 (tamanho da tela do totem), Q-F2 (o totem mostra o modo REAL/SIMULADO? a spec 013 não traz esse dado), Q-F3 (spec 018: a mensagem de erro do backend é genérica e só há os códigos `CAMPO_INVALIDO`, `CONFLITO`, `PLACA_INVALIDA` por campo), Q-F4 (spec 019: o "hoje" padrão do filtro vem do relógio do navegador, porque o contrato não traz o dia do pátio), Q-F6 a Q-F8 (spec 020: 7 dias à frente e 60 s de inatividade são constantes da tela; o bloqueio do totem não informa o tempo restante), Q-F9 (spec 021: horas exibidas no fuso do navegador).

Pergunta da spec 028 (2026-11-07): P-1, o SSE monta a pesagem com o estado do banco no envio, então um leitor lento pode receber a mesma versão repetida (o frontend ignora; confirmar se é o desejado).

Outras pendências:

- Ponto de controle único semeado pela migração `0004` (decisão delegada; nenhum contrato cadastra equipamentos), 2026-11-07.

- CNPJ alfanumérico (spec 007 §5.1): a BE-701 seguiu a IN RFB 2.229/2024; falta a confirmação do autor.

- Spec 001 CA-007 (`dependencies = []`) deixou de valer com o ADR-0006 (dependências de execução do banco), 2026-11-07.

| ID | Pergunta | Origem | Bloqueia |
|---|---|---|---|
| — | Licença: `LICENSE` MIT já existe, mas D-12 consta como pendente | C-001 | INT-003 |
| — | Arquivos vazios `backend/app/*`: exclusão preparada no Git, ainda sem commit | C-001 | — |
| — | Aceite do autor da BE-102 (spec 001) não registrado | BE-102 | — |
| — | `glossario.md` continua `Em revisão` desde a C-101 | C-101 | — |
