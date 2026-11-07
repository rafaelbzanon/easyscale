# Spec 019 — Tela de agendamentos e faixas de horário

- **Trilha:** Frontend
- **Status:** Implementada (FE-302, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-302 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-004, RF-005, RF-028, RF-029, RN-001, RN-013, RN-014, RN-015, RN-023, RN-024, RNF-013, RNF-014
- **Decisões:** ADR-0004 (permissões; o frontend só esconde, o backend decide)
- **Contratos usados:** spec 008 inteira; spec 007 §5 (listas de escolha: veículos, motoristas, transportadoras, produtos); spec 012 §5.2 (permissões)

---

## 1. Contexto e origem

- Criar agendamento é sempre uma ação humana (RN-001, `AGENTS.md` §12). A tela nunca cria sozinha, nem em lote.
- O contrato 008 dá a disponibilidade das faixas e diz que "a tela apresenta a primeira faixa com vaga como sugestão, e quem agenda confirma" (§5.3).
- `ADMINISTRADOR`: consulta, cria, edita e cancela; consulta e altera faixas. `OPERADOR`: consulta e cria; vê as faixas. `AUDITOR`: só consulta agendamentos, sem acesso às faixas (spec 008 §4.3).

## 2. Objetivo

Uma tela para listar e filtrar agendamentos, criar (manual), editar, cancelar com motivo, e manter as faixas de horário.

## 3. Fora de escopo

- Criação pelo motorista (spec 020).
- Qualquer criação automática ou em lote. Importar nota ou calendário (spec 008 §3).
- Decidir autorização de entrada (é do backend).

## 4. Atores

`ADMINISTRADOR`, `OPERADOR`, `AUDITOR`. O menu "Agendamentos" aparece com `CONSULTAR_AGENDAMENTOS`.

## 5. Pré-condições

Sessão ativa. Rota `/agendamentos`; a aba "Faixas de horário" (`?visao=faixas`) só aparece com `CONSULTAR_CADASTROS`.

## 6. Comportamento normal

### 6.1 Lista de agendamentos

1. Filtros: data inicial, data final, status, tipo de operação, origem e placa (spec 008 §5.1). Padrão: data inicial de hoje, para não abrir pela lista de dias passados.
2. Colunas: data, faixa (`faixa_hora_inicio`–`faixa_hora_fim`), placa (monoespaçada), motorista, transportadora, produto, tipo (Carga ou Descarga), status e origem. Só o resumo do contrato; nunca CPF.
3. Status em palavra e forma: Agendado e Em andamento (círculo), Concluído (quadrado), Cancelado (círculo cortado), Expirado (triângulo).
4. Paginada (spec 007 §3.3).

### 6.2 Criar agendamento (só com `CRIAR_AGENDAMENTO`)

1. "Novo agendamento" abre o formulário acima da lista. Campos: veículo, motorista, transportadora (opcional), produto, tipo de operação, data prevista, faixa de horário, código da nota (só em Descarga; o campo some em Carga) e observação (até 200 caracteres).
2. As listas de escolha trazem só cadastros ativos. Ao escolher o veículo, a tela pré-preenche transportadora e motorista padrão do veículo, se houver. Quem agenda confere e pode trocar (spec 008 §6.8).
3. Ao informar a data, a tela consulta a disponibilidade (`GET /api/faixas-horario/disponibilidade?data=`) e mostra cada faixa com as vagas livres. Faixa sem vaga ou encerrada fica desabilitada.
4. A primeira faixa com vaga vem **selecionada como sugestão**, com o texto "Sugerida: primeira faixa com vaga. Confira ou escolha outra." O envio leva sempre o `faixa_horario_id` escolhido, nunca vazio: a escolha da faixa é de quem agenda (RN-001, RF-029). Sem faixa com vaga, o campo fica vazio, com o aviso "Sem vaga neste dia.", e o envio não é possível.
5. Só depois da resposta de sucesso, o formulário fecha, a lista recarrega e aparece "Agendamento criado: faixa 08:00–10:00." com a faixa que o backend gravou.

### 6.3 Editar (só com `GERENCIAR_AGENDAMENTOS`, status `AGENDADO`)

- "Editar" aparece só na linha com status Agendado. O formulário é o da criação, preenchido com `GET /api/agendamentos/{id}`.
- Envia só os campos alterados (`PATCH`). Sem alteração, nada é enviado. Nunca envia `faixa_horario_id: null` (spec 008 §6.5).

### 6.4 Cancelar (só com `GERENCIAR_AGENDAMENTOS`, status `AGENDADO`)

- "Cancelar agendamento" abre um painel acima da lista: texto "Isto cancela o agendamento do veículo {placa} em {data}. A vaga da faixa é liberada.", campo "Motivo" (obrigatório, até 200 caracteres) e os botões "Confirmar cancelamento" e "Voltar". Nada é enviado sem motivo.
- Só depois do sucesso, a linha passa a Cancelado.

### 6.5 Faixas de horário

- Lista (ativas por padrão) com início, fim, capacidade e situação. Com `GERENCIAR_CADASTROS`: "Nova faixa" e "Editar".
- Campos: hora de início, hora de fim, capacidade (inteiro maior que 0) e, na edição, "Faixa ativa".
- O aviso ao desativar é o da spec 018 §6.3, trocando o texto: "Faixa inativa não recebe agendamentos novos. Os que já existem continuam válidos."
- Mudar o horário de uma faixa com agendamentos dá `409 FAIXA_COM_AGENDAMENTOS`; a tela mostra o texto "Há agendamentos nesta faixa. Desative-a e crie outra."

## 7. Comportamento em falha

| Situação | Comportamento |
|---|---|
| Carregando | "Carregando…". |
| Falha ao listar ou ao consultar a disponibilidade | Erro com "Tentar de novo". Sem disponibilidade, o envio fica bloqueado. |
| `401 NAO_AUTENTICADO` | Casca vai ao login. |
| `403 SEM_PERMISSAO` | "Você não tem permissão para esta ação." |
| `409`/`422` no envio | O formulário continua aberto com os dados. A tela mostra a mensagem do backend e, abaixo do campo que o backend indicou em `campos[].campo`, o texto curto do código (spec 008 §6.10): `DATA_NO_PASSADO`, `FAIXA_SEM_VAGA`, `FAIXA_ENCERRADA`, `SEM_FAIXA_DISPONIVEL`, `VEICULO_JA_AGENDADO`, `STATUS_NAO_PERMITE`, `CODIGO_NOTA_NAO_PERMITIDO`, `FAIXA_SOBREPOSTA`, `FAIXA_COM_AGENDAMENTOS`. A disponibilidade é consultada de novo depois de `FAIXA_SEM_VAGA`, `FAIXA_ENCERRADA` e `SEM_FAIXA_DISPONIVEL`. |
| `500`, rede caída, corpo inválido | Erro no formulário; não supõe que salvou. |
| Cancelamento recusado (`409 STATUS_NAO_PERMITE`) | O painel continua aberto com o erro; a lista é recarregada para mostrar o status atual. |
| Lista vazia | "Nenhum agendamento encontrado." |

## 8. Regras e dados

- Tipos e chamadas: `tipos/agendamentos.ts` e `api/agendamentos.ts`; listas de escolha por `api/cadastros.ts`. Nenhum campo novo.
- A tela não grava em `localStorage`, `sessionStorage` nem cookie.
- A data de hoje usada como padrão vem do relógio do navegador; o dia do pátio é do backend (spec 008 §6.1). Ver Q-F4.
- `codigo_nota` e `observacao` aparecem só no formulário de edição, não na lista (podem ter dado pessoal, spec 008 §7).

## 9. Critérios de aceitação

| CA | Critério | Como verificar |
|---|---|---|
| CA-001 | A lista mostra o resumo do agendamento, o status em palavra e filtra por data inicial de hoje, status, tipo, origem e placa. | Teste com `fetch` simulado. |
| CA-002 | Auditor vê a lista e nenhum botão de criar, editar ou cancelar, nem a aba de faixas. Operador cria, mas não edita nem cancela. | Teste com sessões. |
| CA-003 | Ao informar a data, consulta a disponibilidade; a primeira faixa com vaga vem selecionada e com o texto de sugestão; faixa cheia ou encerrada fica desabilitada. | Teste. |
| CA-004 | O envio leva o `faixa_horario_id` escolhido (nunca vazio) e só depois da resposta mostra a faixa gravada. | Teste. |
| CA-005 | Sem faixa com vaga, aparece "Sem vaga neste dia." e o envio não acontece. | Teste. |
| CA-006 | Escolher veículo pré-preenche transportadora e motorista padrão; o usuário pode trocar. | Teste. |
| CA-007 | `codigo_nota` só aparece em Descarga; em Carga não é enviado. | Teste. |
| CA-008 | `409 VEICULO_JA_AGENDADO`, `FAIXA_SEM_VAGA` e `422 DATA_NO_PASSADO` mantêm o formulário e mostram o texto do código; `FAIXA_SEM_VAGA` consulta a disponibilidade de novo. | Teste. |
| CA-009 | `403`, `500` e rede caída no envio mostram erro e não fecham o formulário. | Teste. |
| CA-010 | Editar só aparece em `AGENDADO` para quem gerencia; o `PATCH` leva só o alterado; sem alteração, nada é enviado. | Teste. |
| CA-011 | Cancelar exige motivo; mostra o efeito; envia `POST .../cancelar` com o motivo; `409` mantém o painel e recarrega a lista. | Teste. |
| CA-012 | Faixas: lista, cria, edita e desativa com aviso; sem `GERENCIAR_CADASTROS` não há botões; `409 FAIXA_COM_AGENDAMENTOS` mostra o texto. | Teste. |
| CA-013 | Nenhum código grava em `localStorage`, `sessionStorage` ou `document.cookie`. | `grep`. |

## 10. Impacto

- **Pastas:** `frontend/src/paginas/agendamentos/` (novas); uma rota em `rotas.tsx`; `listar-todos.ts` e o mapa de textos de código em `frontend/src/` (partes da spec 018 passam a usá-los).
- **Segurança operacional:** nenhuma ação física. O agendamento é uma das condições da autorização (RN-002): por isso a faixa nunca é escolhida sem confirmação, e a tela só mostra o que o backend confirmou.
- **Reversibilidade:** alta.

## 11. Perguntas em aberto

| ID | Pergunta | Tratamento |
|---|---|---|
| Q-F4 | O contrato não informa o "hoje" do pátio (`PESAGEM_PATIO_FUSO`). | A tela usa a data do navegador como padrão; o backend valida (`DATA_NO_PASSADO`). Se o navegador estiver em outro fuso, perto da meia-noite o padrão pode divergir. Pedir um campo de data do pátio à Quill se importar. |
| Q-F5 | O contrato não diz o nome do `campo` em `campos[]` para os códigos da §6.10. | Resolvida na verificação com o backend real: ele manda o nome do campo da requisição (ex.: `faixa_horario_id` com `FAIXA_ENCERRADA`, `hora_inicio` com `FAIXA_SOBREPOSTA`). A tela usa esse nome. Pedir à Quill que registre isso no contrato. |
