# Spec 022 — Tela operacional em tempo real

- **Trilha:** Frontend
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-303 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-021, RF-023, RF-024, RN-007, RN-011, RN-016, RN-020, RNF-009, RNF-014
- **Contrato:** spec 009 (estado, canal SSE, ações). Casca: specs 016 e 017.
- **Decisões:** ADR-0005 (SSE, `versao`, aviso e bloqueio), ADR-0004 §4.3 (permissões)

## 1. Objetivo

Mostrar ao operador, em tempo real, a balança, as cancelas, a última placa lida e a fila de pesagens abertas, com cada falha nomeada, e permitir as ações manuais que o backend oferece (RF-021).

## 2. Fora de escopo

- Liberação manual de entrada (`liberar-entrada`): FE-306, porque exige escolher o agendamento.
- Imagens e ROIs: FE-305. A tela mostra só que há imagem (`imagem_id`), sem buscá-la.
- Abrir ou fechar cancela e digitar peso: não existem no contrato (009 §3).

## 3. Comportamento

### 3.1 Canal e ressincronização (009 §6.1, §6.2)

1. Ao abrir a tela, abre o canal `GET /api/operacao/eventos` e depois busca `GET /api/operacao/estado`. Até o `GET` responder, a tela mostra "Sincronizando…" e as ações ficam bloqueadas.
2. A cada reconexão do canal, busca o estado de novo e só então libera as ações.
3. Qualquer mensagem do canal, inclusive `heartbeat`, conta como sinal de vida.
4. **Desatualizada:** sem mensagem por mais de `limite_sem_heartbeat_ms` (vem do estado), ou com o canal caído, a tela mostra "Tela desatualizada" e bloqueia todas as ações (AreaAcoes, spec 016 §6.5). A operação segue no backend.
5. Sem nenhuma mensagem por mais de `limite_sem_heartbeat_ms` (5 s antes do primeiro estado), a tela fecha e reabre o canal: uma conexão pendurada num proxy não avisa erro, e um canal fechado de vez não tenta sozinho. Canal fechado de vez (ex.: sessão encerrada) também busca o estado: um `401` leva ao login (spec 016). A tela oferece ainda "Reconectar".
6. Evento com JSON inválido: é ignorado e a tela busca o estado de novo.

### 3.2 Regras de ordem (009 §6.1)

- `pesagem`: ignorado se `versao` for menor ou igual à que a tela tem. Situação terminal (`FINALIZADA`, `CANCELADA`) tira a pesagem da fila. Pesagem nova entra no fim da fila.
- Os demais substituem o objeto só se o instante for mais novo: `leitura_placa` por `decidida_em`; `balanca` por `comunicacao_em`; `cancela` por `estado_em`, cada cancela pelo nome; `posicao` e `identificacao` por `analisada_em`; `liberacao_caminhao` por `atualizada_em`, cada uma pelo `pesagem_id`. Instante nulo no estado atual aceita o novo.
- `peso_lido` substitui a última leitura da balança se `lida_em` for mais novo.
- `liberacao_caminhao` em `CONCLUIDA` sai da lista de pendências.

### 3.3 Áreas da tela

- **Balança:** última leitura em kg, marcada "leitura, não é peso aceito", com a idade ("há 4 s"); comunicação (`OK`, `FALHA` com o motivo, `DESCONHECIDO`); avaliação do peso (aceito ou o motivo da rejeição); posição do caminhão e identificação.
- **Cancelas:** entrada e saída, cada uma com o estado do sensor (`ABERTA`, `FECHADA`, `DESCONHECIDO`) e o último comando com resultado e tentativas.
- **Última placa:** placa normalizada, decisão, motivo, confiança e hora.
- **Fila:** pesagens abertas na ordem do backend. Por linha: placa, tipo, etapa (situação em português), situação do agendamento, pesos aceitos, comando pendente e, em `AGUARDANDO_INTERVENCAO`, o motivo e a situação anterior.
- **Liberações pendentes:** caminhões cancelados ainda na balança, com a etapa da liberação.

A placa de modo do cabeçalho passa a usar os `dispositivos` desta tela, atualizados pelo canal.

### 3.4 Estados de falha

Cada um tem palavra e forma fixas (DESIGN.md):

