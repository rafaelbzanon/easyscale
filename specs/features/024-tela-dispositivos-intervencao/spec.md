# Spec 024 — Tela de dispositivos, intervenção e liberação de entrada

- **Trilha:** Frontend
- **Status:** Implementada (FE-306, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-306 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-021, RF-023, RN-003, RN-007, RN-011, RN-016, RN-020, RNF-007, RNF-014
- **Contratos:** spec 009 (§4.2 ações, §5.2 e §5.3 leitura e motivos, §5.4 dispositivos, §6.3 a §6.7, canal §6.1 e §6.2); spec 011 §5.4 (`GET /api/dispositivos`). Casca: specs 016, 017, 022.
- **Decisões:** ADR-0005 (tela desatualizada), ADR-0004 §4.3 (permissões)

---

## 1. Contexto e origem

- A spec 022 (FE-303) já mostra a fila de pesagens, as ações manuais de cada uma (`acoes_disponiveis`, com `motivo` e `versao`) e a liberação de caminhão cancelado, com o bloqueio por tela desatualizada. A spec 024 **não repete a lógica**: reaproveita os mesmos componentes.
- O que a 022 não tem, e é desta spec: o **modo de cada dispositivo** (RF-023; hoje só a placa do cabeçalho resume o modo) e a **liberação manual de entrada** (RN-016), que exige escolher o agendamento.
- O backend decide tudo. A tela só mostra e pede (S-5).

## 2. Objetivo

Uma tela para o operador ver cada dispositivo com o modo e a falha, tratar as pesagens que pararam e, o administrador, liberar a entrada de uma placa que o sistema não autorizou por um motivo que a spec 009 §5.3 permite substituir.

## 3. Fora de escopo

- Abrir ou fechar cancela e digitar peso: não existem no contrato (009 §3).
- Troca de cenário dos simuladores e imagens: spec 023.
- Liberação de retorno e demais ações manuais: ficam nas ações da fila (§6.2).

## 4. Atores

Os três perfis veem a tela (`CONSULTAR_OPERACAO`). As ações seguem as permissões da spec 009 §4.3: `OPERADOR` tenta de novo e libera caminhão; `ADMINISTRADOR` faz tudo, inclusive a liberação de entrada (`INTERVIR_OPERACAO`). `AUDITOR` só vê.

## 5. Pré-condições

Sessão ativa. Rota `/dispositivos`, item "Dispositivos" no menu.

## 6. Comportamento normal

### 6.1 Canal e estado (como na spec 022 §3.1 e §3.2)

Mesmo canal e mesma ressincronização: abre o canal, busca `GET /api/operacao/estado`, "Sincronizando…" até lá, "Tela desatualizada" sem mensagem por `limite_sem_heartbeat_ms` ou com o canal caído. Desatualizada, todas as ações ficam bloqueadas (`AreaAcoes`) e os dados ficam esmaecidos.

### 6.2 Dispositivos (RF-023)

Cinco linhas: balança, cancela de entrada, cancela de saída, posição e identificação. Cada linha mostra:

- o **modo**: `REAL` (palavra e triângulo, campo de destaque) ou `SIMULADO` (palavra e círculo). Modo ausente ou fora desses dois valores aparece como "MODO DESCONHECIDO" (triângulo), nunca como simulado;
- o **estado** com palavra e forma, pelos mesmos textos da spec 022 §3.4 (balança: comunicação, motivo da falha e avaliação do peso; cancela: estado do sensor e último comando com resultado e tentativas; posição; identificação);
- a idade da informação ("há 4 s") quando o objeto traz o instante.

`DESCONHECIDO` da cancela nunca aparece como aberta ou fechada (RN-007). A leitura da balança aparece marcada "Leitura, não é peso aceito".

### 6.3 Intervenção manual

A seção "Fila" e a seção de caminhões cancelados na balança são as mesmas da spec 022 (`Fila` e `Liberacoes`): mesmos botões por `acoes_disponiveis` filtrados pela permissão, motivo obrigatório, `versao`, mensagens dos `409` da spec 022 §4. Um resumo no alto diz quantas pesagens estão em "Aguardando intervenção".

### 6.4 Liberação manual de entrada (RN-016, spec 009 §6.5)

1. A seção aparece só com `INTERVIR_OPERACAO`. Ela trata a **última leitura de placa** (`ultima_leitura_placa` do estado, atualizada pelo canal). Mostra placa lida, decisão, motivo, confiança, hora e, se houver, "imagem salva".
2. O formulário só se oferece quando a leitura é `NAO_AUTORIZADA`, ainda sem `pesagem_id`, e o motivo é um dos que a §5.3 marca como substituíveis: `FALHA_IMAGEM`, `FALHA_LEITOR`, `SEM_CANDIDATO`, `PLACA_INVALIDA`, `AMBIGUA`, `CONFIANCA_BAIXA`, `ANTES_DA_FAIXA`. Com outro motivo, a tela diz: "Esse motivo não pode ser liberado aqui. Resolva o cadastro ou o agendamento." Isso só esconde o botão: quem recusa é o backend (`MOTIVO_NAO_SUBSTITUIVEL`).
3. O administrador **escolhe o agendamento** numa lista dos agendamentos `AGENDADO` de hoje (`GET /api/agendamentos`, filtros `status` e `data_inicio`/`data_fim`), cada um com placa, motorista, faixa e tipo. A tela não escolhe, não sugere nem pré-seleciona.
4. Campo "Motivo" obrigatório (até 200 caracteres), uma frase do que a ação faz ("Cria a pesagem para o agendamento escolhido. A entrada só abre depois, com a balança livre.") e "Liberar entrada". Envia `POST /api/leituras-placa/{id}/liberar-entrada` com `{ agendamento_id, motivo }`.
5. `201`: "Entrada liberada para o agendamento. A cancela abre quando a balança estiver livre." e o formulário some. A pesagem nova chega pelo canal.
6. Se chegar uma leitura mais nova, o formulário é reiniciado para a nova leitura (a escolha e o motivo digitados não valem para outra placa).

## 7. Comportamento em falha

| Situação | Tela |
|---|---|
| `409 LEITURA_DESATUALIZADA` | "Chegou uma leitura mais nova. Confira a última placa lida." |
| `409 LEITURA_NAO_LIBERAVEL` | "Essa leitura já foi liberada ou não precisa de liberação." |
| `409 MOTIVO_NAO_SUBSTITUIVEL` | "Esse motivo não pode ser liberado aqui." |
| `409 VEICULO_INATIVO` / `MOTORISTA_INATIVO` | "O veículo (ou motorista) do agendamento está inativo." |
| `409 OPERACAO_JA_ABERTA` | "Esse veículo já tem uma operação aberta." |
| `409 SEM_AGENDAMENTO` | "O agendamento escolhido não vale para hoje." |
| `403`, `422`, `500`, rede caída | Mensagem comum (spec 016 §7). |
| Falha ao listar os agendamentos | Erro com "Tentar de novo"; sem lista, não há envio. |
| Nenhum agendamento `AGENDADO` hoje | "Nenhum agendamento para hoje. Crie o agendamento antes." e o envio fica desabilitado. |

Em nenhum caso a tela supõe que a ação teve efeito sem o `201`.

## 8. Regras e dados

- Tipos e chamadas: `tipos/operacao.ts`, `api/operacao.ts` (`liberarEntrada`) e `api/agendamentos.ts`. Nenhum campo novo.
- "Hoje" vem do navegador (spec 019 Q-F4); o backend valida (`SEM_AGENDAMENTO`).
- O `motivo` das ações é texto livre e fica só no corpo da requisição.
- A tela não grava em `localStorage`, `sessionStorage` nem cookie.

## 9. Critérios de aceitação

| CA | Critério | Como verificar |
|---|---|---|
| CA-001 | A tela abre o canal e busca o estado; sem estado, mostra "Sincronizando…" e bloqueia as ações; sem mensagem por `limite_sem_heartbeat_ms`, mostra "Tela desatualizada". | Teste com o canal falso. |
| CA-002 | Cada dispositivo mostra o modo em palavra e forma; modo fora de `REAL` e `SIMULADO` mostra "MODO DESCONHECIDO". | Teste. |
| CA-003 | Falha da balança, cancela `FALHA`/`SEM_CONFIRMACAO`, cancela `DESCONHECIDO`, posição `INCONCLUSIVA` e identificação `FALHA_*` aparecem com palavra e forma, e a cancela `DESCONHECIDO` nunca como aberta ou fechada. | Teste. |
| CA-004 | A fila e as ações manuais são as da spec 022: botões por `acoes_disponiveis` e permissão, motivo e `versao`, `409` com mensagens próprias, bloqueio por tela desatualizada. | Teste (uma ação ponta a ponta, o resto vale pelos testes da 022). |
| CA-005 | O formulário de liberação de entrada só aparece com `INTERVIR_OPERACAO`, última leitura `NAO_AUTORIZADA` sem pesagem e motivo substituível; com motivo não substituível mostra o aviso. | Teste. |
| CA-006 | O administrador escolhe o agendamento entre os `AGENDADO` de hoje; sem escolha ou sem motivo, não envia; nada vem pré-selecionado. | Teste. |
| CA-007 | O envio manda `{ agendamento_id, motivo }` para a leitura mostrada; só o `201` mostra o sucesso. | Teste. |
| CA-008 | Cada `409` da §7 mostra o texto próprio e mantém o formulário; `403` e rede caída não mostram sucesso. | Teste. |
| CA-009 | Uma leitura mais nova reinicia o formulário. | Teste. |
| CA-010 | Com a tela desatualizada, o formulário e os botões ficam desabilitados. | Teste. |
| CA-011 | Operador e auditor não veem o formulário de liberação de entrada; auditor não vê botão de ação. | Teste. |
| CA-012 | Nenhum código grava em `localStorage`, `sessionStorage` ou `document.cookie`. | `grep`. |

## 10. Impacto

- **Pastas:** `frontend/src/paginas/dispositivos/` (novas); uma rota em `rotas.tsx`; um item em `componentes/navegacao.ts`. Reaproveita `Painel`, `Fila` e `Liberacoes` de `paginas/operacao/PaginaOperacao.tsx` e os indicadores de `operacao/textos.ts` (Loom).
- **Segurança operacional:** a liberação de entrada é a ação com mais peso da tela: substitui uma decisão automática (RN-016). Por isso: só o administrador, escolha explícita do agendamento, motivo obrigatório, leitura sempre a mais recente, bloqueio com tela desatualizada e nenhuma suposição de sucesso. Quem recusa o inseguro é o backend.
- **Reversibilidade:** alta.

## 11. Perguntas em aberto

Nenhuma nova. Valem as da spec 009 §10 (P-1: limite de tempo desde a leitura).
