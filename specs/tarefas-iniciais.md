# Tarefas iniciais — entendimento do projeto e início do desenvolvimento

Sistema open-source de automação de pesagem rodoviária com LPR e visão computacional (TCC — IFRS, Veranópolis).

Local: `specs/tarefas-iniciais.md` (kebab-case, conforme `CONVENCOES.md` §3) — aprovado pelo autor em 2026-10-29 (C-003). A trilha A mantém este arquivo.

Esta lista guia o agente (OpenCode) do zero até um protótipo com backend e frontend. Ela **não substitui** o `AGENTS.md`, o `AMBIENTE.md` nem o `CONVENCOES.md`. Em caso de conflito, esses documentos prevalecem e o agente deve avisar o autor.

Legenda: **[ARTIGO]**, **[DEFINIDO]**, **[PROPOSTA]**, **[PENDENTE]** — mesma do `AGENTS.md` §0. 🔒 = porta de aprovação do autor.

---

## 0. Trilhas e regras de separação (ler antes de qualquer tarefa)

O trabalho está dividido em **cinco trilhas**. Cada tarefa pertence a **uma única trilha** e só pode alterar as pastas permitidas dela.

| Trilha | Prefixo | Pode alterar | Não pode alterar |
|---|---|---|---|
| **A — Base comum** | `C-` | `specs/` (requisitos, glossário, índice, `tarefas-iniciais.md`), `docs/decisoes/`, `AMBIENTE.md`, `CONVENCOES.md` | `backend/`, `frontend/` |
| **B — Backend** | `BE-` | `backend/`, specs e ADRs marcados "Trilha: Backend" | `frontend/`, specs de contrato |
| **C — Contratos de API** (ponte) | `CT-` | specs marcadas "Trilha: Contrato", ADRs transversais | `backend/`, `frontend/` (nenhum código) |
| **D — Frontend** | `FE-` | `frontend/`, specs e ADRs marcados "Trilha: Frontend" | `backend/`, specs de contrato |
| **E — Integração** | `INT-` | `compose.yaml`, `.env.exemplo`, `README.md`, `backend/tests/ponta_a_ponta/` | lógica de `backend/src/` e `frontend/src/` |

### Regras

- **S-1 — Uma trilha por sessão.** Ao iniciar uma sessão, declare a trilha em que vai trabalhar. Não alterne de trilha no meio da sessão. Se a tarefa atual exigir algo de outra trilha, **pare e informe o autor**.
- **S-2 — Uma tarefa por vez**, na ordem da trilha. Marque `[x]` com a data ao concluir.
- **S-3 — O contrato é a única ponte.** Backend e frontend só se conhecem pelas specs da trilha C. O frontend **nunca** lê `backend/src/` para descobrir campos, rotas ou estados; usa apenas o contrato aprovado. O backend nunca implementa rota que não esteja num contrato aprovado.
- **S-4 — Mudança de contrato volta para a trilha C.** Se o backend ou o frontend descobrir que o contrato precisa mudar, pare, abra uma tarefa `CT-` de revisão e espere a aprovação. Nunca ajuste o contrato "por dentro" do código.
- **S-5 — O frontend não decide segurança.** Autorização de entrada, aceitação de peso e acionamento de cancela são sempre do backend (`AGENTS.md` §7.3, `AMBIENTE.md` §4.1). O frontend apenas apresenta e solicita ações.
- **S-6 — Dados falsos só tipados pelo contrato.** O frontend pode usar respostas simuladas em testes ou em desenvolvimento, desde que elas sigam exatamente os tipos do contrato aprovado. Nenhum campo é inventado.
- **S-7 — Ferramentas separadas.** Ferramentas de teste/lint/build do backend e do frontend são decididas em ADRs separados e não se misturam (`pyproject.toml` só em `backend/`, `package.json` só em `frontend/`).
- **S-8 — Docker por serviço.** Cada trilha cria só o `Dockerfile` da sua pasta. O `compose.yaml` pertence à trilha E.
- **S-9 — Cabeçalho obrigatório em toda spec e ADR:** `Trilha: Comum | Backend | Contrato | Frontend | Integração`.
- **S-10 — Relato.** Ao concluir cada tarefa, entregue o relato do `AGENTS.md` §11, a linha "Convenções" (`CONVENCOES.md` §11.7) e a linha "Trilha: X — pastas alteradas: …".
- Nada de commit, push ou exclusão de arquivos sem pedido explícito do autor (`AGENTS.md` §12).
- A numeração das features (`NNN-slug`) é atribuída na criação da pasta, em ordem sequencial. Esta lista se refere às specs pelo **slug**.

### Ordem recomendada entre trilhas

