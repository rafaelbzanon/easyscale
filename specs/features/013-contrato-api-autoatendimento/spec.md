# Spec 013 — Contrato da API de autoatendimento

- **Trilha:** Contrato
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** CT-107; implementação no backend (`api/`), uso na FE-307 (tela do motorista) — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-004, RF-029, RF-033, RN-001, RN-002, RN-014, RN-015, RN-021, RN-023, RN-024, RNF-013, RNF-014
- **Decisões:** ADR-0004 §4.4 (autoatendimento sem login); spec 008 §6 (regras de agendamento e faixas); spec 007 §3 (regras comuns da API); spec 012 §6.9 (CSRF e origem)

---

## 1. Contexto e origem

- O motorista cria o próprio agendamento numa tela própria, sem login e sem operador, por totem ou pela rede do pátio. Na descarga, informa o código da nota, digitado ou escaneado (RF-033, ADR-0004 P-B).
- É a única rota sem sessão, e tem as barreiras do ADR-0004 §4.4: rede, cadastro, dados, abuso e alcance.
- As regras de data, faixa, vaga e um agendamento aberto por veículo são as da spec 008 §6, sem mudança.
- O ADR-0005 §5 diz que o autoatendimento não usa o canal de eventos.

## 2. Objetivo

Definir as rotas do autoatendimento, a resposta que não revela o que falhou, o limite de tentativas e a configuração, com critérios verificáveis pelos dois lados.

## 3. Fora de escopo

- Consultar, editar ou cancelar agendamentos sem login (ADR-0004 §4.4 item 5).
- Verificar a autenticidade ou o formato do código da nota (RN-021).
- Leitura do código por câmera na tela: é da FE-307. Para a API, o código é sempre texto.
- Canal de eventos (ADR-0005 §5).
- Acesso pela internet: exige um novo ADR (ADR-0004 §4.4).

## 4. Rotas

Nenhuma rota exige sessão. Todas passam pela barreira de rede da §6.1. A forma das respostas e os erros seguem a spec 007 §3, e o `POST` segue a spec 012 §6.9.

| Método e rota | Efeito | Sucesso |
|---|---|---|
| `GET /api/autoatendimento/produtos` | Produtos ativos, para escolher (§5.2) | 200 |
| `GET /api/autoatendimento/disponibilidade?data=` | Vagas das faixas ativas no dia, no formato da spec 008 §5.3 | 200 |
| `POST /api/autoatendimento/agendamentos` | Cria um agendamento com `origem` `AUTOATENDIMENTO` (§5.1) | 201 (§5.1) |

Nenhuma outra rota da API fica acessível sem sessão por causa desta spec.

## 5. Campos

### 5.1 Criação

Corpo do `POST`:

| Campo | Tipo | Obr. | Validação |
|---|---|---|---|
| `placa` | texto | Sim | Normalizada como na spec 007 §6.1, inclusive recusando correção de OCR (`422 PLACA_INVALIDA`). |
| `cpf` | texto de 11 | Sim | Só dígitos, dígitos verificadores válidos (spec 007 §5.2). |
| `tipo_operacao` | texto | Sim | `CARGA` ou `DESCARGA`. |
| `produto_id` | inteiro | Sim | Produto ativo. |
| `data_prevista` | data | Sim | Hoje ou depois, no fuso do pátio (spec 008 §6.1). |
| `faixa_horario_id` | inteiro | — | Como na spec 008 §6.3: ausente ou `null`, o backend usa a primeira faixa com vaga. |
| `codigo_nota` | texto até 100 | Em `DESCARGA` | **Obrigatório em `DESCARGA`** e proibido em `CARGA` (§6.4). |

Campo desconhecido dá `422 CAMPO_INVALIDO`. Não há `transportadora_id` nem `observacao` (P-1).

Resposta `201`, só com o necessário para o motorista conferir, sem nenhum dado de cadastro (ADR-0004 §4.4 item 3):

