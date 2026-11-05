# Spec 008 — Contrato da API de agendamentos

- **Trilha:** Contrato
- **Status:** Aprovada pelo autor em 2026-11-04 (respostas às perguntas da §11)
- **Data:** 2026-11-04
- **Tarefa:** CT-102; implementação na BE-702, uso na FE-302 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-004, RF-005, RF-028, RF-029, RN-001, RN-002, RN-009, RN-013, RN-014, RN-015, RN-023, RN-024, RNF-013, RNF-014
- **Decisões:** ADR-0004 (permissões); spec 006 §6.2 (efeito da operação no status); spec 007 §3 (regras comuns da API)

---

## 1. Contexto e origem

- O artigo prevê a criação e o gerenciamento de agendamentos **[ARTIGO §1, §2, §4]**. A criação é sempre uma ação humana (RN-001).
- As faixas de horário e as regras de validade vêm da Q-13 (RF-028, RF-029, RN-014, RN-015).
- A spec 007 §7 deixou as faixas para este contrato.
- `docs/modelo-dados/schema.sql` é referência **[PROPOSTA]**: não tem faixas, e a BE-502 o ajusta a este contrato.

## 2. Objetivo

Definir rotas, campos, erros e permissões de agendamentos e faixas de horário, com critérios verificáveis pelos dois lados.

## 3. Fora de escopo

- Criação pelo motorista, sem login: CT-107. Ela reaproveita as regras da §6 e o campo `origem`.
- Decisão de autorizar a entrada (RN-002, RN-014): é da orquestração, na BE-601, e aparece na CT-103.
- Consulta externa da nota e calendário de feriados ou dias fechados.

## 4. Rotas e permissões

A forma das respostas, os erros e a paginação seguem a spec 007 §3.

### 4.1 Agendamentos

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/agendamentos` | Lista, com filtros | 200 | `CONSULTAR_AGENDAMENTOS` (P-1) |
| `GET /api/agendamentos/{agendamento_id}` | Um item | 200 | `CONSULTAR_AGENDAMENTOS` (P-1) |
| `POST /api/agendamentos` | Cria | 201, com o item | `CRIAR_AGENDAMENTO` |
| `PATCH /api/agendamentos/{agendamento_id}` | Altera só os campos enviados | 200, com o item | `GERENCIAR_AGENDAMENTOS` |
| `POST /api/agendamentos/{agendamento_id}/cancelar` | Cancela (§6.5) | 200, com o item | `GERENCIAR_AGENDAMENTOS` |

**Não há `DELETE`:** o histórico das operações depende do agendamento.

### 4.2 Faixas de horário

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/faixas-horario` | Lista | 200 | `CONSULTAR_CADASTROS` |
| `GET /api/faixas-horario/{faixa_horario_id}` | Um item | 200 | `CONSULTAR_CADASTROS` |
| `POST /api/faixas-horario` | Cria | 201, com o item | `GERENCIAR_CADASTROS` |
| `PATCH /api/faixas-horario/{faixa_horario_id}` | Altera só os campos enviados, inclusive `ativo` | 200, com o item | `GERENCIAR_CADASTROS` |
| `GET /api/faixas-horario/disponibilidade?data=` | Vagas das faixas ativas no dia (§6.2) | 200 | `CRIAR_AGENDAMENTO` |

### 4.3 Acesso por perfil

| Perfil | Agendamentos | Faixas |
|---|---|---|
| `ADMINISTRADOR` | Consulta, cria, edita e cancela | Consulta e altera |
| `OPERADOR` | Consulta e cria (RN-013: não edita nem cancela) | Consulta e vê as vagas |
| `AUDITOR` | Só consulta (P-1) | Sem acesso às rotas de faixa; vê a faixa dentro do agendamento |

## 5. Recursos e campos

### 5.1 `agendamentos`

