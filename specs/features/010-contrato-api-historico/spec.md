# Spec 010 — Contrato da API de histórico

- **Trilha:** Contrato
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** CT-104; implementação no backend (`api/`), uso na tela de histórico do frontend — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-016, RF-018, RF-019, RF-020, RN-006, RN-009, RN-011, RN-022, RNF-010, RNF-013, RNF-014
- **Decisões:** ADR-0004 (permissões); spec 002 (peso líquido e classificação); spec 004 (resultado dos comandos de cancela); spec 006 (situações, eventos e registro de auditoria); spec 007 §3 (regras comuns da API); spec 012 (sessão e CSRF)

---

## 1. Contexto e origem

- O artigo prevê o histórico das pesagens para consulta e auditoria e o registro dos eventos de cancela **[ARTIGO §2, §3.5, §4]** (RF-018, RF-019, RF-020).
- Cada transição, rejeição e evento registrado da spec 006 vira um registro de auditoria com situação de origem e de destino, evento, instante, responsável e motivo, sem placa nem imagem (spec 006 §10).
- A tela operacional em tempo real é da CT-103 (spec 009). Este contrato é só consulta: nada aqui muda uma operação.

## 2. Objetivo

Definir a lista das pesagens, abertas e encerradas, e os eventos de cada uma, com filtros, paginação e permissões verificáveis pelos dois lados.

## 3. Fora de escopo

- Item da pesagem, estado atual em tempo real, canal de eventos e ações manuais: spec 009.
- Leituras de placa, imagens, ROIs e estado dos dispositivos: spec 011. Aqui os eventos só trazem as referências (§5.2).
- Auditoria de acesso e de cadastros (login, usuários, agendamentos): specs 012 e 008.
- Exportação, relatórios e comprovante de pesagem (Q-03).

## 4. Rotas e permissões