```json
{
  "agendamento_id": 42,
  "tipo_operacao": "DESCARGA",
  "data_prevista": "2026-11-08",
  "faixa_hora_inicio": "08:00",
  "faixa_hora_fim": "10:00"
}
```

Os valores acima são só um exemplo.

### 5.2 Produtos

Item: `id`, `codigo` e `descricao`, só dos produtos ativos. Lista paginada como na spec 007 §3.3, com o filtro `busca` (código ou descrição). Ordem: `descricao`, `id`.

## 6. Regras

### 6.1 Rede (ADR-0004 §4.4 item 1)

- A lista de redes vem de `PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES`, sem valor padrão.
- **Sem a variável, ou vazia, as três rotas ficam desligadas:** respondem `404 NAO_ENCONTRADO`, como se não existissem.
- Com a variável, um pedido de endereço fora das redes dá `403 REDE_NAO_PERMITIDA`, sem efeito.
- O endereço conferido é o do cliente. Se houver um proxy na frente (INT-001), ele precisa repassar o endereço real, e o backend só aceita esse repasse do proxy configurado na INT-001. Sem isso, todos os pedidos teriam o endereço do proxy, e a barreira não valeria (§9).

### 6.2 Ordem da verificação do `POST`

1. Rede (§6.1).
2. Bloqueio da origem (§6.5): `429 AUTOATENDIMENTO_BLOQUEADO`.
3. CSRF e tipo de conteúdo (spec 012 §6.9).
4. Formato dos campos (§5.1): `422 CAMPO_INVALIDO` ou `PLACA_INVALIDA`, com o campo indicado. Erro de formato não diz nada sobre o cadastro e não conta como tentativa.
5. Cadastro (§6.3): `422 DADOS_NAO_CONFEREM`, que conta como tentativa.
6. Regras da spec 008 §6 (§6.4).

Cada passo só roda se o anterior passou. Nada é criado se algum falhar.

### 6.3 Cadastro (RN-021, ADR-0004 §4.4 itens 2 e 3)

- A placa precisa corresponder, pela `chave_comparacao` (spec 003), a um veículo **ativo**, e o CPF a um motorista **ativo** (spec 007 §6.2).
- Não se exige que o motorista seja o `motorista_padrao_id` do veículo: o RN-021 pede só que os dois estejam cadastrados.
- Placa inexistente, CPF inexistente, veículo inativo, motorista inativo ou mais de um desses ao mesmo tempo dão **a mesma resposta**: `422 DADOS_NAO_CONFEREM`, com a mesma `mensagem` e `campos` vazio.

### 6.4 Regras de agendamento (spec 008 §6)

Só depois do cadastro conferido, valem sem mudança e com os mesmos códigos:

- data no passado: `422 DATA_NO_PASSADO`;
- faixa sem vaga, encerrada ou nenhuma disponível: `409 FAIXA_SEM_VAGA`, `FAIXA_ENCERRADA` ou `SEM_FAIXA_DISPONIVEL` (RN-014, RN-015, RN-024);
- veículo com agendamento aberto: `409 VEICULO_JA_AGENDADO` (RN-023);
- `codigo_nota` em `CARGA`: `422 CODIGO_NOTA_NAO_PERMITIDO`;
- `codigo_nota` ausente ou vazio em `DESCARGA`: `422 CODIGO_NOTA_OBRIGATORIO`. Base: o RF-033 diz que na descarga o motorista "informa também o código da nota", e a spec 008 P-6 deixou a obrigatoriedade para este contrato.

Esses códigos aparecem só para quem já informou placa e CPF que conferem, então não revelam o cadastro a quem não os conhece.

O agendamento criado tem `origem` `AUTOATENDIMENTO`, `criado_por` `null`, `transportadora_id` `null` e `status` `AGENDADO` (spec 008 §5.1). Depois de criado, segue a spec 008 como qualquer outro.