```
A (Base comum) ──► B1–B5 (backend: esqueleto, domínio, dispositivos, LPR)
                        │
                        ▼
                  C (contratos) ──► B6–B8 (backend: persistência, orquestração, API)
                        │
                        └─────────► D (frontend)  ──► E (integração)
```

- A trilha **D** só começa depois de **FE-001 e FE-002** (decisões do frontend) e **pelo menos um contrato aprovado** (trilha C).
- Backend (B6–B8) e frontend (D) podem avançar em paralelo **em sessões diferentes**, porque ambos dependem só do contrato.
- A trilha **E** só começa quando houver ao menos um fluxo implementado nos dois lados.

---

## Trilha A — Base comum (`C-`)

Pastas permitidas: `specs/`, `docs/decisoes/`, `AMBIENTE.md`, `CONVENCOES.md`. **Nenhum código.**

### [x] C-000 — Leitura obrigatória e relatório de entendimento 🔒 — concluída 2026-10-29
- **Ler:** `AGENTS.md`, `AMBIENTE.md`, `CONVENCOES.md`, `docs/modelo-dados/schema.sql`, artigo do TCC (se estiver no repositório; senão, pedir ao autor), e a seção 0 deste arquivo.
- **Fazer:** resumir em até uma página: objetivo e escopo (o agendamento é **manual**); fluxo operacional (`AMBIENTE.md` §2); segurança operacional (`AGENTS.md` §7); tecnologias **[DEFINIDO]** e decisões **[PENDENTE]**; fluxo SDD; as cinco trilhas e as regras S-1 a S-10.
- **Saída:** resumo no chat; nenhum arquivo criado.

### [x] C-001 — Inventário real do repositório — concluída 2026-10-29
- **Ler:** `AGENTS.md` §1, `AMBIENTE.md` §0.2, `CONVENCOES.md` §2.
- **Fazer:** listar o que **realmente existe** (arquivos, pastas, histórico Git). Classificar cada item como "existe", "documentado mas não existe" ou "existe mas não documentado".
- **Atenção:** o `docs/modelo-dados/schema.sql` existe, mas o `AMBIENTE.md` §0.2 diz que não há esquema (tratado na C-002).

### [x] C-002 — Divergências entre `docs/modelo-dados/schema.sql` e os documentos 🔒 — concluída 2026-10-29
- **Ler:** `docs/modelo-dados/schema.sql`, `AGENTS.md` §7, `AMBIENTE.md` §2, §8, §11–§13, `CONVENCOES.md` §6, §10, P-10.
- **Fazer:** apresentar ao autor as divergências abaixo (e outras encontradas), no formato do `AGENTS.md` §6. **Não editar o `docs/modelo-dados/schema.sql`** (exceção já feita a pedido do autor: mudança de local e de nomenclatura, item 11).

| # | Divergência observada | Documento afetado |
|---|---|---|
| 1 | `docs/modelo-dados/schema.sql` existe e é PostgreSQL 12+, mas o banco (D-01) está **[PENDENTE]** e o AMBIENTE diz que não há esquema. | AMBIENTE §0.2, §13, §15 |
| 2 | `peso_liquido_kg` gerado já fixa a regra (CARGA = final − inicial; DESCARGA = inicial − final), mas Q-02 está aberta. | AMBIENTE §2, Q-02 |
| 3 | `pesagem.agendamento_id UNIQUE`: uma única pesagem por agendamento. Confirmar a regra (inclusive após cancelamento). | Q-02, Q-13 |
| 4 | `pesagem.situacao` tem só 4 valores; a máquina de estados proposta tem estados de falha e de intervenção manual. | AMBIENTE §2.1, AGENTS §7.1.5 |
| 5 | `evento_cancela.sucesso` é booleano; não representa "estado desconhecido". | AGENTS §7.1.3, §7.2 |
| 6 | `leitura_placa.resultado` não distingue baixa confiança, formato inválido nem múltiplos candidatos; faltam `placa_normalizada` e `roi`. | AGENTS §7.2, AMBIENTE §9.2, §10.1, CONVENCOES §10 |
| 7 | Parâmetros seriais e `simulada` estão em tabelas, mas o AMBIENTE prevê configuração por variáveis de ambiente com modo `SIMULADO` padrão. Qual é a fonte de verdade? | AMBIENTE §8, CONVENCOES §7.1, AGENTS §7.3 |
| 8 | `endereco_ip` em `balanca`/`cancela`: há equipamentos por rede, além de RS232? | AMBIENTE §11, Q-01 |
| 9 | `usuario.perfil` em (`ADMINISTRADOR`, `OPERADOR`) antecipa parte de D-04 / Q-11. | AMBIENTE §15 |
| 10 | `log_sistema.origem` não tem origem para orquestração nem para intervenção manual. | AGENTS §7.1.6 |
| 11 | ~~O `schema.sql` estava na raiz; o `CONVENCOES.md` P-10 prevê `docs/modelo-dados/schema.sql`.~~ **Resolvido (2026-10-29):** movido para `docs/modelo-dados/schema.sql` e nomenclatura ajustada ao `CONVENCOES.md` §1/§6, a pedido do autor, sem mudança de regras. | CONVENCOES §2 |