A forma das respostas, os erros e a paginação seguem a spec 007 §3.

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/pesagens` | Lista, abertas e encerradas, com filtros (§5.1) | 200 | `CONSULTAR_OPERACAO` |
| `GET /api/pesagens/{pesagem_id}/eventos` | Eventos da pesagem, paginados (§5.2) | 200 | `CONSULTAR_OPERACAO` |

O item `GET /api/pesagens/{pesagem_id}` e as ações sobre a pesagem são da spec 009. Esta spec não aceita outro método nas suas rotas: dá `405`, com o corpo de erro da spec 007 §3.2 e `codigo` `METODO_NAO_PERMITIDO`.

`ADMINISTRADOR`, `OPERADOR` e `AUDITOR` têm `CONSULTAR_OPERACAO` (ADR-0004 §4.3), então os três veem o histórico completo.

## 5. Recursos e campos

### 5.1 `pesagens`

Cada item da lista é o **objeto Pesagem da spec 009 §5.1**, sem campo a mais nem a menos. Esta spec não o redefine. Pontos que o histórico depende dele:

- `placa` e `tipo_operacao` são os gravados quando a pesagem nasceu e não mudam com o cadastro (spec 007 §6.3);
- `peso_liquido_kg` e `classificacao` são os da spec 002, `null` sem o peso final, e o líquido nunca é trocado por zero, inclusive em `SEM_MOVIMENTACAO` (RN-006);
- depois de um `TENTAR_NOVAMENTE` com `LIQUIDO_NEGATIVO`, o peso final, o líquido e a classificação voltam a `null` (spec 006 §6.1), e os valores descartados ficam nos eventos (§5.2);
- `motorista_nome`, `transportadora_razao_social` e `produto_descricao` mostram o cadastro atual (P-1). Nenhuma resposta traz CPF (RNF-013).

Filtros:

| Filtro | Efeito |
|---|---|
| `data_inicio`, `data_fim` | Dia de `criado_em`, no fuso do pátio (`PESAGEM_PATIO_FUSO`, spec 008 §6.1), com os dois limites incluídos. `data_fim` antes de `data_inicio` dá `422`. |
| `aberta` | `true`: situação não terminal; `false`: `FINALIZADA` ou `CANCELADA`. |
| `situacao` | Um valor da spec 006 §5.1. |
| `tipo_operacao` | `CARGA` ou `DESCARGA`. |
| `classificacao` | Um valor da spec 002. |
| `liberacao_manual` | `true` ou `false`. |
| `placa` | Compara pela `chave_comparacao` (spec 003). Placa que não normaliza dá `422 PLACA_INVALIDA`. |
| `agendamento_id` | Pesagens daquele agendamento. Pode haver várias, se as anteriores foram `CANCELADA` (RN-009). |

Ordem: `criado_em` decrescente, depois `id` decrescente: a mais recente primeiro.

### 5.2 Eventos da pesagem

Cada item é um registro de auditoria. Os campos que não se aplicam ao `tipo` vêm `null`.

| Campo | Tipo | Conteúdo |
|---|---|---|
| `id` | inteiro | — |
| `tipo` | texto | `TRANSICAO` (situação mudou), `TRANSICAO_REJEITADA` (spec 006 §7.1), `EVENTO_REGISTRADO` (spec 006 §5.5, situação não mudou) ou `COMANDO_CANCELA`. |
| `ocorrido_em` | data e hora | — |
| `evento` | texto | Evento automático (spec 006 §5.2) ou ação manual (spec 006 §5.3). Também `CRIACAO` para o nascimento da pesagem e `LIBERACAO_CAMINHAO_CANCELADO` para a liberação da spec 006 §6.4. `null` em `COMANDO_CANCELA`. |
| `situacao_origem` | texto | Situação antes do evento. |
| `situacao_destino` | texto | Situação depois; `null` em `TRANSICAO_REJEITADA` e `EVENTO_REGISTRADO`. |
| `motivo_rejeicao` | texto | Só em `TRANSICAO_REJEITADA`. |
| `motivo_intervencao` | texto | Quando a transição leva a `AGUARDANDO_INTERVENCAO` (spec 006 §5.4). |
| `motivo_dispositivo` | texto | Motivo vindo da balança ou da spec 002 em `PESO_REJEITADO` e `BALANCA_FALHA` (por exemplo `INSTAVEL`). |
| `peso_kg` | decimal como texto | Peso aceito em `PESO_ACEITO`. |
| `peso_liquido_kg`, `classificacao` | decimal como texto, texto | Em `PESO_ACEITO` da pesagem final. Assim um peso final descartado por `TENTAR_NOVAMENTE` continua visível (spec 006 §6.1). |
| `cancela` | texto | `ENTRADA` ou `SAIDA`, em `COMANDO_CANCELA`. |
| `comando` | texto | `ABRIR` ou `FECHAR`. |
| `resultado` | texto | `CONFIRMADO`, `FALHA` ou `SEM_CONFIRMACAO` (spec 004). |
| `tentativas` | inteiro | 0, 1 ou 2 (spec 004). |
| `responsavel` | objeto | `{ "id": 1, "nome": "..." }` do usuário que pediu a ação manual; `null` em evento automático (RN-011). |
| `motivo` | texto | Motivo digitado na ação manual (RN-011); `null` em evento automático. |
| `imagem_id` | inteiro | Imagem salva da decisão, quando houver (RN-022); senão `null`. Só a referência: a imagem é buscada em `GET /api/imagens-decisao/{imagem_id}` (spec 011), que exige `CONSULTAR_IMAGENS_DECISAO`. |
| `leitura_placa_id` | inteiro | Leitura de placa que gerou o evento, como em `CRIACAO` e `PLACA_RETORNO_ACEITA`; senão `null`. Detalhe em `GET /api/leituras-placa` (spec 011). |

Nenhum evento traz placa, CPF ou imagem (spec 006 §10, RNF-013).

Sem filtros. Ordem: `ocorrido_em`, depois `id`, do mais antigo ao mais recente, para ler a operação na ordem em que aconteceu.

## 6. Regras

### 6.1 Só consulta

- As rotas não mudam nada e não renovam nada além do prazo da sessão (spec 012 §6.3).
- O histórico mostra o que foi gravado. Nenhum valor é recalculado na consulta: o `peso_liquido_kg` é o gravado pela orquestração (spec 002).

### 6.2 Consistência

- A resposta é uma leitura do banco no momento do pedido. Uma pesagem aberta pode mudar logo depois; a tela de histórico não é a tela operacional, e não tem canal de eventos.
- A lista é paginada com ordem fixa (§5.1). Uma pesagem nova criada entre duas páginas pode deslocar os itens. É aceito: a tela mostra o `total` de cada pedido.

### 6.3 Imagem excluída (RN-022)

A exclusão de uma imagem não muda a pesagem nem os eventos: o `imagem_id` continua no evento. Pela spec 011, `GET /api/imagens-decisao/{imagem_id}` responde com `excluida: true`, quem excluiu, quando e o motivo, e o conteúdo da imagem dá `409` com `IMAGEM_EXCLUIDA`.

### 6.4 Falhas

| Situação | Resposta |
|---|---|
| Banco indisponível | `500 ERRO_INTERNO`. O frontend mostra erro e não mostra dado antigo como atual. |
| `pesagem_id` inexistente em `/eventos` | `404 NAO_ENCONTRADO`. |
| Filtro com valor fora da lista ou de tipo errado | `422 CAMPO_INVALIDO`, com o filtro indicado. |
| Tempo de resposta | Sem número definido; não há dado para isso. |

### 6.5 Códigos

`PLACA_INVALIDA` em `campos[].codigo`, e `METODO_NAO_PERMITIDO` (405), além dos códigos comuns da spec 007 e da spec 012.

## 7. Dados pessoais

- A placa e o nome do motorista aparecem para os três perfis, como na spec 008 (P-1 de lá).
- A query string fica fora dos registros de acesso (spec 007 §3.4); o filtro `placa` passa por ela.
- O `motivo` digitado é texto livre e pode conter dados pessoais: não vai para logs.

## 8. Critérios de aceitação

Verificáveis no backend (testes de API) e no frontend (respostas simuladas com estes tipos, S-6).

| CA | Critério |
|---|---|
| CA-001 | As duas rotas da §4 existem e só aceitam `GET`; outro método dá `405`. |
| CA-002 | Sem sessão: `401`. `ADMINISTRADOR`, `OPERADOR` e `AUDITOR` consultam; um perfil sem `CONSULTAR_OPERACAO` recebe `403`. |
| CA-003 | Uma pesagem `FINALIZADA` de CARGA traz pesos inicial e final, `peso_liquido_kg` = final − inicial e a `classificacao`; em DESCARGA, inicial − final. |
| CA-004 | Em `SEM_MOVIMENTACAO`, o `peso_liquido_kg` é o calculado (por exemplo `"12.000"`), não zero. |
| CA-005 | O filtro `aberta=true` traz só situações não terminais, e os pesos ainda não aceitos vêm `null`; cada item tem exatamente os campos do objeto Pesagem da spec 009 §5.1. |
| CA-006 | Em `AGUARDANDO_INTERVENCAO`, `situacao_anterior` e `motivo_intervencao` vêm preenchidos; nas outras situações, `null`. |
| CA-007 | Os eventos vêm em ordem cronológica e cobrem transições, rejeições, eventos registrados e comandos de cancela da operação. |
| CA-008 | Uma ação manual aparece com `responsavel` e `motivo`; um evento automático, com os dois `null`. |
| CA-009 | Um comando de cancela traz `cancela`, `comando`, `resultado` e `tentativas`; `SEM_CONFIRMACAO` aparece como tal, nunca como sucesso. |
| CA-010 | Depois de `TENTAR_NOVAMENTE` com `LIQUIDO_NEGATIVO`, a pesagem mostra o peso final `null`, e o evento do `PESO_ACEITO` anterior ainda traz o peso e o líquido descartados. |
| CA-011 | O filtro `placa` encontra `ABC1C34` ao pedir `ABC1234` (chave de comparação); uma placa que não normaliza dá `422`. |
| CA-012 | `data_inicio` e `data_fim` usam o fuso do pátio: uma pesagem criada às 23h30 no fuso do pátio entra no dia do pátio, e não no do servidor. |
| CA-013 | Duas pesagens do mesmo agendamento, a primeira `CANCELADA`, aparecem as duas no filtro `agendamento_id` (RN-009). |
| CA-014 | Nenhuma resposta contém CPF, imagem ou placa dentro dos eventos. |
| CA-015 | A lista e os eventos trazem `itens`, `total`, `pagina` e `tamanho_pagina`, na ordem da §5. |
| CA-016 | Os registros de acesso não contêm a query string nem o `motivo` digitado. |

## 9. Impacto

- **Backend:** rotas de leitura sobre `pesagem` e sobre os registros de auditoria da spec 006 §10 e de cancela.
- **Frontend:** tela de histórico e detalhe com a lista de eventos.
- **Esquema (BE-502, spec 014), sem alterar agora:** índice para a ordem `criado_em DESC, id DESC` e para os filtros `situacao`, `agendamento_id` e a chave de comparação da placa; nos eventos, `responsavel`, `motivo`, `motivo_dispositivo`, `peso_kg`, `peso_liquido_kg`, `classificacao`, `imagem_id` e `leitura_placa_id`; o `evento_cancela` com `resultado` e `tentativas` no lugar de `sucesso` (C-002 item 5) e o responsável da liberação da spec 006 §6.4.
- **Spec 009:** dona do objeto Pesagem e do item; mudança nele muda a lista desta spec.
- **Spec 011:** as rotas da imagem e da leitura, e a resposta para imagem excluída.
- **Segurança operacional:** nenhuma ação física.
- **Reversibilidade:** alta, sem código ainda.

## 10. Perguntas em aberto

| ID | Pergunta | Situação até a resposta |
|---|---|---|
| P-1 | `motorista_nome`, `transportadora_razao_social` e `produto_descricao` devem ser os do momento da pesagem? A spec 007 §6.3 diz que as operações encerradas mantêm os dados do momento, mas só a placa e o tipo são gravados na pesagem. | Mostram o cadastro atual, como na spec 008 e na 009. A `placa` e o `tipo_operacao` são os do momento. |