### 6.5 Limite por origem (ADR-0004 §4.4 item 4)

- Conta as respostas `DADOS_NAO_CONFEREM` por endereço de origem.
- Depois de `PESAGEM_SEGURANCA_AUTOATENDIMENTO_TENTATIVAS_MAXIMAS` falhas seguidas, a origem fica bloqueada por `PESAGEM_SEGURANCA_AUTOATENDIMENTO_BLOQUEIO_S` segundos. Durante o bloqueio, todo `POST` dá `429 AUTOATENDIMENTO_BLOQUEADO`, sem conferir o cadastro, e não prolonga o bloqueio.
- Uma criação bem-sucedida zera o contador da origem, e o fim do bloqueio também.
- As rotas `GET` não contam e não são bloqueadas: não revelam dados pessoais.
- O contador sobrevive a um reinício do backend, como o da spec 012 §6.8.
- Um totem compartilhado é uma única origem: um motorista que erra pode bloquear o totem para os outros pelo tempo configurado (§9).

### 6.6 Dados pessoais (RNF-013)

- Logs e registros de acesso não contêm placa, CPF nem `codigo_nota`. A query string já fica fora (spec 007 §3.4).
- A auditoria registra a criação com `origem` `AUTOATENDIMENTO` e as falhas de cadastro só com a origem e o instante, sem o que foi digitado.

### 6.7 Configuração

Sem valor padrão no código (`AMBIENTE.md` §8):

| Variável | Conteúdo | Validação |
|---|---|---|
| `PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES` | Redes aceitas, em notação CIDR, separadas por vírgula | Cada item é uma rede IPv4 ou IPv6 válida. Ausente ou vazia: rotas desligadas (§6.1). |
| `PESAGEM_SEGURANCA_AUTOATENDIMENTO_TENTATIVAS_MAXIMAS` | Falhas seguidas que bloqueiam a origem | Inteiro > 0. |
| `PESAGEM_SEGURANCA_AUTOATENDIMENTO_BLOQUEIO_S` | Duração do bloqueio, em segundos | Inteiro > 0. |

Com as redes configuradas, as outras duas são obrigatórias. Se faltar uma, ou qualquer valor for inválido, o backend não inicia. Sem as redes, as outras duas são ignoradas.

### 6.8 Falhas

| Situação | Resposta |
|---|---|
| Banco indisponível | `500 ERRO_INTERNO`. Nada é gravado, e a tela não mostra o agendamento como criado. |
| Dois pedidos pela última vaga ou para o mesmo veículo | Um `201` e um `409`, pelas transações da spec 008 §6.2 e §6.4. |
| Fuso do pátio sem configuração | O backend não inicia (spec 008 §6.9). |
| Tempo de resposta | Sem número definido; não há dado para isso. |

### 6.9 Códigos novos

| Status | `codigo` | Quando |
|---|---|---|
| 403 | `REDE_NAO_PERMITIDA` | Origem fora das redes (§6.1). |
| 422 | `DADOS_NAO_CONFEREM` | Placa ou CPF não conferem (§6.3). |
| 429 | `AUTOATENDIMENTO_BLOQUEADO` | Origem bloqueada (§6.5). |

Em `campos[].codigo`: `CODIGO_NOTA_OBRIGATORIO`, além dos da spec 008 §6.10 e dos comuns da spec 007.

## 7. Critérios de aceitação

Verificáveis no backend (testes de API) e no frontend (respostas simuladas com estes tipos, S-6).