- **Pronto quando:** o autor decidir o status do `docs/modelo-dados/schema.sql` (referência a revisar ou base aprovada) (a mudança de local já foi feita, item 11). Atualizar `AMBIENTE.md` §0.2, §0.3 e §15 só após aprovação.

Divergências adicionais encontradas pelo agente:

| # | Divergência observada | Documento afetado |
|---|---|---|
| 12 | `evento_cancela` e `log_sistema` não registram o usuário responsável (ação manual sem autor). | AGENTS §7.1.6 |
| 13 | Instantes em `TIMESTAMP` sem fuso; auditoria ambígua. | AGENTS §7.1.6 |
| 14 | `leitura_placa.confianca NUMERIC(5,2)` sem escala definida (0–1 ou 0–100). | AMBIENTE §8 (limiar) |
| 15 | `pesagem` repete `veiculo_id`, `motorista_id`, `placa`, `tipo_operacao` do agendamento (fotografia ou redundância?). | AMBIENTE §12 |
| 16 | `veiculo.tara_kg` cadastral não pode substituir peso medido sem regra aprovada. | AGENTS §7.2 |
| 17 | `pesagem.numero UNIQUE` sem mecanismo de geração (risco com concorrência). | AMBIENTE R-11 |
| 18 | Arquivo legado `nota_fiscal.py` sugere nota fiscal como "documento" (escopo). | AMBIENTE Q-03 |

**Resultado (2026-10-29):** decisões do autor registradas em `AMBIENTE.md` §0.4:
- item 1 → PostgreSQL **[DEFINIDO]**; `schema.sql` é referência **[PROPOSTA]**;
- item 3 → nova pesagem permitida após `CANCELADA` **[DEFINIDO]**;
- item 7 → banco cadastra, variáveis de ambiente configuram modo/comunicação **[DEFINIDO]**;
- item 18 → **[PENDENTE]** (Q-03).

Recomendações do agente, **[PROPOSTA]** a tratar na spec indicada. A situação de cada item está no `AMBIENTE.md` §0.4:

| # | Recomendação | Spec |
|---|---|---|
| 2 | Regra do peso líquido explícita e testada no domínio; banco pode manter coluna gerada com teste de coerência. | BE-202, BE-502 |
| 4 | Estados definidos primeiro na máquina de estados; esquema se ajusta. | BE-201, BE-502 |
| 5 | Trocar `sucesso` por `resultado` (`CONFIRMADO`, `FALHA`, `SEM_CONFIRMACAO`). | BE-301, BE-502 |
| 6 | Campos de leitura (`placa_normalizada`, `roi`, motivos de rejeição) definidos no LPR/placa. | BE-203, BE-401 |
| 8 | Manter `endereco_ip` só se Q-01 confirmar equipamento de rede. | BE-301 |
| 9 | Perfis ficam **[PROPOSTA]** até CT-001. | CT-001 |
| 10, 12 | Acrescentar origens de orquestração/intervenção manual e usuário responsável nos eventos. | BE-502 |
| 13 | Usar `TIMESTAMPTZ`. | BE-502 |
| 14 | Fixar escala da confiança. | BE-401 |
| 15 | Tratar como fotografia intencional, com regra de coerência. | BE-502 |
| 16 | Proibir uso da tara cadastral como peso medido sem regra aprovada. | BE-202 |
| 17 | Gerar `numero` por sequência no banco. | BE-502 |

### [x] C-003 — Aprovar convenções, trilhas e estrutura de specs 🔒 — concluída 2026-10-29
- **Fazer:** perguntar ao autor se o `CONVENCOES.md` pode ser aprovado (fecha D-10), se a estrutura `specs/` + `docs/decisoes/` pode ser criada e se a divisão em trilhas desta lista está aprovada.

### [x] C-101 — Índice e glossário — concluída 2026-10-29
- **Fazer:** criar `specs/README.md` (índice com colunas **Trilha** e **Status** para specs e ADRs, mais perguntas em aberto) e `specs/glossario.md` (termos do domínio com os identificadores exatos do `CONVENCOES.md` §10).