| Situação | Forma | Texto |
|---|---|---|
| Balança `FALHA`, cancela `FALHA` ou `SEM_CONFIRMACAO`, identificação `FALHA_*`, leitura `NAO_AUTORIZADA` | círculo cortado, vermelho | o valor em português, com o motivo |
| `DESCONHECIDO`, posição `INCONCLUSIVA`, `AGUARDANDO_INTERVENCAO`, peso rejeitado | triângulo, amarelo | o valor e o motivo |
| `OK`, `CONFIRMADA`, peso aceito, `AUTORIZADA` | quadrado, verde | o valor |

### 3.5 Ações (009 §4.2, §6.3)

- Por pesagem, um botão para cada item de `acoes_disponiveis` que a sessão pode usar: `TENTAR_NOVAMENTE` exige `TENTAR_NOVAMENTE`; as demais, `INTERVIR_OPERACAO`.
- Por liberação pendente, "Liberar caminhão", com `LIBERAR_CAMINHAO_CANCELADO`, se não houver liberação em curso (etapa `PENDENTE` ou `FALHOU`).
- O botão abre na linha o campo "Motivo" (obrigatório, até 200 caracteres), uma frase sobre o que a ação faz e "Confirmar". A ação envia a `versao` que a tela mostrava, e o motivo.
- `200`: "Pedido aceito. O resultado chega pelos eventos." A tela aplica a `Pesagem` devolvida pela regra de `versao`. A cancela só aparece movida pelo evento `cancela`.
- Com a tela desatualizada, os botões e os formulários abertos ficam bloqueados.

## 4. Falhas das ações

| Resposta | Tela |
|---|---|
| `409 VERSAO_DESATUALIZADA` | "A pesagem mudou desde que você abriu a ação. Confira a situação e peça de novo." |
| `409 TRANSICAO_REJEITADA` | "Essa ação não vale mais na situação atual." |
| `409 LIBERACAO_EM_CURSO` | "Já existe uma liberação em curso para esse caminhão." |
| `409 OPERACAO_NAO_OCUPA_BALANCA` | "Esse caminhão não está mais aguardando liberação." |
| `403 SEM_PERMISSAO`, `422` e outros | A mensagem comum (spec 016 §7). |

Em nenhum caso a tela supõe que a ação teve efeito.

## 5. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | Ao abrir, a tela abre o canal antes de buscar o estado, e as ações ficam bloqueadas até o estado chegar (009 CA-011). |
| CA-002 | Evento `pesagem` com `versao` menor ou igual é ignorado; maior substitui; terminal tira da fila (009 CA-010). |
| CA-003 | Eventos de dispositivo e de leitura mais antigos que o atual são ignorados. |
| CA-004 | Sem mensagem por mais de `limite_sem_heartbeat_ms`, aparece "Tela desatualizada" e os botões ficam desabilitados; um `heartbeat` não libera sozinho depois de uma queda: só o `GET` do estado libera (009 CA-011). |
| CA-005 | Com o canal caído, a tela fica desatualizada; ao reabrir, busca o estado e só então libera. Sem mensagem além do limite, fecha e reabre o canal sozinha. |
| CA-006 | Cada falha da §3.4 aparece com a palavra e a forma da tabela; cancela `DESCONHECIDO` nunca aparece como aberta ou fechada. |
| CA-007 | Só aparecem botões de ações que estão em `acoes_disponiveis` e que a sessão tem permissão de usar. |
| CA-008 | A ação envia `{ versao, motivo }` com a versão mostrada; sem motivo, não envia. |
| CA-009 | `409 VERSAO_DESATUALIZADA` e `TRANSICAO_REJEITADA` mostram as mensagens da §4, e a tela não muda a pesagem por conta própria. |
| CA-010 | "Liberar caminhão" aparece só com `LIBERAR_CAMINHAO_CANCELADO` e etapa `PENDENTE` ou `FALHOU`, e envia `{ motivo }`. |
| CA-011 | A leitura da balança aparece marcada como leitura, separada dos pesos aceitos da pesagem. |
| CA-012 | A placa de modo do cabeçalho segue os `dispositivos` recebidos pela tela. |

## 6. Perguntas em aberto

Nenhuma nova. Valem as da spec 009 §10.