| Campo | Tipo | Na criação | Validação |
|---|---|---|---|
| `id` | inteiro | Só leitura | — |
| `veiculo_id` | inteiro | Obrigatório | Veículo ativo. |
| `motorista_id` | inteiro | Obrigatório | Motorista ativo. |
| `transportadora_id` | inteiro | Opcional | Transportadora ativa (RF-004; spec 007, P-5). |
| `produto_id` | inteiro | Obrigatório | Produto ativo. |
| `tipo_operacao` | texto | Obrigatório | `CARGA` ou `DESCARGA`. |
| `data_prevista` | data | Obrigatório | Hoje ou depois (§6.1). |
| `faixa_horario_id` | inteiro | Opcional | Faixa ativa, com vaga e não encerrada (§6.3). `null` ou ausente: primeira faixa com vaga (RF-029). |
| `codigo_nota` | texto até 100 | Opcional | Só em `DESCARGA` (P-6). Sem verificar o formato ou a autenticidade (RN-021). |
| `observacao` | texto até 200 | Opcional | — |
| `status` | texto | Só leitura | §6.6. |
| `origem` | texto | Só leitura | `USUARIO` ou `AUTOATENDIMENTO`. |
| `criado_por` | inteiro | Só leitura | Usuário da sessão; `null` no autoatendimento. |
| `criado_em` | data e hora | Só leitura | — |
| `cancelado_por` | inteiro | Só leitura | `null` se não cancelado. |
| `cancelado_em` | data e hora | Só leitura | `null` se não cancelado. |
| `motivo_cancelamento` | texto | Só leitura | `null` se não cancelado. |

**Resumo somente leitura**, para o `AUDITOR` e o `OPERADOR` não precisarem de outras rotas: `placa`, `motorista_nome`, `transportadora_razao_social`, `produto_descricao`, `faixa_hora_inicio`, `faixa_hora_fim`. Esses campos mostram o cadastro atual. **Nenhuma resposta desta spec traz o CPF** (RNF-013).

Filtros: `data_inicio`, `data_fim`, `status`, `tipo_operacao`, `origem`, `placa` (compara pela `chave_comparacao`, spec 003). Ordem: `data_prevista`, `faixa_hora_inicio`, `id`.

### 5.2 `faixas-horario`

| Campo | Tipo | Na criação | Validação |
|---|---|---|---|
| `id` | inteiro | Só leitura | — |
| `hora_inicio` | hora `HH:MM` | Obrigatório | — |
| `hora_fim` | hora `HH:MM` | Obrigatório | Maior que `hora_inicio` (P-5). |
| `capacidade` | inteiro | Obrigatório | Maior que 0. |
| `ativo` | booleano | `true` ao criar | — |

Filtros: `ativo`. Ordem: `hora_inicio`, `id`.

### 5.3 Disponibilidade

Faixas ativas no dia pedido, na ordem de `hora_inicio`. Não é paginada, porque são poucas faixas:

```json
{
  "data": "2026-11-05",
  "itens": [
    {
      "faixa_horario_id": 1,
      "hora_inicio": "08:00",
      "hora_fim": "10:00",
      "capacidade": 5,
      "vagas_ocupadas": 5,
      "vagas_livres": 0,
      "encerrada": false
    }
  ]
}
```

Os horários acima são só um exemplo. A tela apresenta a primeira faixa com vaga como sugestão, e quem agenda confirma. Assim a criação continua manual (RF-029, RN-001).

## 6. Regras

### 6.1 Dia

- "Hoje" e o horário da faixa usam o **fuso do pátio**, que vem de `PESAGEM_PATIO_FUSO`, sem valor padrão no código. A mesma configuração vale para a RN-014 na BE-601.
- `data_prevista` no passado dá `422`. Não há limite para datas futuras, porque nenhum requisito pede (P-7).
- As faixas valem igualmente para todos os dias, inclusive fins de semana e feriados (P-5).

### 6.2 Vagas (RN-015)

- `vagas_ocupadas` conta os agendamentos da faixa naquele dia com status `AGENDADO`, `EM_ANDAMENTO` ou `CONCLUIDO`. Só o cancelamento libera a vaga. Um caminhão que já saiu não libera a vaga, porque a capacidade é do dia e não do pátio naquele instante.
- `vagas_livres` nunca é negativa: vale `capacidade − vagas_ocupadas`, com mínimo 0.
- Dois pedidos pela última vaga: um recebe `201` e o outro `409`, garantido por transação no banco.

### 6.3 Escolha da faixa