### [x] C-102 — Requisitos consolidados (`specs/requisitos.md`) 🔒 — concluída 2026-10-29
- **Ler:** artigo (seções 1, 2, 3.5 e 4), `AMBIENTE.md` §1, §2, §10, §14.4.
- **Fazer:** RF, RNF e RN com IDs estáveis e origem (**[ARTIGO]** ou decisão do autor). Cada requisito recebe a coluna **Lado**: `Backend`, `Frontend` ou `Ambos`. Itens ambíguos apontam para a pergunta Q-xx. Os 7 cenários de validação do artigo (`AMBIENTE.md` §14.4) ficam ligados a requisitos.

### [ ] C-103 — Rodada de perguntas bloqueantes
- **Fazer:** apresentar as perguntas do `AMBIENTE.md` §17 agrupadas por quem bloqueiam:
  - **Domínio do backend:** Q-02, Q-04, Q-10, Q-13.
  - **Dispositivos reais:** Q-01, Q-05, Q-07.
  - **LPR e dados de teste:** Q-06, Q-08, Q-09.
  - **Frontend e acesso:** Q-05 (orientação de posicionamento na tela?), Q-11.
  - **Podem esperar:** Q-03, Q-12.
- **Saída:** respostas registradas em `specs/requisitos.md` e `AMBIENTE.md` §17.
- **Andamento:** perguntas apresentadas ao autor em 2026-10-29. Respondidas e registradas no mesmo dia: Q-02, Q-04, Q-10 e Q-13 (alterações em `specs/requisitos.md` aprovadas). Reapresentadas em 2026-11-04. Respondidas nessa data: Q-05, Q-11 e Q-17. Parcial: Q-06 (câmeras na frente, atrás e superior; faltam tipo, resolução e uso das câmeras da frente e de trás). Parcial, na mesma data: Q-08 (falta a adequação à LGPD). Parcial pelas specs: Q-01 (spec 004), Q-03 (`codigo_nota`, RF-033), Q-09 (spec 005) e Q-12 (uma balança por enquanto, spec 006). Ainda sem resposta: Q-07.

### [x] C-104 — Sincronizar `CONVENCOES.md` e glossário com as specs 002 a 005 🔒 — concluída 2026-11-02
- **Origem:** pendências registradas nos relatos da BE-302 e da BE-402 (2026-10-29 e 2026-10-30).
- **Fazer:** atualizar a árvore da §2, os cenários da §4.4, a regra de exceções da §4.5, a §9 (testes, D-11 já decidido) e o glossário (§10 e `specs/glossario.md`) com o que as specs aprovadas já definiram. Nenhuma regra nova sem aprovação.

### [x] C-201 — ADR-0001: banco de dados (D-01) 🔒 — concluída 2026-10-29
- **Fazer:** `docs/decisoes/ADR-0001-banco-de-dados.md` (Trilha: Comum) com opções, critérios e consequências (`AMBIENTE.md` §13). Registrar que o `docs/modelo-dados/schema.sql` foi escrito para PostgreSQL. Não instalar nada.

### [x] C-202 — ADR-0002: monólito modular vs. serviços (D-07) 🔒 — concluída 2026-10-29
- **Fazer:** registrar a recomendação preliminar (monólito modular) e as consequências para Docker e portas seriais (R-05).

---

## Trilha B — Backend (`BE-`)

Pastas permitidas: `backend/` e specs/ADRs com `Trilha: Backend`. **Nunca tocar em `frontend/`.**
Regras de camadas: `CONVENCOES.md` P-4 a P-7 (`dominio/` sem I/O; só `dispositivos/` importa `serial`; só `lpr/` importa `cv2`/`easyocr`).

### B1 — Decisões do backend

#### [x] BE-001 — ADR de ferramentas do backend: teste, lint, formatação, tipagem (D-11, parte backend) 🔒 — concluída 2026-10-29
- **Depende de:** trilha A concluída.
- **Ler:** `AGENTS.md` §8, §10, §10.1, `CONVENCOES.md` §9.
- **Fazer:** opções com prós e contras, licença e justificativa. Escopo **apenas Python/backend**.

### B2 — Esqueleto

#### [x] BE-101 — Spec e plano `esqueleto-backend` 🔒 — concluída 2026-10-29
- **Depende de:** BE-001, C-202.
- **Resultado:** `specs/features/001-esqueleto-backend/` aprovada em 2026-10-29 (Python ≥ 3.12; sem build backend).
- **Fazer:** o mínimo para rodar testes do domínio: `backend/pyproject.toml`, `backend/src/pesagem/__init__.py`, `backend/src/pesagem/dominio/`, `backend/tests/unitarios/`. Nenhuma rota, banco ou Docker ainda. Toda dependência justificada (`AGENTS.md` §10.1).

