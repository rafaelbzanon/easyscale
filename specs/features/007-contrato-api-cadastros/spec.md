# Spec 007 — Contrato da API de cadastros

- **Trilha:** Contrato
- **Status:** Aprovada pelo autor em 2026-11-04 (respostas às perguntas da §10)
- **Data:** 2026-11-04
- **Tarefa:** CT-101; implementação na BE-701, uso na FE-301 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-001, RF-002, RF-003, RF-025, RF-026, RN-002, RN-006, RN-008, RN-017, RNF-013, RNF-014
- **Decisões:** ADR-0004 (sessão e permissões)

---

## 1. Contexto e origem

- O artigo prevê os cadastros de veículos, motoristas e transportadoras **[ARTIGO §1, §2, §4]**. Produtos e tipos de veículo foram incluídos pelo autor (Q-14).
- Os campos partem do `docs/modelo-dados/schema.sql`, que é referência **[PROPOSTA]** (C-002). A BE-502 ajusta o esquema a este contrato.
- Frontend e backend só se conhecem por este documento (S-3). Mudar algo aqui exige uma tarefa CT-9xx (S-4).

## 2. Objetivo

Definir rotas, campos, erros e permissões dos cinco cadastros, com critérios verificáveis pelos dois lados. A §3 vale também para os próximos contratos.

## 3. Regras comuns da API

### 3.1 Formato

- Prefixo `/api`; JSON em UTF-8; campos em `snake_case` (`CONVENCOES.md` §5).
- Datas no padrão ISO 8601. `Decimal` trafega como **texto** (`"15000.125"`), para não perder precisão em JSON.
- Campo opcional sem valor vem como `null`, nunca omitido nas respostas.

### 3.2 Erros

Toda resposta de erro tem este corpo, inclusive a validação automática do framework, que precisa ser convertida:

```json
{
  "erro": {
    "codigo": "CAMPO_INVALIDO",
    "mensagem": "Texto para o usuário.",
    "campos": [{ "campo": "placa", "codigo": "PLACA_INVALIDA" }]
  }
}
```

`campos` é uma lista vazia quando o erro não se refere a um campo. O frontend decide pelo `codigo`, nunca pelo texto. A `mensagem` nunca traz detalhe interno.

| Status | `codigo` | Quando |
|---|---|---|
| 401 | `NAO_AUTENTICADO` | Sem sessão válida. |
| 403 | `SEM_PERMISSAO` | A sessão não tem a permissão da rota. |
| 404 | `NAO_ENCONTRADO` | O id não existe. |
| 409 | `CONFLITO` | Duplicidade ou estado que impede a ação (§6.3); `campos` indica a causa. |
| 422 | `CAMPO_INVALIDO` | Corpo ou parâmetro inválido (§5). |
| 500 | `ERRO_INTERNO` | Falha inesperada. Sem detalhe interno. |

### 3.3 Listas

Parâmetros `pagina` (começa em 1) e `tamanho_pagina`. O máximo vem de configuração, e um valor acima dele dá `422`.

```json
{ "itens": [], "total": 0, "pagina": 1, "tamanho_pagina": 50 }
```

Sem `tamanho_pagina` na requisição, vale o padrão configurado; o `50` acima é só um exemplo. A ordem é fixa em cada recurso, para que a paginação seja estável.

### 3.4 Dados pessoais

- Registros de acesso **não gravam a query string**, porque ela pode trazer placa ou nome (RNF-013).
- Respostas e logs não trazem CPF completo fora do previsto na §4.2.

## 4. Permissões e rotas

### 4.1 Rotas