- **Com `faixa_horario_id`:** usa essa faixa. Sem vaga, `409 FAIXA_SEM_VAGA`. Faixa encerrada hoje, `409 FAIXA_ENCERRADA` (P-3).
- **Sem `faixa_horario_id`:** o backend usa a primeira faixa ativa, não encerrada e com vaga, e a resposta mostra qual foi. Se não houver, `409 SEM_FAIXA_DISPONIVEL`, e nada é criado.
- A RN-014 trata da **chegada**: quem já tinha agendamento e chega depois da faixa ainda pode entrar no mesmo dia. Uma faixa encerrada só deixa de aceitar agendamentos **novos**.

### 6.4 Um agendamento aberto por veículo (P-2, RN-023)

Um veículo não pode ter dois agendamentos **abertos** ao mesmo tempo, seja qual for a data: `409 VEICULO_JA_AGENDADO`, garantido pela unicidade no banco.

- **Aberto:** `AGENDADO` ou `EM_ANDAMENTO`.
- **Encerrado:** `CONCLUIDO`, `CANCELADO` ou `EXPIRADO`. Só depois disso o veículo pode ter um novo agendamento, inclusive no mesmo dia.
- **Consequência:** não dá para deixar o mesmo veículo agendado em dois dias com antecedência, e um `EM_ANDAMENTO` que passou da meia-noite impede um novo agendamento até terminar.

Motivo: a RN-002 exige um **único** agendamento válido. Com dois, o caminhão ficaria parado na entrada até alguém resolver.

### 6.5 Edição e cancelamento (RN-013, spec 006 §6.2)

| Status | `PATCH` | `cancelar` |
|---|---|---|
| `AGENDADO` | Permitido | Permitido |
| `EM_ANDAMENTO` | `409 STATUS_NAO_PERMITE` | `409 STATUS_NAO_PERMITE` |
| `CONCLUIDO`, `CANCELADO`, `EXPIRADO` | `409 STATUS_NAO_PERMITE` | `409 STATUS_NAO_PERMITE` |

- **`PATCH`:** aceita os campos de entrada da §5.1, e `status` e os demais campos somente leitura dão `422`. Só valida as referências enviadas. Mudar `data_prevista` ou `faixa_horario_id` verifica de novo as vagas e a §6.3, sem contar o próprio agendamento. Mudar `veiculo_id` verifica de novo a §6.4. No `PATCH`, `faixa_horario_id: null` dá `422`: a escolha automática só existe na criação.
- **`cancelar`:** o corpo é `{ "motivo": "..." }`, obrigatório, não vazio, até 200 caracteres (P-4). Grava `cancelado_por`, `cancelado_em` e `motivo_cancelamento`.
- O registro de auditoria guarda o responsável por edições e cancelamentos, sem dados pessoais além do necessário (RNF-010, RNF-013).

### 6.6 Status

| Status | Quando |
|---|---|
| `AGENDADO` | Criado, ou voltou de uma operação cancelada no mesmo dia (spec 006 §6.2). |
| `EM_ANDAMENTO` | Tem operação aberta. Continua assim depois da meia-noite, porque a volta não reaplica a RN-014. |
| `CONCLUIDO` | Operação `FINALIZADA`. |
| `CANCELADO` | Cancelado pela rota da §6.5. |
| `EXPIRADO` | Era `AGENDADO` e o dia acabou, inclusive quando a operação é cancelada em um dia posterior. |

Nenhuma resposta traz `AGENDADO` com data passada, e o filtro `status` segue a mesma regra, sem depender de uma tarefa agendada ter rodado.

### 6.7 Faixas (P-5)

- Faixas ativas não podem se sobrepor: `409 FAIXA_SOBREPOSTA`. Podem ser vizinhas, com o fim de uma igual ao início da outra. Assim, "primeira faixa" e RN-014 têm só uma leitura.
- Mudar `hora_inicio` ou `hora_fim` com agendamento `AGENDADO` ou `EM_ANDAMENTO` naquela faixa, hoje ou depois: `409 FAIXA_COM_AGENDAMENTOS`. Para mudar o horário, desative a faixa e crie outra.
- Reduzir a `capacidade` abaixo do ocupado é permitido: os agendamentos existentes continuam, e não entram novos até haver vaga.
- Desativar uma faixa é permitido: os agendamentos existentes continuam válidos, e não entram novos.

