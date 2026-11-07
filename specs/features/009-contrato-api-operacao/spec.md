# Spec 009 — Contrato da API da operação

- **Trilha:** Contrato
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** CT-103; implementação na BE-703, uso na FE-303 e na FE-306 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-010, RF-014, RF-015, RF-017, RF-021, RF-023, RF-024, RF-027, RN-002, RN-003, RN-005, RN-007, RN-011, RN-012, RN-014, RN-016, RN-018, RN-019, RN-020, RNF-009, RNF-013, RNF-014
- **Decisões:** ADR-0004 (permissões), ADR-0005 (tempo real); spec 006 (situações e ações); spec 007 §3 (regras comuns da API); spec 012 (sessão e CSRF); spec 015 (orquestração, combinada com o Gyro em 2026-11-07)

---

## 1. Contexto e origem

- A tela operacional mostra em tempo real a chegada do caminhão, a placa reconhecida, a autorização, a situação do agendamento, o peso lido, a etapa e os comandos das cancelas **[ARTIGO §2, §4]** (RF-021).
- As situações, os eventos e as ações manuais são os da spec 006. A decisão de entrada, a leitura da balança, a posição e a liberação de caminhão cancelado são da orquestração (spec 015). Os nomes abaixo foram combinados com o Gyro.
- O canal de eventos é SSE, só de leitura; o estado de verdade vem por `GET` (ADR-0005).
- Frontend e backend só se conhecem por este documento (S-3). Mudar algo aqui exige uma tarefa CT-9xx (S-4).

## 2. Objetivo

Definir as rotas, os campos, os eventos, os erros e as permissões da operação em tempo real e das intervenções manuais, com critérios verificáveis pelos dois lados.

## 3. Fora de escopo

- Lista e eventos de auditoria das pesagens: spec 010 (`GET /api/pesagens`, `GET /api/pesagens/{pesagem_id}/eventos`).
- Imagens, ROIs, histórico de reconhecimentos, rota do estado dos dispositivos e simuladores: spec 011.
- **Abrir ou fechar uma cancela diretamente.** Todo comando sai da máquina de estados (spec 006) ou da liberação da §6.6. O operador pede movimento só pelas ações da §4.2 (RN-007, `AGENTS.md` §7.1.3).
- **Digitar um peso.** Nenhuma rota recebe peso (RN-004, spec 006 §5.3).
- Login, sessão e CSRF: spec 012.

## 4. Rotas e permissões

A forma das respostas, os erros e a paginação seguem a spec 007 §3. As rotas com `POST` seguem a proteção contra CSRF da spec 012 §6.9.