As cinco famílias de rota têm a mesma forma:

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/{recurso}` | Lista, com filtros (§5) | 200 | `CONSULTAR_CADASTROS` |
| `GET /api/{recurso}/{id}` | Um item | 200 | `CONSULTAR_CADASTROS` |
| `POST /api/{recurso}` | Cria | 201, com o item | `GERENCIAR_CADASTROS` |
| `PATCH /api/{recurso}/{id}` | Altera só os campos enviados, inclusive `ativo` | 200, com o item | `GERENCIAR_CADASTROS` |

Recursos: `transportadoras`, `motoristas`, `tipos-veiculo`, `veiculos` e `produtos`. **Não há `DELETE`** (P-1).

### 4.2 Perfis (P-3, P-4)

| Perfil | Acesso |
|---|---|
| `ADMINISTRADOR` | Consulta e altera; vê o CPF completo. |
| `OPERADOR` | Só consulta, para criar agendamentos; vê o CPF mascarado. |
| `AUDITOR` | Sem acesso: ele acompanha os processos pelas telas de operação e histórico. |

`CONSULTAR_CADASTROS` é uma permissão nova, já incluída no ADR-0004. O CPF completo só aparece em `GET`, `POST` e `PATCH` de um item, e só para quem tem `GERENCIAR_CADASTROS`. Nos demais casos, `cpf` vem `null`.

## 5. Recursos e campos

Em todos: `id` (inteiro, somente leitura) e `ativo` (booleano, `true` ao criar). **Obr.** indica campo obrigatório na criação.

### 5.1 `transportadoras`

| Campo | Tipo | Obr. | Validação |
|---|---|---|---|
| `razao_social` | texto até 100 | Sim | Não vazio. |
| `nome_fantasia` | texto até 100 | — | — |
| `cnpj` | texto de 14 | Sim | Único; sem máscara; dígitos verificadores válidos. Aceita o CNPJ alfanumérico da Receita (a regra exata será confirmada na BE-701). |
| `telefone` | texto até 15 | — | Só dígitos. |
| `email` | texto até 100 | — | Formato de e-mail. |

Filtros: `ativo`, `busca` (razão social ou nome fantasia). Ordem: `razao_social`, `id`.

### 5.2 `motoristas`

| Campo | Tipo | Obr. | Validação |
|---|---|---|---|
| `nome` | texto até 100 | Sim | Não vazio. |
| `cpf` | texto de 11 | Sim | Único; sem máscara; dígitos verificadores válidos. Na resposta, segue a §4.2. |
| `cpf_mascarado` | texto | Só leitura | Esconde os 3 primeiros dígitos e o verificador: `***.456.789-**`. |
| `transportadora_id` | inteiro | — | Transportadora ativa. |
| `cnh_numero` | texto até 20 | — | — |
| `cnh_categoria` | texto até 2 | — | — |
| `data_validade_cnh` | data | — | Informativa (P-2). |
| `telefone` | texto até 15 | — | Só dígitos. |

Filtros: `ativo`, `transportadora_id`, `busca` (nome). Ordem: `nome`, `id`.

### 5.3 `tipos-veiculo`

| Campo | Tipo | Obr. | Validação |
|---|---|---|---|
| `descricao` | texto até 100 | Sim | Único, sem diferenciar maiúsculas. |

Filtros: `ativo`. Ordem: `descricao`, `id`.

### 5.4 `veiculos`

| Campo | Tipo | Obr. | Validação |
|---|---|---|---|
| `placa` | texto | Sim | Ver a §6.1. |
| `formato_placa` | texto | Só leitura | `ANTIGO` ou `MERCOSUL` (spec 003). |
| `tipo_veiculo_id` | inteiro | Sim | Tipo ativo. |
| `transportadora_id` | inteiro | — | Transportadora ativa. Vazio para veículo sem transportadora, como o de motorista autônomo (P-5). |
| `motorista_padrao_id` | inteiro | — | Motorista ativo. |
| `marca` | texto até 30 | — | — |
| `modelo` | texto até 30 | — | — |
| `eixos` | inteiro | — | Maior que 0. |
| `tara_kg` | decimal, 3 casas | — | ≥ 0. Informativa: nunca substitui um peso medido (RN-006). |
| `capacidade_kg` | decimal, 3 casas | — | > 0. |

Filtros: `ativo`, `transportadora_id`, `placa` (compara pela `chave_comparacao`). Ordem: `placa`, `id`.

### 5.5 `produtos`

| Campo | Tipo | Obr. | Validação |
|---|---|---|---|
| `codigo` | texto até 30 | Sim | Único. |
| `descricao` | texto até 100 | Sim | Não vazio. |
| `unidade` | texto até 5 | — | Padrão `KG`. |

Filtros: `ativo`, `busca` (código ou descrição). Ordem: `descricao`, `id`.

## 6. Regras

### 6.1 Placa do veículo

- A entrada aceita minúsculas, hífen e espaço; a resposta traz a `placa` já normalizada, sem separador.
- Usa `normalizar_placa` (spec 003). **Toda correção de OCR é recusada aqui**: se a normalização trocar uma letra por dígito ou o contrário, a resposta é `422 PLACA_INVALIDA`. As correções existem para leituras de câmera; aplicá-las em um cadastro digitado mudaria a placa sem o usuário perceber.
- A unicidade é pela `chave_comparacao` (spec 003), então `ABC1234` e `ABC1C34` são o mesmo veículo: `409`.

### 6.2 Cadastro inativo

- Não aparece nas listas de seleção: o frontend filtra por `ativo=true`.
- Não pode ser referenciado em um novo cadastro ou agendamento (`422`).
- **Veículo ou motorista inativo não é autorizado na entrada** (RN-002 e RN-021).

### 6.3 Mudança com operação aberta

Retornam `409`, para não alterar uma operação em curso (RN-008):
- desativar veículo, motorista ou transportadora ligados a uma operação aberta;
- alterar a `placa` de um veículo com operação aberta.

As operações encerradas mantêm os dados do momento em que ocorreram (C-002 item 15).

### 6.4 Falhas

| Situação | Resposta |
|---|---|
| Banco indisponível | `500 ERRO_INTERNO`. Nada é gravado. O frontend mostra erro e não supõe que salvou. |
| Dois pedidos criam o mesmo CPF, CNPJ ou placa | Um recebe `201`, o outro `409`, garantido pela unicidade no banco. |
| Id de referência inexistente ou inativo | `422 CAMPO_INVALIDO`, com o campo indicado. |
| `PATCH` com campo somente leitura ou desconhecido | `422 CAMPO_INVALIDO`. |
| Tempo de resposta | Sem número definido; não há dado para isso. |

## 7. Fora de escopo

- Faixas de horário (CT-102), usuários (CT-106) e documentos do motorista (Q-03).
- Consulta externa de CPF, CNPJ ou placa.
- Importação em massa.

## 8. Critérios de aceitação

Verificáveis no backend (testes de API) e no frontend (respostas simuladas com estes tipos, S-6).

| CA | Critério |
|---|---|
| CA-001 | Os cinco recursos têm as quatro rotas da §4.1, e nenhum aceita `DELETE`. |
| CA-002 | Sem sessão: `401`. Com sessão sem a permissão: `403`. |
| CA-003 | `OPERADOR` consulta e não altera; `AUDITOR` recebe `403` em tudo. |
| CA-004 | `OPERADOR` e listas recebem `cpf: null` e `cpf_mascarado`; `ADMINISTRADOR` recebe o `cpf` completo no item. |
| CA-005 | Todo erro tem o corpo da §3.2, inclusive a validação automática. |
| CA-006 | A lista traz `itens`, `total`, `pagina` e `tamanho_pagina`; um valor acima do máximo dá `422`. |
| CA-007 | `abc-1d23` é salva como `ABC1D23`, com `formato_placa` `MERCOSUL`. |
| CA-008 | Uma placa que exigiria correção de OCR, como `ABCO123`, dá `422 PLACA_INVALIDA` e nada é salvo. |
| CA-009 | Com `ABC1234` cadastrada, criar `ABC1C34` dá `409`. |
| CA-010 | CPF ou CNPJ com dígito verificador errado dá `422`; repetido dá `409`. |
| CA-011 | Referência a id inexistente ou inativo dá `422`, com o campo indicado. |
| CA-012 | `PATCH` altera só os campos enviados; campo somente leitura ou desconhecido dá `422`. |
| CA-013 | Desativar um cadastro ligado a uma operação aberta dá `409`; sem operação, o `ativo` vira `false` e o item continua consultável. |
| CA-014 | `tara_kg` e `capacidade_kg` trafegam como texto, sem perda de casas. |
| CA-015 | Os registros de acesso não contêm a query string nem o CPF. |
| CA-016 | Dois `POST` simultâneos com a mesma placa resultam em um `201` e um `409`. |

## 9. Impacto

- **Backend (BE-701):** rotas, esquemas, conversão de erros; depende da BE-503 e do login (CT-106).
- **Frontend (FE-301):** telas de cadastro usam só este contrato.
- **Esquema (BE-502), sem alterar agora:** unicidade por `chave_comparacao`; retirar `rg` (P-2); `veiculo.transportadora_id` e `agendamento.transportadora_id` passam a aceitar vazio (P-5); `ativo` nos cadastros já existe.
- **ADR-0004:** nova permissão `CONSULTAR_CADASTROS`.
- **Regras:** "veículo cadastrado" na RN-002 significa cadastrado **e ativo**, e a transportadora no agendamento vale só quando houver (RF-004).
- **Segurança operacional:** nenhuma ação física; o efeito é indireto, porque o cadastro define quem pode ser autorizado.
- **Reversibilidade:** alta, sem código ainda.

## 10. Decisões do autor (2026-11-04)

| ID | Pergunta | Decisão |
|---|---|---|
| P-1 | Só desativar, sem apagar cadastros? | **Sim.** Apagar quebraria o histórico das pesagens. A exclusão a pedido do titular fica para a discussão de LGPD (Q-08). |
| P-2 | Quais dados do motorista guardar, e CNH vencida bloqueia? | Retirar o `rg`, que nenhum requisito usa, e manter a CNH opcional, **sem bloquear a entrada** por validade, porque nenhum requisito pede isso. |
| P-3 | Quem vê o CPF completo? | **Só o administrador.** O operador identifica o motorista pelo nome e pelo CPF mascarado. |
| P-4 | Quem consulta os cadastros? | **Administrador e operador.** O operador cria agendamentos, e o auditor só acompanha os processos. |
| P-5 | Todo veículo precisa de transportadora? | **Não.** O campo é opcional. |
| P-6 | Veículo ou motorista desativado com operação aberta? | **Recusar (`409`)** até a operação terminar ou ser cancelada. |