### 6.8 Referências e cadastros

- Em `CARGA`, `codigo_nota` preenchido dá `422 CODIGO_NOTA_NAO_PERMITIDO`, inclusive em um `PATCH` que mude o tipo sem limpar o campo (P-6).
- O backend não copia a transportadora do veículo. A tela pode pré-preencher o campo, e quem agenda confirma.
- Desativar um veículo ou motorista depois de agendar não muda o agendamento, mas a entrada não é autorizada (spec 007 §6.2).

### 6.9 Falhas

| Situação | Resposta |
|---|---|
| Banco indisponível | `500 ERRO_INTERNO`. Nada é gravado, e o frontend não supõe que salvou. |
| Id de referência inexistente ou inativo | `422 CAMPO_INVALIDO`, com o campo indicado. |
| Corpo com campo desconhecido ou somente leitura | `422 CAMPO_INVALIDO`. |
| Cancelamento e entrada do caminhão ao mesmo tempo | Transação no banco: se a operação nasceu antes, `409 STATUS_NAO_PERMITE`; se o cancelamento veio antes, a entrada não é autorizada. |
| Fuso do pátio sem configuração | O backend não inicia, porque não dá para saber o dia com segurança. |
| Tempo de resposta | Sem número definido; não há dado para isso. |

### 6.10 Códigos em `campos[].codigo`

`DATA_NO_PASSADO`, `FAIXA_SEM_VAGA`, `FAIXA_ENCERRADA`, `SEM_FAIXA_DISPONIVEL`, `VEICULO_JA_AGENDADO`, `STATUS_NAO_PERMITE`, `CODIGO_NOTA_NAO_PERMITIDO`, `FAIXA_SOBREPOSTA`, `FAIXA_COM_AGENDAMENTOS`, além dos códigos de validação comuns da spec 007.

## 7. Dados pessoais

- A placa e o nome do motorista só aparecem para quem tem `CONSULTAR_AGENDAMENTOS`. A query string fica fora dos registros de acesso (spec 007 §3.4).
- `codigo_nota` e `observacao` não vão para logs. O campo `observacao` é texto livre e pode conter dados pessoais.

## 8. Critérios de aceitação

Verificáveis no backend (testes de API) e no frontend (respostas simuladas com estes tipos, S-6).

| CA | Critério |
|---|---|
| CA-001 | As rotas da §4 existem, e nem agendamentos nem faixas aceitam `DELETE`. |
| CA-002 | Sem sessão: `401`. Com sessão sem a permissão da rota: `403`. |
| CA-003 | `OPERADOR` consulta e cria, mas `PATCH` e `cancelar` dão `403` (RN-013). |
| CA-004 | `AUDITOR` consulta agendamentos, mas criar, editar, cancelar e as rotas de faixa dão `403` (P-1). |
| CA-005 | Nenhuma resposta de agendamento contém o CPF. |
| CA-006 | Sem `faixa_horario_id`, a criação usa a primeira faixa ativa, não encerrada e com vaga, e a resposta a informa. |
| CA-007 | Faixa cheia dá `409 FAIXA_SEM_VAGA`, e nada é criado. |
| CA-008 | Dois `POST` simultâneos pela última vaga resultam em um `201` e um `409`. |
| CA-009 | Cancelar libera a vaga, e `CONCLUIDO` não libera. |
| CA-010 | Faixa já encerrada hoje dá `409 FAIXA_ENCERRADA`; a mesma faixa em dia futuro é aceita (P-3). |
| CA-011 | `data_prevista` passada dá `422 DATA_NO_PASSADO`. |
| CA-012 | Com um agendamento aberto, um novo para o mesmo veículo dá `409 VEICULO_JA_AGENDADO`, no mesmo dia ou em outro, inclusive com dois pedidos simultâneos; depois de encerrado o primeiro, é aceito (P-2). |
| CA-013 | `PATCH` e `cancelar` em agendamento fora de `AGENDADO` dão `409 STATUS_NAO_PERMITE`. |
| CA-014 | `cancelar` sem motivo dá `422`; com motivo, grava responsável, momento e motivo (P-4). |
| CA-015 | `PATCH` altera só os campos enviados; campo somente leitura, desconhecido ou `faixa_horario_id: null` dá `422`. |
| CA-016 | `AGENDADO` de ontem aparece como `EXPIRADO`, inclusive no filtro, e não impede um novo agendamento do veículo (§6.4). |
| CA-017 | `codigo_nota` em `CARGA` dá `422`; em `DESCARGA`, é guardado como enviado (P-6). |
| CA-018 | Faixa sobreposta dá `409`; faixa vizinha é aceita (P-5). |
| CA-019 | Mudar o horário de faixa com agendamento ativo dá `409`; reduzir a capacidade abaixo do ocupado é aceito, e `vagas_livres` fica em 0 (P-5). |
| CA-020 | "Hoje" segue o fuso configurado: perto da meia-noite, a data vem do fuso do pátio, e não do fuso do servidor. |
| CA-021 | Os registros de acesso e os logs não contêm a query string, `codigo_nota` nem `observacao`. |