#### [x] BE-102 — Implementar o esqueleto — concluída 2026-10-29
- **Fazer:** criar só o que a spec cobre; nenhuma pasta vazia "para o futuro".
- **Verificar:** executar o comando de testes definido na BE-001 e relatar a saída real.

### B3 — Domínio (puro, sem I/O)

#### [x] BE-201 — Spec `maquina-estados-operacao` 🔒 — concluída 2026-11-04
- **Ler:** `AMBIENTE.md` §2, §2.1; `AGENTS.md` §7; respostas de Q-02, Q-04, Q-13; C-002 (itens 3, 4, 5).
- **Fazer:** estados, eventos, transições válidas e rejeitadas (registradas, nunca "corrigidas"), falhas, intervenção manual, retomada após reinício, concorrência. Valores em `UPPER_SNAKE_CASE`. Apontar o que o `docs/modelo-dados/schema.sql` precisaria mudar, sem alterá-lo.
- **Andamento:** spec 006 aprovada pelo autor em 2026-11-04, com P-1 a P-8 respondidas.

#### [x] BE-202 — Spec `regras-pesagem` 🔒 — concluída 2026-10-29
- **Resultado:** `specs/features/002-regras-pesagem/spec.md` aprovada (estabilidade pelo software; registra a última leitura; parâmetros sem valor padrão, exceto a tolerância de 20 kg).
- **Fazer:** aceitação de leitura de peso (bem formada, dentro de faixa, estável; parâmetros vindos de configuração) e cálculo do peso líquido por tipo de operação, incluindo resultado negativo ou nulo.

#### [x] BE-203 — Spec `normalizacao-placa` 🔒 — concluída 2026-10-29
- **Resultado:** `specs/features/003-normalizacao-placa/spec.md` aprovada (8 pares de correção, chave de comparação antiga ↔ Mercosul, separadores espaço/hífen/ponto).
- **Fazer:** formatos aceitos (Q-10), correções explícitas de confusões de OCR por posição do caractere, casos rejeitados.

#### [x] BE-211 — Implementar `dominio/placa/` (spec `normalizacao-placa`) — concluída 2026-10-29 (aceita pelo autor em 2026-10-29)
#### [x] BE-212 — Implementar `dominio/pesagem/` (spec `regras-pesagem`) — concluída 2026-10-29 (aceita pelo autor em 2026-10-29)
#### [x] BE-213 — Implementar `dominio/operacao/` (spec `maquina-estados-operacao`) — concluída 2026-11-04 (aceita pelo autor em 2026-11-04)
- Testes ligados aos `CA-`, cobrindo caminho normal, falhas do `AGENTS.md` §7.2 e casos-limite, executados e relatados. Ao final, spec → `Implementada`. 🔒 aceite do autor.

### B4 — Dispositivos (simulados primeiro)

#### [x] BE-301 — Spec `camada-dispositivos` 🔒 — concluída 2026-10-29
- **Resultado:** `specs/features/004-camada-dispositivos/spec.md` aprovada (interfaces assíncronas; falhas como resultados; segunda tentativa só sem resposta; estado da cancela pelo sensor; simulado como padrão e `REAL` indisponível; protocolos de balança por modelo, RF-030).
- **Ler:** `AMBIENTE.md` §11, §14.2; `AGENTS.md` §7.3; `CONVENCOES.md` §4.4; C-002 (item 7).
- **Fazer:** interfaces `Balanca` e `Cancela`; `BalancaSimulada`/`CancelaSimulada` com cenários (`ESTAVEL`, `INSTAVEL`, `TIMEOUT`, `QUADRO_CORROMPIDO`, `SEM_RESPOSTA`); timeouts; estado desconhecido da cancela; modo `SIMULADO` como padrão. `BalancaSerial`, `CancelaSerial` e `parser_quadro.py` ficam **bloqueados** até Q-01 ter resposta e haver quadros reais em `docs/equipamentos/`.

#### [x] BE-302 — Implementar interfaces e simuladores — concluída 2026-10-29 (aceita pelo autor em 2026-10-29)

### B5 — LPR

#### [x] BE-401 — Spec `pipeline-lpr` 🔒 — concluída 2026-10-29
- **Resultado:** `specs/features/005-pipeline-lpr/spec.md` aprovada (fonte por pasta; localização com OpenCV; candidatos separados; confiança de 0 a 1 truncada; limiar obrigatório; seleção conservadora; avaliação fora da execução padrão; acervo real fora do repositório).
- **Ler:** `AMBIENTE.md` §9, §14.3; `CONVENCOES.md` §2, §9; respostas de Q-06, Q-08, Q-09.
- **Fazer:** fonte de imagem substituível (pasta de imagens primeiro), resultado estruturado, limiar de confiança vindo de configuração, formato do `gabarito.csv`, métricas (peso maior para falso positivo de autorização), OCR atrás da fronteira `LeitorPlaca`.