### 4.1 Consulta

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/operacao/estado` | Estado atual (§5.5) | 200 | `CONSULTAR_OPERACAO` |
| `GET /api/operacao/eventos` | Canal SSE (§6.1) | 200, `text/event-stream` | `CONSULTAR_OPERACAO` |
| `GET /api/pesagens/{pesagem_id}` | Uma pesagem, aberta ou encerrada | 200 | `CONSULTAR_OPERACAO` |

### 4.2 Ações

Todas respondem `200` com a `Pesagem` atualizada, exceto a `liberar-entrada`, que responde `201` com a nova `Pesagem`.

| Método e rota | Ação (spec 006) | Permissão |
|---|---|---|
| `POST /api/pesagens/{pesagem_id}/tentar-novamente` | `TENTAR_NOVAMENTE` | `TENTAR_NOVAMENTE` |
| `POST /api/pesagens/{pesagem_id}/confirmar-posicao` | `CONFIRMAR_POSICAO_MANUAL` | `INTERVIR_OPERACAO` |
| `POST /api/pesagens/{pesagem_id}/confirmar-balanca-vazia` | `CONFIRMAR_BALANCA_VAZIA_MANUAL` | `INTERVIR_OPERACAO` |
| `POST /api/pesagens/{pesagem_id}/liberar-retorno` | `LIBERAR_RETORNO_MANUAL` | `INTERVIR_OPERACAO` |
| `POST /api/pesagens/{pesagem_id}/aceitar-peso-final` | `ACEITAR_PESO_FINAL` | `INTERVIR_OPERACAO` |
| `POST /api/pesagens/{pesagem_id}/cancelar` | `CANCELAR` | `INTERVIR_OPERACAO` |
| `POST /api/pesagens/{pesagem_id}/liberar-caminhao` | Liberação de caminhão cancelado (spec 006 §6.4; §6.6) | `LIBERAR_CAMINHAO_CANCELADO` |
| `POST /api/leituras-placa/{leitura_placa_id}/liberar-entrada` | Liberação manual de entrada (RN-016; §6.5) | `INTERVIR_OPERACAO` |

### 4.3 Acesso por perfil (ADR-0004 §4.3, spec 006 §9)

| Perfil | Acesso |
|---|---|
| `ADMINISTRADOR` | Consulta e todas as ações. |
| `OPERADOR` | Consulta, `tentar-novamente` e `liberar-caminhao`. |
| `AUDITOR` | Só consulta. |

## 5. Recursos e campos

Pesos são decimais com 3 casas e trafegam como texto (spec 007 §3.1). Campo sem valor vem `null`.

### 5.1 `Pesagem`

O mesmo objeto é usado na lista da spec 010.

| Campo | Tipo | Conteúdo |
|---|---|---|
| `id` | inteiro | — |
| `versao` | inteiro | Sobe a cada transição (spec 006 §5.5). |
| `situacao` | texto | Um dos 20 valores da spec 006 §5.1. É a **etapa atual**. |
| `situacao_anterior` | texto | Só em `AGUARDANDO_INTERVENCAO`; senão `null`. |
| `motivo_intervencao` | texto | Spec 006 §5.4. Só em `AGUARDANDO_INTERVENCAO`; senão `null`. |
| `comando_pendente` | objeto | `{ "comando": "ABRIR" \| "FECHAR", "cancela": "ENTRADA" \| "SAIDA" }` da situação atual (spec 006 §5.1), ou `null`. |
| `acoes_disponiveis` | lista de texto | Ações da spec 006 §5.3 que a máquina aceita agora, sem considerar o perfil. Vazia nas terminais. |
| `ocupa_balanca` | booleano | A pesagem ocupa a balança (spec 006 §6.3). |
| `aguarda_liberacao_balanca` | booleano | `CANCELADA` com o caminhão ainda na balança (spec 006 §6.4). |
| `liberacao_manual` | booleano | Alguma ação manual substituiu uma decisão automática. |
| `agendamento_id` | inteiro | — |
| `agendamento_status` | texto | Spec 008 §6.6 (situação do agendamento, RF-021). |
| `tipo_operacao` | texto | `CARGA` ou `DESCARGA`. |
| `placa` | texto | Placa do veículo cadastrado. |
| `motorista_nome` | texto | — |
| `transportadora_razao_social` | texto | `null` se não houver. |
| `produto_descricao` | texto | — |
| `data_prevista` | data | Do agendamento. |
| `faixa_hora_inicio`, `faixa_hora_fim` | hora `HH:MM` | Do agendamento. |
| `peso_inicial_kg`, `peso_inicial_em` | decimal, data e hora | Peso **aceito** e registrado (RF-014). |
| `peso_final_kg`, `peso_final_em` | decimal, data e hora | Idem. |
| `peso_liquido_kg` | decimal | Spec 002; pode ser negativo. |
| `classificacao` | texto | `COM_MOVIMENTACAO`, `SEM_MOVIMENTACAO` ou `NEGATIVO_FORA_TOLERANCIA`. |
| `criado_em`, `atualizado_em` | data e hora | — |

`acoes_disponiveis` existe para o frontend não repetir a tabela da spec 006 §6.1. Ele só mostra botões; quem decide é o backend (S-5).

### 5.2 `LeituraPlaca`

Uma decisão sobre uma placa lida no ponto de entrada (spec 015). A spec 011 acrescenta as ROIs e os textos lidos.

| Campo | Tipo | Conteúdo |
|---|---|---|
| `id` | inteiro | — |
| `decisao` | texto | `AUTORIZADA`, `RETORNO_ACEITO` ou `NAO_AUTORIZADA`. |
| `motivo` | texto | §5.3; `null` se não for `NAO_AUTORIZADA`. |
| `placa_lida` | texto | Texto bruto do candidato escolhido; `null` sem placa selecionada. |
| `placa_normalizada` | texto | `null` sem placa selecionada. |
| `confianca` | decimal | De 0 a 1, 3 casas, como texto (spec 005); `null` sem placa selecionada. |
| `pesagem_id` | inteiro | Pesagem criada ou, na volta, a pesagem aberta. Em `NAO_AUTORIZADA`, `null`, ou a pesagem criada pela liberação manual (§6.5). |
| `agendamento_id` | inteiro | `null` se não houver. |
| `imagem_id` | inteiro | Imagem salva da decisão (RN-022); `null` sem imagem. |
| `capturada_em`, `decidida_em` | data e hora | — |

Só se registra uma nova leitura quando a decisão muda em relação à última (spec 015).

### 5.3 Motivos de não autorização

Na ordem de precedência da spec 015:

| Motivo | Origem | Substituível na `liberar-entrada` |
|---|---|---|
| `FALHA_IMAGEM` | Câmera indisponível ou imagem inválida | Sim |
| `FALHA_LEITOR` | Falha do OCR (spec 005) | Sim |
| `SEM_CANDIDATO` | Nenhum texto lido (spec 005) | Sim |
| `PLACA_INVALIDA` | Nenhum texto com formato de placa (RN-017) | Sim |
| `AMBIGUA` | Mais de uma placa (spec 005) | Sim |
| `CONFIANCA_BAIXA` | Abaixo do limiar (RN-002) | Sim |
| `VEICULO_NAO_CADASTRADO` | RN-002 | Não |
| `VEICULO_INATIVO` | Spec 007 §6.2 | Não |
| `OPERACAO_JA_ABERTA` | Veículo com operação aberta fora de `EM_CARGA_DESCARGA` (RN-008) | Não |
| `SEM_AGENDAMENTO` | Nenhum `AGENDADO` de hoje, inclusive de outro dia (RN-014) | Não |
| `AGENDAMENTO_AMBIGUO` | Mais de um agendamento válido (RN-002) | Não |
| `MOTORISTA_INATIVO` | Spec 007 §6.2 | Não |
| `ANTES_DA_FAIXA` | Antes do início da faixa (RN-014) | Sim |

### 5.4 Dispositivos (`EstadoDispositivos`)

O mesmo objeto é usado na spec 011.

```json
{
  "balanca": {
    "modo": "SIMULADO",
    "comunicacao": "OK",
    "motivo_falha": null,
    "comunicacao_em": "2026-11-07T10:00:00-03:00",
    "ultima_leitura": { "peso_kg": "15000.000", "lida_em": "2026-11-07T10:00:00-03:00" },
    "avaliacao_peso": { "aceito": false, "motivo_rejeicao": "INSTAVEL", "avaliada_em": "2026-11-07T10:00:00-03:00" }
  },
  "cancelas": [
    {
      "cancela": "ENTRADA",
      "modo": "SIMULADO",
      "estado": "FECHADA",
      "estado_em": "2026-11-07T10:00:00-03:00",
      "ultimo_comando": {
        "comando": "FECHAR",
        "resultado": "CONFIRMADO",
        "tentativas": 1,
        "concluido_em": "2026-11-07T10:00:00-03:00",
        "pesagem_id": 12
      }
    }
  ],
  "posicao": { "modo": "SIMULADO", "resultado": "AUSENTE", "capturada_em": "...", "analisada_em": "..." },
  "identificacao": { "modo": "SIMULADO", "resultado": "OK", "analisada_em": "..." }
}
```

Os valores acima são só um exemplo.

| Campo | Valores |
|---|---|
| `modo` | `SIMULADO` ou `REAL` (RF-023, spec 004 §5.3). |
| `balanca.comunicacao` | `OK`, `FALHA` ou `DESCONHECIDO` (nunca lida desde a partida). |
| `balanca.motivo_falha` | `SEM_RESPOSTA`, `QUADRO_CORROMPIDO` ou `DESCONECTADA` (spec 004); `null` fora de `FALHA`. |
| `balanca.ultima_leitura` | Última leitura recebida. **É leitura, não peso aceito** (ADR-0005 §4.7). A balança só é lida com uma pesagem em `POSICIONADA_*` (spec 015); fora disso, a leitura é antiga e o `lida_em` mostra isso. |
| `balanca.avaliacao_peso` | Resultado da spec 002 sobre a série atual: `aceito` e `motivo_rejeicao` (`LEITURA_INVALIDA`, `FORA_DE_FAIXA`, `LEITURAS_INSUFICIENTES`, `INSTAVEL`, `FORA_DE_ORDEM`; `null` se aceito). `null` sem série. |
| `cancelas` | Sempre duas, `ENTRADA` e `SAIDA`, nesta ordem. |
| `cancelas[].estado` | `ABERTA`, `FECHADA` ou `DESCONHECIDO`, da **última consulta** ao sensor (spec 004 §5.2), feita ao comandar, ao avaliar a balança livre e na retomada (spec 015). |
| `cancelas[].ultimo_comando` | Último comando concluído: `resultado` `CONFIRMADO`, `FALHA` ou `SEM_CONFIRMACAO`, `tentativas` de 0 a 2. `null` se nenhum. O comando em curso aparece no `comando_pendente` da pesagem. |
| `posicao.resultado` | `CONFIRMADA`, `AUSENTE` ou `INCONCLUSIVA`, já com o limite de idade da imagem (ADR-0005 §4.1); `null` se nunca analisada. |
| `identificacao.resultado` | `OK`, `FALHA_IMAGEM` ou `FALHA_LEITOR`; `null` se nunca analisada. |

### 5.5 Estado atual (`GET /api/operacao/estado`)

```json
{
  "gerado_em": "2026-11-07T10:00:00-03:00",
  "tempo_real": { "intervalo_heartbeat_ms": 5000, "limite_sem_heartbeat_ms": 15000 },
  "pesagens_abertas": [],
  "liberacoes_caminhao": [],
  "ultima_leitura_placa": null,
  "dispositivos": {}
}
```

- `tempo_real`: os tempos configurados (§6.2); os números acima são só um exemplo.
- `pesagens_abertas`: as `Pesagem` não terminais, na ordem `criado_em`, `id`, que é a ordem de chegada da fila da balança (spec 006 §6.3). Não é paginada: há no máximo uma por placa.
- `liberacoes_caminhao`: as `LiberacaoCaminhao` (§5.6) com `aguarda_liberacao_balanca` ainda verdadeiro.
- `ultima_leitura_placa`: a última `LeituraPlaca` registrada, ou `null`.
- `dispositivos`: §5.4.

### 5.6 `LiberacaoCaminhao` (spec 006 §6.4)

| Campo | Conteúdo |
|---|---|
| `pesagem_id` | Pesagem `CANCELADA` que ocupava a balança. |
| `etapa` | `PENDENTE` (ainda não pedida), `ABRINDO_SAIDA`, `AGUARDANDO_BALANCA_VAZIA`, `FECHANDO_SAIDA`, `CONCLUIDA` ou `FALHOU`. |
| `motivo_falha` | `CANCELA_FALHA`, `CANCELA_SEM_CONFIRMACAO` ou `TEMPO_ESGOTADO`; `null` fora de `FALHOU`. |
| `pedido_por`, `pedido_por_nome` | Usuário que pediu; `null` em `PENDENTE`. |
| `motivo` | Texto do pedido; `null` em `PENDENTE`. |
| `pedida_em`, `atualizada_em` | `pedida_em` é `null` em `PENDENTE`. |

## 6. Regras

### 6.1 Canal de eventos (ADR-0005)

- **Só leitura:** o canal não aceita comandos.
- **Abertura:** exige sessão e `CONSULTAR_OPERACAO`. Sem isso, responde `401` ou `403` com o corpo da spec 007 §3.2, antes de abrir o canal. Quando a sessão acaba, o servidor fecha o canal. O canal não renova o prazo da sessão (spec 012 §6.3).
- **Formato:** cada evento tem `event: <tipo>` e `data: <JSON em uma linha>`. Não há `id:` nem reenvio: o servidor ignora `Last-Event-ID`.
- **Tipos:**

| `event` | `data` | Quando |
|---|---|---|
| `pesagem` | `Pesagem` (§5.1) | Cada transição aplicada, inclusive para uma situação terminal. |
| `leitura_placa` | `LeituraPlaca` (§5.2) | Cada leitura registrada. |
| `peso_lido` | `{ "peso_kg", "lida_em" }` | Leitura da balança, no máximo uma a cada `PESAGEM_TEMPO_REAL_INTERVALO_PESO_MS`. **Não é peso aceito.** |
| `balanca` | `dispositivos.balanca` | Mudança de `comunicacao`, `motivo_falha` ou `avaliacao_peso`. |
| `cancela` | Um item de `dispositivos.cancelas` | Mudança de estado ou comando concluído. |
| `posicao` | `dispositivos.posicao` | Mudança de `resultado`. |
| `identificacao` | `dispositivos.identificacao` | Mudança de `resultado`. |
| `liberacao_caminhao` | `LiberacaoCaminhao` (§5.6) | Cada mudança de etapa, e quando uma pesagem passa a aguardar a liberação. |
| `heartbeat` | `{ "enviado_em" }` | A cada `intervalo_heartbeat_ms`, sempre. |

- **Ordem:** o frontend ignora um evento `pesagem` com `versao` menor ou igual à que já tem. Os demais objetos são substituídos se o instante deles (`lida_em`, `comunicacao_em`, `estado_em`, `analisada_em`, `decidida_em`, `atualizada_em`) for mais novo.
- **Pesagem encerrada:** ao receber `pesagem` com situação terminal, o frontend a tira de `pesagens_abertas`.
- **Imagens:** os eventos nunca levam imagem, só `imagem_id` (spec 011).
- Rejeições e eventos "registra" da spec 006 não geram evento no canal; vão só para a auditoria (spec 010).

### 6.2 Tela desatualizada e ressincronização

- Configuração, obrigatória e **sem valor padrão** (o backend não inicia sem ela):
  - `PESAGEM_TEMPO_REAL_HEARTBEAT_MS`: intervalo do `heartbeat`;
  - `PESAGEM_TEMPO_REAL_LIMITE_SEM_HEARTBEAT_MS`: tempo sem nenhuma mensagem para a tela ser considerada desatualizada; precisa ser maior que o intervalo do `heartbeat`, senão o backend não inicia;
  - `PESAGEM_TEMPO_REAL_INTERVALO_PESO_MS`: intervalo mínimo entre eventos `peso_lido`.
- **Desatualizada:** sem nenhuma mensagem dentro de `limite_sem_heartbeat_ms`, ou com o canal caído, a tela mostra um aviso claro e **bloqueia todas as ações** (ADR-0005 P-B).
- **Ressincronização:** ao abrir a tela e a cada reconexão, o frontend abre o canal e depois busca `GET /api/operacao/estado`, aplicando a regra de ordem da §6.1. Só então tira o aviso e libera as ações.
- **Sessão encerrada:** o canal fecha. O `GET` seguinte recebe `401`, e o frontend volta ao login (ADR-0004 §5).

### 6.3 Ações sobre uma pesagem

- **Corpo:** `{ "versao": 7, "motivo": "..." }`. Os dois são obrigatórios. `motivo` não vazio, até 200 caracteres (RN-011). Campo desconhecido dá `422`: não há campo para peso nem para responsável.
- **Responsável:** sempre o usuário da sessão, gravado pelo backend (RN-011).
- **Versão vista:** se `versao` não for a atual, `409` com `VERSAO_DESATUALIZADA`, e nada muda (ADR-0005 §4.5). Essa verificação vem antes da máquina de estados.
- **Máquina de estados:** a ação vai à spec 006. Se ela rejeitar, `409` com `TRANSICAO_REJEITADA`, e nada muda. A rejeição é registrada (RN-010).
- **Sucesso:** `200` com a `Pesagem` nova. Quer dizer que a transição foi aplicada e gravada, **não** que a cancela já se moveu. O resultado do comando chega depois, pelos eventos `cancela` e `pesagem`.
- `TENTAR_NOVAMENTE` com `LIQUIDO_NEGATIVO` faz uma nova pesagem final: o peso final, o líquido e a classificação voltam a `null` (spec 006 §6.1).

### 6.4 Erros das ações

Seguem a spec 007 §3.2. Em `409`, o `erro.codigo` é `CONFLITO` e a causa vai em `campos`:

| Situação | Status | `campos` |
|---|---|---|
| Sem sessão ou sem permissão | 401 / 403 | `[]` |
| `pesagem_id` ou `leitura_placa_id` inexistente | 404 | `[]` |
| `motivo` vazio, longo demais, `versao` ausente ou campo desconhecido | 422 | o campo |
| Versão desatualizada | 409 | `[{ "campo": "versao", "codigo": "VERSAO_DESATUALIZADA" }]` |
| Ação não aceita na situação | 409 | `[{ "campo": "situacao", "codigo": "TRANSICAO_REJEITADA" }]` |
| `liberar-caminhao` sem pendência | 409 | `[{ "campo": "pesagem_id", "codigo": "OPERACAO_NAO_OCUPA_BALANCA" }]` |
| `liberar-caminhao` com liberação em curso | 409 | `[{ "campo": "pesagem_id", "codigo": "LIBERACAO_EM_CURSO" }]` |
| `liberar-entrada` com leitura que não é a mais recente | 409 | `[{ "campo": "leitura_placa_id", "codigo": "LEITURA_DESATUALIZADA" }]` |
| `liberar-entrada` com leitura já liberada ou não `NAO_AUTORIZADA` | 409 | `[{ "campo": "leitura_placa_id", "codigo": "LEITURA_NAO_LIBERAVEL" }]` |
| `liberar-entrada` com motivo da leitura não substituível (§5.3) | 409 | `[{ "campo": "leitura_placa_id", "codigo": "MOTIVO_NAO_SUBSTITUIVEL" }]` |
| `liberar-entrada` com condição do agendamento não atendida | 409 | `[{ "campo": "agendamento_id", "codigo": "<motivo da §5.3>" }]`, com `VEICULO_INATIVO`, `MOTORISTA_INATIVO`, `OPERACAO_JA_ABERTA` ou `SEM_AGENDAMENTO` |
| Banco indisponível | 500 | `[]`. Nada muda e nenhum comando é emitido. |

Os códigos da spec 012 §6.9 (`ORIGEM_NAO_PERMITIDA`, `TIPO_CONTEUDO_INVALIDO`) valem para todas as rotas `POST`.

### 6.5 Liberação manual de entrada (RN-016; spec 006 P-1)

- **Corpo:** `{ "agendamento_id": 31, "motivo": "..." }`, os dois obrigatórios; `motivo` como na §6.3.
- **Só substitui** a identificação da placa e o `ANTES_DA_FAIXA` (§5.3). Continua exigindo, na ordem da §5.3: veículo do agendamento ativo, sem operação aberta, agendamento `AGENDADO` com `data_prevista` de hoje no fuso do pátio, e motorista ativo.
- **Dado velho:** a leitura precisa ser a `LeituraPlaca` mais recente registrada (ADR-0005 §4.5). Uma leitura nova, de outro caminhão, torna a anterior inválida para a liberação.
- **Efeito:** cria a pesagem em `AGUARDANDO_BALANCA_INICIAL`, com `liberacao_manual = true`, grava o responsável e o motivo, liga a leitura à pesagem (`pesagem_id`) e muda o agendamento para `EM_ANDAMENTO` (spec 006 §6.2), tudo na mesma transação. A entrada só abre depois, com a balança livre (RN-019).
- Dois pedidos simultâneos para a mesma leitura ou o mesmo veículo: um recebe `201`, o outro `409`.

### 6.6 Liberação de caminhão cancelado (RN-020; spec 006 §6.4)

- **Corpo:** `{ "motivo": "..." }`. Não leva `versao`, porque a pesagem já é terminal; a proteção contra pedido repetido é o `LIBERACAO_EM_CURSO`.
- Só vale com `aguarda_liberacao_balanca = true`. Sem isso, `409 OPERACAO_NAO_OCUPA_BALANCA`.
- **Sucesso:** `200` com a `Pesagem`. A orquestração comanda `ABRIR` saída e, com a balança vazia pelas câmeras, `FECHAR` saída. As etapas chegam pelo evento `liberacao_caminhao`.
- Em `FALHOU`, a pendência continua e o pedido pode ser repetido. Em `CONCLUIDA`, `aguarda_liberacao_balanca` vira `false` e a balança pode ser liberada para a próxima pesagem (spec 006 §6.3).

### 6.7 Como a tela recebe cada falha

| Situação | O que chega | Saída |
|---|---|---|
| Placa inconclusiva (`FALHA_LEITOR`, `SEM_CANDIDATO`, `PLACA_INVALIDA`, `AMBIGUA`, `CONFIANCA_BAIXA`) | `leitura_placa` `NAO_AUTORIZADA` com o motivo e, se houve candidato, `imagem_id` | Ninguém entra (RN-003). O administrador pode usar a `liberar-entrada`. |
| Sem agendamento, agendamento ambíguo, veículo ou motorista inativo, operação já aberta | `leitura_placa` `NAO_AUTORIZADA` com o motivo | Resolver o cadastro ou o agendamento (specs 007, 008). Não há liberação. |
| Antes da faixa | `leitura_placa` `NAO_AUTORIZADA`, `ANTES_DA_FAIXA` | Esperar a faixa, ou `liberar-entrada` pelo administrador. |
| Placa não reconhecida na volta | `leitura_placa` `NAO_AUTORIZADA`; a pesagem continua `EM_CARGA_DESCARGA` | `liberar-retorno` pelo administrador (spec 006 §6). |
| Câmera de identificação indisponível | `identificacao` `FALHA_IMAGEM` e `leitura_placa` `NAO_AUTORIZADA`, `FALHA_IMAGEM`, sem imagem | Ninguém entra; `liberar-entrada` possível. |
| Câmera de posição indisponível ou incerta | `posicao` `INCONCLUSIVA`; a pesagem não avança | Se continuar, `pesagem` em `AGUARDANDO_INTERVENCAO` com `TEMPO_ESGOTADO`. |
| Balança sem resposta ou com falha | `balanca` `FALHA` com `motivo_falha`; nenhum peso é registrado (RN-005) | Se continuar, `TEMPO_ESGOTADO`; `tentar-novamente`. |
| Leitura de peso rejeitada | `balanca.avaliacao_peso` com `aceito: false` e o motivo | Igual à linha acima. |
| Cancela com `FALHA` ou `SEM_CONFIRMACAO` | `cancela` com o resultado e o estado do sensor (pode ser `DESCONHECIDO`, RN-007); `pesagem` em `AGUARDANDO_INTERVENCAO` com o motivo | `tentar-novamente`, ou as confirmações manuais da spec 006 §6.1. |
| Caminhão sai de posição durante a pesagem | `pesagem` em `AGUARDANDO_INTERVENCAO`, `POSICAO_PERDIDA` | `tentar-novamente` ou `cancelar`. |
| Líquido negativo fora da tolerância | `pesagem` em `AGUARDANDO_INTERVENCAO`, `LIQUIDO_NEGATIVO`, com os pesos | `tentar-novamente` (nova pesagem final) ou `aceitar-peso-final` pelo administrador. |
| Reinício do backend sem estado seguro | Canal cai; depois `pesagem` em `AGUARDANDO_INTERVENCAO`, `REINICIO_INCONCLUSIVO` | Ressincronização da §6.2. |
| Canal ou rede caídos | Sem mensagens | Aviso e bloqueio da §6.2. A operação segue no backend. |

## 7. Dados pessoais

- `Pesagem` e `LeituraPlaca` trazem placa e nome do motorista, nunca o CPF (RNF-013).
- O conteúdo dos eventos e o `motivo` das ações não vão para os logs de acesso. A query string também não (spec 007 §3.4).

## 8. Critérios de aceitação

Verificáveis no backend (testes de API com os simuladores) e no frontend (respostas e eventos simulados com estes tipos, S-6).

| CA | Critério |
|---|---|
| CA-001 | As rotas da §4 existem com as permissões indicadas; sem sessão `401`, sem permissão `403`. |
| CA-002 | `OPERADOR` consegue `tentar-novamente` e `liberar-caminhao` e recebe `403` nas demais ações; `AUDITOR` recebe `403` em todas as ações e consulta o estado e o canal. |
| CA-003 | `GET /api/operacao/estado` traz os seis campos da §5.5; `pesagens_abertas` vem na ordem de chegada e sem terminais; `cancelas` traz `ENTRADA` e `SAIDA`. |
| CA-004 | Toda `Pesagem` traz os campos da §5.1 com os valores das specs 006 e 008; `situacao_anterior` e `motivo_intervencao` só vêm preenchidos em `AGUARDANDO_INTERVENCAO`. |
| CA-005 | `acoes_disponiveis` coincide com as ações aceitas pela spec 006 em cada situação (teste por tabela). |
| CA-006 | O canal recusa sem sessão (`401`) e fecha quando a sessão acaba. |
| CA-007 | Cada transição aplicada gera exatamente um evento `pesagem` com a `versao` nova; rejeições não geram evento. |
| CA-008 | `heartbeat` chega a cada `intervalo_heartbeat_ms`, mesmo sem outros eventos. |
| CA-009 | `peso_lido` não chega com intervalo menor que o configurado e nunca altera `peso_inicial_kg` ou `peso_final_kg`. |
| CA-010 | Frontend: um evento `pesagem` com `versao` menor ou igual à atual é ignorado. |
| CA-011 | Frontend: sem mensagens por `limite_sem_heartbeat_ms`, ou com o canal caído, a tela mostra o aviso e bloqueia as ações; ao reconectar, só libera depois do `GET` do estado. |
| CA-012 | Sem uma das três variáveis da §6.2, ou com o limite menor ou igual ao intervalo do `heartbeat`, o backend não inicia. |
| CA-013 | Ação com `versao` antiga dá `409 VERSAO_DESATUALIZADA`, e a pesagem não muda. |
| CA-014 | Ação sem `motivo`, com `motivo` vazio ou com campo de peso ou de responsável dá `422`. |
| CA-015 | Ação recusada pela spec 006 dá `409 TRANSICAO_REJEITADA`, sem comando e com a rejeição na auditoria. |
| CA-016 | Ação aceita grava o usuário da sessão como responsável e o motivo. |
| CA-017 | `confirmar-posicao` com a entrada aberta responde `200` com `FECHANDO_ENTRADA` e `comando_pendente` de fechar a entrada; a cancela só aparece `FECHADA` depois, pelo evento `cancela`. |
| CA-018 | Placa abaixo do limiar gera `leitura_placa` `NAO_AUTORIZADA`, `CONFIANCA_BAIXA`, com `imagem_id`, e nenhuma pesagem. |
| CA-019 | Placa de veículo sem agendamento de hoje gera `SEM_AGENDAMENTO`; antes da faixa, `ANTES_DA_FAIXA`; com dois candidatos, `AMBIGUA`. |
| CA-020 | `liberar-entrada` sobre `CONFIANCA_BAIXA` ou `ANTES_DA_FAIXA`, com agendamento válido, cria a pesagem em `AGUARDANDO_BALANCA_INICIAL` com `liberacao_manual = true` e põe o agendamento em `EM_ANDAMENTO`. |
| CA-021 | `liberar-entrada` sobre `SEM_AGENDAMENTO` dá `409 MOTIVO_NAO_SUBSTITUIVEL`; com motorista inativo, `409 MOTORISTA_INATIVO`; com uma leitura mais nova registrada, `409 LEITURA_DESATUALIZADA`; repetida, `409 LEITURA_NAO_LIBERAVEL`. |
| CA-022 | `cancelar` uma pesagem que ocupa a balança deixa `aguarda_liberacao_balanca = true` e gera `liberacao_caminhao` em `PENDENTE`. |
| CA-023 | `liberar-caminhao` passa por `ABRINDO_SAIDA`, `AGUARDANDO_BALANCA_VAZIA`, `FECHANDO_SAIDA` e `CONCLUIDA`; sem pendência, `409 OPERACAO_NAO_OCUPA_BALANCA`; durante uma em curso, `409 LIBERACAO_EM_CURSO`; depois de `FALHOU`, aceita de novo. |
| CA-024 | Com a balança em `SEM_RESPOSTA`, chega `balanca` com `FALHA` e `motivo_falha`, e nenhum peso é registrado. |
| CA-025 | Com a cancela em `SENSOR_SEM_RESPOSTA`, chegam `cancela` com `SEM_CONFIRMACAO` e estado `DESCONHECIDO` e `pesagem` em `AGUARDANDO_INTERVENCAO`, `CANCELA_SEM_CONFIRMACAO`. |
| CA-026 | Nenhum evento contém bytes de imagem nem CPF; os logs de acesso não contêm o conteúdo dos eventos nem o `motivo`. |

## 9. Impacto

- **Backend (BE-703):** rotas, canal SSE, conversão de erros; depende da orquestração (BE-602), da persistência (BE-503) e do login (BE-706). A forma de servir SSE no FastAPI ainda não foi verificada (ADR-0005 §5).
- **Frontend (FE-303, FE-306):** tela operacional e intervenções usam só este contrato.
- **Orquestração (spec 015):** calcula `acoes_disponiveis` pela spec 006, emite os eventos da §6.1 e aplica a §6.5 e a §6.6.
- **Esquema (spec 014):** `leitura_placa` com os campos da §5.2 e da spec 015; `pesagem.aguarda_liberacao_balanca`; registro da liberação de caminhão (etapa, motivo da falha, quem pediu, motivo, instantes); responsável e motivo em toda ação; unicidade que impeça duas liberações de entrada para a mesma leitura.
- **Integração (INT-001):** desligar o buffer do proxy em `/api/operacao/eventos`; incluir as três variáveis da §6.2 no `.env.exemplo`.
- **Segurança operacional:** o contrato não cria nenhum caminho novo para acionar cancela; todo comando continua na máquina de estados e na §6.6. A tela bloqueia ações quando está desatualizada, e o backend recusa a versão velha. Nada foi validado com hardware real.
- **Reversibilidade:** alta, sem código ainda.

## 10. Perguntas em aberto

| ID | Pergunta | Até a resposta |
|---|---|---|
| P-1 | A `liberar-entrada` deve ter também um limite de tempo desde a leitura, além de ser a mais recente? | Vale só a regra da leitura mais recente (§6.5). |
| P-2 | Na liberação de caminhão cancelado, se as câmeras não confirmarem a balança vazia, pode haver confirmação manual (como a `CONFIRMAR_BALANCA_VAZIA_MANUAL`)? Pergunta também na spec 015. | Não há: a liberação vai a `FALHOU` com `TEMPO_ESGOTADO` e pode ser repetida. |