## 9. Impacto

- **Backend (BE-702):** rotas, esquemas e regras; depende da BE-503 e do login (CT-106).
- **Frontend (FE-302):** telas de agendamento e de faixas usam só este contrato.
- **Esquema (BE-502), sem alterar agora:** nova tabela `faixa_horario`; `agendamento.faixa_horario_id` substitui `janela_inicio` e `janela_fim`; novos `origem`, `codigo_nota` e campos de cancelamento; `criado_por` aceita vazio; unicidade parcial por veículo entre os agendamentos abertos (P-2); proteção contra sobreposição de faixas. Como o status `EXPIRADO` não depende de tarefa agendada (§6.6), a criação precisa gravar a expiração dos agendamentos vencidos do veículo na mesma transação, antes de testar a unicidade.
- **ADR-0004:** nova permissão `CONSULTAR_AGENDAMENTOS` (P-1).
- **Requisitos:** novas RN-023 e RN-024; RN-013 passa a exigir o motivo do cancelamento.
- **Orquestração (BE-601):** usa o fuso configurado na RN-014 e aplica o efeito da spec 006 §6.2.
- **Segurança operacional:** nenhuma ação física. O efeito é indireto, porque o agendamento é uma das condições da RN-002. A §6.4 reduz paradas por ambiguidade, sem mudar a regra de não escolher sozinho entre candidatos (`AGENTS.md` §7.2).
- **Reversibilidade:** alta, sem código ainda.

## 10. Riscos conhecidos

- **Agendamento errado bloqueia o veículo:** o operador cria, mas não cancela (RN-013). Se o erro for dele ou do motorista, só o administrador resolve; até lá, ou até o agendamento expirar, a §6.4 impede um novo para aquele veículo.
- **Dia fechado:** sem calendário, não há como impedir agendamentos em um dia fechado, a não ser desativando as faixas, o que afeta todos os dias.

## 11. Decisões do autor (2026-11-04)

| ID | Pergunta | Decisão |
|---|---|---|
| P-1 | Quem consulta os agendamentos? | `ADMINISTRADOR`, `OPERADOR` e `AUDITOR`, com a nova permissão `CONSULTAR_AGENDAMENTOS`. O auditor vê placa e nome do motorista, mas não o CPF. |
| P-2 | Um veículo pode ter dois agendamentos ativos no mesmo dia? | **Não, e em nenhum momento:** "só aceitar novo agendamento no dia caso o outro tenha sido encerrado, a placa não pode ter dois agendamentos abertos ao mesmo tempo". RN-023. |
| P-3 | Dá para criar agendamento hoje em uma faixa que já terminou? | Não. Faixa em andamento é aceita, e a RN-014 continua valendo para quem já tinha agendamento e se atrasou. RN-024. |
| P-4 | O cancelamento exige motivo? | Sim, com o responsável registrado. |
| P-5 | Regras das faixas: valem todos os dias, não se sobrepõem, não cruzam a meia-noite, horário não muda com agendamento ativo, capacidade pode cair abaixo do ocupado? | Sim para todas. |
| P-6 | `codigo_nota` só em descarga, opcional na tela interna e sem validar o formato? | Sim. A obrigatoriedade para o motorista fica para a CT-107. |
| P-7 | Há limite de antecedência para agendar? | Não. |