#### [x] BE-402 — Implementar o pipeline com fonte de pasta de imagens — concluída 2026-10-30 (aceita pelo autor em 2026-11-02)
- Testes reprodutíveis sem câmera.

> **Pausa da trilha B.** Antes de seguir para B6, os contratos da trilha C que o backend vai implementar precisam estar aprovados.

### B6 — Persistência

#### [ ] BE-501 — ADR de ORM e migrações (D-02) 🔒
- **Depende de:** C-201 aceito.

#### [ ] BE-502 — Spec `persistencia` 🔒
- **Fazer:** revisar o `docs/modelo-dados/schema.sql` à luz das specs BE-201 a BE-203, BE-301 e BE-401 e das respostas da C-002; definir repositórios por agregado (`CONVENCOES.md` §2). Testes de persistência contra o mesmo motor de execução (`AGENTS.md` §8).
- **Alterações já levantadas:** spec 004 §11 (`evento_cancela`), spec 006 §12 (situações, reserva da balança, eventos de transição), spec 007 §9, spec 008 §9, ADR-0004 §5 (sessão, perfis, `criado_por`, `codigo_nota`) e RN-022 (onde guardar as imagens das decisões).

#### [ ] BE-503 — Implementar persistência e primeira migração

### B7 — Orquestração

#### [ ] BE-601 — Spec `orquestracao-operacao` 🔒
- **Fazer:** como o domínio, o LPR, os dispositivos e a persistência se coordenam em cada passo do fluxo (`AMBIENTE.md` §2), incluindo execução sem bloquear a API (D-05, ADR na própria spec ou separado).
- **Pontos já levantados:** fonte de posição com simulador (RF-027, spec 006 §12), análise contínua com limite de idade da imagem (RF-034, ADR-0005 §4.1), retomada, reserva da balança e liberação de caminhão cancelado (spec 006 §6.3, §6.4, §7.2), RN-014 com o fuso do pátio (spec 008 §6.1) e o que fazer se falhar a gravação de uma imagem de decisão (RN-022, ainda sem decisão).

#### [ ] BE-602 — Implementar a orquestração com dispositivos e LPR simulados

### B8 — API (implementa os contratos da trilha C)

Cada tarefa implementa **exatamente** um contrato aprovado. Nada além do contrato (S-3).

#### [ ] BE-701 — API de cadastros (contrato `contrato-api-cadastros`)
#### [ ] BE-702 — API de agendamentos (contrato `contrato-api-agendamentos`)
#### [ ] BE-703 — API da operação em tempo real (contrato `contrato-api-operacao`)
#### [ ] BE-704 — API de histórico (contrato `contrato-api-historico`)
#### [ ] BE-705 — API de diagnóstico e dispositivos (contrato `contrato-api-diagnostico`)
#### [ ] BE-706 — API de autenticação e usuários (contrato `contrato-api-autenticacao`)
#### [ ] BE-707 — API de autoatendimento (contrato `contrato-api-autoatendimento`)
- Testes de integração (API + banco + dispositivos simulados) citando os `CA-` do contrato.

### B9 — Container do backend

#### [ ] BE-801 — Spec e implementação do `backend/Dockerfile` 🔒
- **Fazer:** apenas o Dockerfile do backend; volumes para modelos do EasyOCR (D-08) e modo `SIMULADO` como padrão. O `compose.yaml` é da trilha E.

---

## Trilha C — Contratos de API (`CT-`)

Pastas permitidas: specs com `Trilha: Contrato` e ADRs transversais. **Nenhum código em `backend/` nem em `frontend/`.**
Esta trilha é a **única ponte** entre backend e frontend (S-3, S-4).

### [x] CT-001 — ADR de autenticação e perfis (D-04) 🔒 — concluída 2026-11-04
- **Ler:** `AMBIENTE.md` §10.2, §15; resposta de Q-11; C-002 (item 9).
- **Fazer:** decisão transversal que afeta o backend (validação) e o frontend (login, sessão, telas por perfil).
- **Resultado:** ADR-0004 aceito pelo autor em 2026-11-04.

### [x] CT-002 — ADR de atualização em tempo real (D-06) 🔒 — concluída 2026-11-04
- **Fazer:** como a tela operacional e o diagnóstico recebem eventos e imagens (polling, SSE, WebSocket, snapshots). Opções com prós e contras para os **dois** lados.
- **Resultado:** ADR-0005 aceito pelo autor em 2026-11-04.