| CA | Critério |
|---|---|
| CA-001 | Sem `PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES`, as três rotas dão `404`. |
| CA-002 | Com as redes configuradas, um pedido de fora delas dá `403 REDE_NAO_PERMITIDA` nas três rotas, e nada é criado. |
| CA-003 | Placa e CPF de veículo e motorista ativos, com faixa com vaga, criam o agendamento com `origem` `AUTOATENDIMENTO` e `criado_por` `null`, e a resposta só tem os campos da §5.1. |
| CA-004 | Placa inexistente, CPF inexistente, veículo inativo e motorista inativo dão respostas idênticas `422 DADOS_NAO_CONFEREM`, e nada é criado. |
| CA-005 | Depois do número configurado de `DADOS_NAO_CONFEREM` seguidos, a origem recebe `429`, inclusive com dados certos; depois do tempo configurado, volta a funcionar; outra origem não é afetada. |
| CA-006 | Erro de formato (CPF com dígito errado, placa inválida) dá `422` com o campo indicado e não conta como tentativa. |
| CA-007 | Os códigos da spec 008 §6.4 aparecem nas mesmas situações: faixa cheia, faixa encerrada, sem faixa, data passada, veículo já agendado. |
| CA-008 | Em `DESCARGA`, sem `codigo_nota` dá `422 CODIGO_NOTA_OBRIGATORIO`; com ele, é guardado como enviado. Em `CARGA`, com `codigo_nota` dá `422 CODIGO_NOTA_NAO_PERMITIDO`. |
| CA-009 | Sem `faixa_horario_id`, usa a primeira faixa ativa, não encerrada e com vaga, e a resposta mostra o horário. |
| CA-010 | Dois `POST` simultâneos pela última vaga resultam em um `201` e um `409`. |
| CA-011 | O `POST` sem `Origin` permitido ou sem JSON é recusado como na spec 012 §6.9. |
| CA-012 | Nenhuma rota de consulta, edição ou cancelamento de agendamento fica acessível sem sessão. |
| CA-013 | Logs, registros de acesso e auditoria não contêm placa, CPF nem `codigo_nota`. |
| CA-014 | Com as redes configuradas e sem limite de tentativas ou com valor inválido, o backend não inicia. |

## 8. Impacto

- **Backend:** três rotas, conferência de rede e contador por origem; reaproveita a criação da spec 008. Nenhuma dependência nova (`ipaddress` da biblioteca padrão).
- **Frontend (FE-307):** tela do motorista; não usa sessão nem canal de eventos. Trata `DADOS_NAO_CONFEREM` com uma só mensagem.
- **Esquema (BE-502, spec 014), sem alterar agora:** contador de tentativas por origem, que sobrevive a reinício; `agendamento.origem`, `criado_por` vazio e `codigo_nota` já previstos na spec 008.
- **Integração (INT-001):** o proxy precisa repassar o endereço real do cliente, e só ele pode fazer isso (§6.1).
- **Requisitos:** o RF-033 passa a ter o código da nota obrigatório na descarga pelo motorista.
- **Segurança operacional:** nenhuma ação física. O efeito é indireto: o agendamento é uma das condições da RN-002, e a entrada continua exigindo a placa lida com confiança e o agendamento válido.
- **Reversibilidade:** alta, sem código ainda.

## 9. Riscos conhecidos

- **CPF não é segredo:** quem conhece a placa e o CPF de um motorista agenda por ele. Risco aceito no ADR-0004 §4.4, só com o acesso limitado ao pátio.
- **Proxy mal configurado:** se o backend vir só o endereço do proxy, a barreira de rede e o limite por origem deixam de valer (§6.1).
- **Totem bloqueado:** um único endereço para todos os motoristas faz o erro de um bloquear os outros pelo tempo configurado (§6.5).

## 10. Perguntas em aberto

| ID | Pergunta | Situação até a resposta |
|---|---|---|
| P-1 | O agendamento do motorista deve ter transportadora? O motorista não conhece o `id`, e a spec 008 §6.8 diz que o backend não copia a transportadora do veículo. | Fica `null`, permitido pelo RF-004 ("quando houver"). A tela interna pode completar depois, com `GERENCIAR_AGENDAMENTOS`. |
