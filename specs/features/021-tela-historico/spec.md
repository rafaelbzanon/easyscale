# Spec 021 — Tela de histórico e auditoria

- **Trilha:** Frontend
- **Status:** Implementada (FE-304, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-304 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-016, RF-018, RF-019, RF-020, RN-006, RN-009, RN-011, RN-022, RNF-010, RNF-013, RNF-014
- **Decisões:** ADR-0004 (os três perfis têm `CONSULTAR_OPERACAO`)
- **Contratos usados:** spec 010 inteira; spec 009 §5.1 (objeto Pesagem, item da lista); spec 006 §5 (eventos e situações)

---

## 1. Contexto e origem

- O histórico serve à auditoria: o que aconteceu com cada pesagem, quando, por quem e por quê. Só consulta. Nada aqui muda uma operação (spec 010 §6.1).
- Administrador, operador e auditor veem o mesmo conteúdo, sem CPF (spec 010 §7).
- Não há canal de eventos: a tela é uma leitura do momento da consulta (spec 010 §6.2). Ela diz isso.

## 2. Objetivo

Listar as pesagens (abertas e encerradas) com filtros e mostrar os eventos de cada uma na ordem em que aconteceram, sem esconder falha e sem mostrar falha como sucesso.

## 3. Fora de escopo

- Tempo real, ações manuais e item da pesagem (spec 022).
- Imagens, ROIs e leituras de placa (spec 023). Os eventos só mostram o número da imagem ou da leitura, sem buscá-las.
- Exportação, relatórios e comprovante (spec 010 §3).
- Auditoria de acesso e de cadastros.

## 4. Atores

`ADMINISTRADOR`, `OPERADOR` e `AUDITOR`. O menu "Histórico" aparece com `CONSULTAR_OPERACAO`.

## 5. Pré-condições

Sessão ativa. Rota `/historico`.

## 6. Comportamento normal

### 6.1 Lista

1. Filtros (spec 010 §5.1): data inicial, data final, abertas ou encerradas, situação, tipo, classificação, liberação manual, placa e número do agendamento. Filtro vazio não vai na consulta. A ordem é a do backend (mais recente primeiro).
2. Colunas: criada em, placa (monoespaçada), tipo, motorista, produto, situação, peso inicial, peso final, peso líquido com a classificação, liberação manual e o botão "Eventos".
3. Situação em palavra e forma: Finalizada (quadrado), Cancelada (círculo cortado), Aguardando intervenção (triângulo, com o motivo) e as demais em andamento (círculo). Os textos vêm dos mesmos nomes da spec 022.
4. Peso sem valor aparece como "—". O peso líquido aparece como veio, inclusive em `SEM_MOVIMENTACAO` (nunca trocado por zero, RN-006).
5. Abaixo do título: "Consulta feita às HH:MM:SS. Esta tela não atualiza sozinha." e o botão "Atualizar". A lista é paginada com o total.

### 6.2 Eventos de uma pesagem

1. "Eventos" abre o detalhe acima da lista: placa, tipo e situação da pesagem e a lista de `GET /api/pesagens/{id}/eventos`, do mais antigo ao mais recente, paginada.
2. Cada evento mostra: data e hora; tipo (Transição, Transição rejeitada, Registrado, Comando de cancela); o que aconteceu; quem e por quê.
   - Transição: "situação de origem → situação de destino" e o nome do evento; o motivo da intervenção, se houver.
   - Transição rejeitada: a situação em que ficou, o evento e o `motivo_rejeicao`, com o aviso "Rejeitada: nada mudou".
   - Registrado: o evento e a situação em que a pesagem ficou.
   - Comando de cancela: cancela (entrada ou saída), comando (abrir ou fechar), resultado e tentativas. `FALHA` e `SEM_CONFIRMACAO` aparecem como falha, com palavra e forma, nunca como sucesso.
   - Peso aceito: o peso e, quando houver, o líquido e a classificação (inclusive os que depois foram descartados por `TENTAR_NOVAMENTE`).
   - Motivo do dispositivo (ex.: `INSTAVEL`) aparece como veio.
3. Ação manual mostra o responsável e o motivo digitado. Evento automático mostra "Automático".
4. Número de imagem ou de leitura aparece como "Imagem da decisão nº X" e "Leitura de placa nº Y", sem buscar nada.
5. Evento ou valor que a tela não conhece aparece como veio, sem tradução.

### 6.3 Perfis

Os três perfis têm a mesma tela. Não há nenhum botão que mude dado: só "Filtrar", "Atualizar", "Eventos", paginação e "Fechar".

## 7. Comportamento em falha

| Situação | Comportamento |
|---|---|
| Carregando | "Carregando…". Sem dado antigo no lugar do novo. |
| Falha ao listar ou ao buscar eventos | Erro com "Tentar de novo". A tela não mostra a lista anterior como atual. |
| `401 NAO_AUTENTICADO` | Casca vai ao login. |
| `403 SEM_PERMISSAO` | "Você não tem permissão para esta ação." |
| `422` de filtro (ex.: `PLACA_INVALIDA`, data final antes da inicial) | Erro acima da lista, com o texto do código quando a tela o conhece. Os filtros digitados ficam. |
| `404` nos eventos | Erro; a lista é recarregada. |
| Lista vazia | "Nenhuma pesagem encontrada." / "Nenhum evento registrado." |

## 8. Regras e dados

- Tipos e chamadas: `tipos/historico.ts`, `tipos/operacao.ts` e `api/historico.ts`. Nenhum campo novo.
- A tela não recalcula peso, líquido nem classificação (spec 010 §6.1).
- Horas aparecem no fuso do navegador. O fuso do pátio é do backend (Q-F9).
- A tela não grava em `localStorage`, `sessionStorage` nem cookie.
- O `motivo` das ações manuais é texto livre e pode ter dado pessoal (spec 010 §7): aparece só nesta tela e nunca em log do navegador.

## 9. Critérios de aceitação

| CA | Critério | Como verificar |
|---|---|---|
| CA-001 | A lista mostra as colunas da §6.1, a nota de consulta e o total; "Atualizar" consulta de novo. | Teste com `fetch` simulado. |
| CA-002 | Cada filtro preenchido vai na consulta com o nome do contrato; filtro vazio não vai; filtrar volta à página 1. | Teste. |
| CA-003 | Situação aparece em palavra e forma; `AGUARDANDO_INTERVENCAO` mostra o motivo. | Teste. |
| CA-004 | Peso líquido em `SEM_MOVIMENTACAO` aparece como veio (ex.: `12.000 kg`), peso ausente aparece "—". | Teste. |
| CA-005 | "Eventos" mostra os eventos na ordem recebida, com transição, rejeição, registro e comando de cancela como na §6.2. | Teste. |
| CA-006 | `SEM_CONFIRMACAO` e `FALHA` aparecem como falha em palavra; `CONFIRMADO` como ok. | Teste. |
| CA-007 | Ação manual mostra responsável e motivo; evento automático mostra "Automático". | Teste. |
| CA-008 | `PESO_ACEITO` com peso e líquido descartados continua visível. | Teste. |
| CA-009 | Imagem e leitura aparecem só como número; nenhuma chamada a imagens ou leituras. | Teste. |
| CA-010 | Falha ao listar e ao buscar eventos mostra erro e "Tentar de novo"; `422` de placa mostra o texto do código e mantém os filtros. | Teste. |
| CA-011 | Paginação da lista e dos eventos pede a página seguinte. | Teste. |
| CA-012 | Auditor, operador e administrador veem a mesma tela, sem botão que mude dado. | Teste. |
| CA-013 | Nenhum código grava em `localStorage`, `sessionStorage` ou `document.cookie`. | `grep`. |

## 10. Impacto

- **Pastas:** `frontend/src/paginas/historico/` (novas); uma rota em `rotas.tsx`. Reaproveita `SITUACAO` e `MOTIVO_INTERVENCAO` de `paginas/operacao/textos.ts` (Loom), `IndicadorEstado` e `formatarPeso`.
- **Segurança operacional:** nenhuma ação física. A tela de auditoria não pode esconder falha nem mostrar `SEM_CONFIRMACAO` como sucesso: por isso o texto e a forma fixos.
- **Reversibilidade:** alta.

## 11. Perguntas em aberto

| ID | Pergunta | Tratamento |
|---|---|---|
| Q-F9 | O contrato não dá o fuso do pátio para exibir as horas. | A tela usa o fuso do navegador. Os filtros de data usam o fuso do pátio no backend, então perto da meia-noite a hora mostrada pode ficar em outro dia. |