### [ ] CT-101 a CT-107 — Specs de contrato 🔒 (uma por tarefa)

| Tarefa | Spec | Cobre | Depende de |
|---|---|---|---|
| CT-101 | `contrato-api-cadastros` | veículos, motoristas, transportadoras, tipos de veículo e produtos | C-102, CT-001 |
| CT-102 | `contrato-api-agendamentos` | criação **manual**, consulta, edição, cancelamento, faixas de horário | C-102, Q-13 |
| CT-103 | `contrato-api-operacao` | estado atual da operação, placa reconhecida, peso lido, etapa, comandos de cancela solicitados pelo operador, intervenção manual | BE-201, CT-002 |
| CT-104 | `contrato-api-historico` | consulta de pesagens, peso líquido, eventos | BE-202 |
| CT-105 | `contrato-api-diagnostico` | imagens, ROIs, interpretações do LPR, estado dos dispositivos, indicação de modo real/simulado | BE-301, BE-401, CT-002 |
| CT-106 | `contrato-api-autenticacao` | login, logout, usuário atual com permissões, gestão de usuários (RF-032) | CT-001 |
| CT-107 | `contrato-api-autoatendimento` | criação de agendamento pelo motorista, sem login (RF-033, RN-021) | CT-001, CT-102 |

Cada contrato define, sem código:
- rotas conforme `CONVENCOES.md` §5 (prefixo `/api`, recursos no plural em kebab-case);
- campos JSON em `snake_case`, com unidades (`_kg`, `_em`), idênticos ao domínio;
- valores de estado em `UPPER_SNAKE_CASE`, idênticos às specs do domínio;
- respostas de erro e de falha (o que a tela recebe quando a balança falha, a placa é inconclusiva etc.);
- quais ações exigem quais perfis (CT-001);
- critérios de aceitação verificáveis pelos **dois** lados.

**Andamento:** CT-101 concluída em 2026-11-04 (spec 007, aprovada pelo autor). CT-102 concluída em 2026-11-04 (spec 008, aprovada pelo autor).

### [ ] CT-9xx — Revisão de contrato (sob demanda)
- Aberta quando backend ou frontend encontrar algo que o contrato não cobre (S-4). Atualizar a spec, obter aprovação 🔒 e só então voltar às trilhas B ou D.

---

## Trilha D — Frontend (`FE-`)

Pastas permitidas: `frontend/` e specs/ADRs com `Trilha: Frontend`. **Nunca tocar em `backend/`, nem ler `backend/src/` para descobrir campos (S-3).**
Regras: `CONVENCOES.md` §8 (TypeScript, Tailwind, campos da API em `snake_case` sem conversão). Nenhuma decisão de segurança no frontend (S-5).

### D1 — Decisões do frontend

#### [ ] FE-001 — ADR do framework do frontend (D-03) 🔒
- **Ler:** `AMBIENTE.md` §3, §10; `CONVENCOES.md` §8.
- **Fazer:** opções compatíveis com TypeScript + Tailwind **[DEFINIDO]**, com prós e contras, licença e impacto em Docker. Se o framework impuser convenções próprias, propor a atualização do `CONVENCOES.md` §8 no mesmo ADR.

#### [ ] FE-002 — ADR de ferramentas do frontend: teste, lint, formatação, TypeScript estrito (D-11, parte frontend) 🔒
- Escopo **apenas frontend**. Independente da BE-001.

### D2 — Esqueleto

#### [ ] FE-101 — Spec e plano `esqueleto-frontend` 🔒
- **Depende de:** FE-001, FE-002.
- **Fazer:** estrutura mínima em `frontend/src/` (`paginas/`, `componentes/`, `api/`, `tipos/`, `estilos/`, conforme `CONVENCOES.md` §2), configuração de build e de testes, layout base com indicação visível do modo (real/simulado — `AMBIENTE.md` §10.1 item 7). Sem telas de negócio ainda.

#### [ ] FE-102 — Implementar o esqueleto
- **Verificar:** executar build e testes definidos na FE-002 e relatar a saída real.

### D3 — Tipos e cliente da API

#### [ ] FE-201 — Tipos e cliente HTTP a partir de um contrato aprovado
- **Depende de:** o contrato correspondente (CT-101 a CT-107) aprovado.
- **Fazer:** em `frontend/src/tipos/` e `frontend/src/api/`, tipos que espelham **exatamente** o contrato e um cliente HTTP. Respostas simuladas para desenvolvimento e testes só com esses tipos (S-6).
- Repetir esta tarefa (FE-201a, FE-201b, …) para cada contrato aprovado.

### D4 — Telas

Cada tela tem dois passos: **spec da tela** 🔒 (Trilha: Frontend; comportamento, estados de carregamento/erro/falha, perfis, critérios de aceitação) e depois **implementação** com testes.

| Tarefa | Tela | Contrato usado | Observações |
|---|---|---|---|
| FE-301 | Cadastros (veículos, motoristas, transportadoras, tipos de veículo, produtos) | `contrato-api-cadastros` | — |
| FE-302 | Agendamentos (criação **manual**) e faixas de horário | `contrato-api-agendamentos` | Nada de agendamento automático (`AGENTS.md` §12). |
| FE-303 | Tela operacional em tempo real | `contrato-api-operacao` | Estados de falha claros e inequívocos; comandos só solicitam, quem decide é o backend (S-5). |
| FE-304 | Histórico e auditoria | `contrato-api-historico` | — |
| FE-305 | Diagnóstico de visão computacional (imagens, ROIs, interpretações) | `contrato-api-diagnostico` | Respeitar a política de privacidade/retenção (Q-08). |
| FE-306 | Estado dos dispositivos e intervenção manual | `contrato-api-diagnostico`, `contrato-api-operacao` | Intervenção sempre rastreável; permissões conforme CT-001. |
| FE-307 | Autoatendimento do motorista (RF-033), sem login | `contrato-api-autoatendimento` | Nunca mostra dados do cadastro (RN-021). |
| FE-308 | Login e gestão de usuários (RF-032) | `contrato-api-autenticacao` | Não guarda credencial em JavaScript (ADR-0004). |

- Ordem sugerida: FE-308 → FE-301 → FE-302 → FE-307 → FE-304 → FE-303 → FE-305 → FE-306 (das telas mais simples para as de tempo real; as protegidas dependem do login).
- Se a tela precisar de um dado que o contrato não tem: **pare** e abra uma CT-9xx (S-4).

### D5 — Container do frontend

#### [ ] FE-401 — Spec e implementação do `frontend/Dockerfile` 🔒
- **Fazer:** apenas o Dockerfile do frontend (desenvolvimento e build estático). O `compose.yaml` é da trilha E.

---

## Trilha E — Integração (`INT-`)

Pastas permitidas: `compose.yaml`, `.env.exemplo`, `README.md`, `backend/tests/ponta_a_ponta/`. **Não altera a lógica de `backend/src/` nem de `frontend/src/`**; se encontrar defeito, abre tarefa na trilha correta.

#### [ ] INT-001 — Spec e implementação do `compose.yaml` 🔒
- **Depende de:** BE-801, FE-401, C-201.
- **Fazer:** serviços `backend`, `frontend`, `db`; volumes `pesagem-dados-db` e `pesagem-modelos-ocr`; perfis `dev`, `teste`, `hardware-real` (`CONVENCOES.md` §7.2); `.env.exemplo` com todas as variáveis `PESAGEM_<GRUPO>_<NOME>`, sem segredos e com modo `SIMULADO` padrão; HTTPS (ADR-0004) e proxy sem buffer na rota de eventos (ADR-0005).

#### [ ] INT-002 — Testes ponta a ponta com simuladores
- **Fazer:** os 7 cenários do artigo (`AMBIENTE.md` §14.4) mais as falhas do `AGENTS.md` §7.2, do agendamento manual ao peso líquido, sem hardware real.

#### [ ] INT-003 — README de instalação, configuração e execução em modo simulado
- **Fazer:** documentação básica **[ARTIGO]**, só com comandos realmente testados nesta sessão. Licença (D-12) apenas com decisão do autor.

---

## Checklist rápido antes de encerrar qualquer tarefa

- [ ] A tarefa pertence a uma única trilha e só alterou as pastas permitidas dela.
- [ ] Backend e frontend se comunicaram apenas por contratos aprovados (nada lido do código do outro lado).
- [ ] A tarefa está ligada a um requisito e a uma spec aprovada (ou é tarefa de documentação/decisão).
- [ ] Nenhum item **[PENDENTE]** foi decidido sem o autor; nenhuma **[PROPOSTA]** virou **[DEFINIDO]** por conta própria.
- [ ] Nada foi inventado (protocolos, versões, números, limiares, campos, rotas).
- [ ] Testes relevantes executados nesta sessão, com saída relatada — ou declarado "não executado".
- [ ] `AMBIENTE.md`, specs, ADRs e `specs/README.md` afetados atualizados na mesma mudança.
- [ ] Relato do `AGENTS.md` §11 com as linhas "Convenções" e "Trilha".
