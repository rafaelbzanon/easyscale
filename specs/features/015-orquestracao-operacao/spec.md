# Spec 015 — Orquestração da operação

- **Trilha:** Backend
- **Status:** Implementada (BE-602, 2026-11-07; aprovação e aceite delegados pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** BE-601 (spec); implementação na BE-602 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-006, RF-009, RF-010, RF-014, RF-015, RF-017, RF-019, RF-024, RF-027, RF-034, RN-002, RN-003, RN-005, RN-007, RN-008, RN-011, RN-012, RN-014, RN-016, RN-018, RN-019, RN-020, RN-022, RNF-009, RNF-010, RNF-011, RNF-013
- **Decisões:** ADR-0002 (um processo), ADR-0005 §4.1 e §4.9 (análise contínua, distribuição em memória), spec 006 (máquina de estados), spec 004 (dispositivos), spec 005 (LPR), spec 002 (peso), spec 008 §6.1 (fuso do pátio)
- **Código:** `backend/src/pesagem/orquestracao/`, `backend/src/pesagem/dominio/autorizacao/`, `backend/src/pesagem/lpr/posicao/`, `backend/src/pesagem/lpr/reconhecedor_simulado.py`, `backend/src/pesagem/lpr/codificacao.py`; testes em `backend/tests/unitarios/orquestracao/`, `.../dominio/autorizacao/`, `.../lpr/posicao/`

---

## 1. Contexto e origem

- O artigo descreve o fluxo: identificação, validação pelo agendamento, cancela, pesagem inicial, carga ou descarga, pesagem final, saída e histórico **[ARTIGO §3.5, §4]**. As regras puras já existem (specs 002, 003, 005 §6.3 e 006). Os dispositivos (spec 004) e o LPR (spec 005) têm interfaces e simuladores. Falta quem os coordena: esta spec.
- O que ainda não existe e esta spec define só pela interface e pelo simulador: a **fonte de posição** (RF-027). O critério real de análise da câmera superior não está definido (Q-06, Q-17); a implementação real fica **bloqueada**.
- Segurança operacional (`AGENTS.md` §7) é a prioridade: a orquestração é a única que aciona cancela e aceita peso. Em qualquer dúvida, não autoriza, não aciona e não registra.

## 2. Objetivo

1. Decidir a entrada e a volta do caminhão com uma regra **pura** (`dominio/autorizacao/`): RN-002, RN-003, RN-014, RN-018.
2. Executar o fluxo da spec 006: gerar os eventos automáticos a partir do LPR, da fonte de posição e da balança, executar as ações pedidas e gravar cada passo.
3. Garantir a reserva da balança e a ordem de chegada (spec 006 §6.3), a retomada após reinício (§7.2), a liberação do caminhão cancelado (§6.4) e o efeito no agendamento (§6.2).
4. Rodar sem bloquear a API (D-05) e distribuir os eventos em memória para o SSE (ADR-0005).
5. Em modo `SIMULADO`, permitir o controle dos simuladores que o contrato 011 expõe.

## 3. Fora de escopo

- Rotas, permissões e formato JSON (contratos 009 e 011; BE-703, BE-705). Esta spec entrega métodos e eventos; a API os expõe.
- Leitura das variáveis de ambiente (`config.py`). Aqui ficam os nomes, as regras de validação e o tipo `ConfiguracaoOrquestracao`.
- Esquema e repositórios (spec 014). Aqui ficam os `Protocol` que a orquestração usa; a implementação em memória serve só aos testes.
- Análise real da câmera superior e câmeras reais (Q-06, Q-17).
- Votação entre quadros do LPR (spec 005 §3). Vale uma imagem por decisão.

## 4. Atores

- **Orquestração:** tarefas `asyncio` dentro do processo da API.
- **API (BE-703, BE-705):** chama os métodos de ação manual, liberação e controle de simuladores, já com a permissão verificada (ADR-0004).
- **Administrador e operador:** pelas rotas, conforme spec 006 §9, RN-016 e RN-020.

## 5. Dados e interfaces **[PROPOSTA]**

Nomes conforme `CONVENCOES.md`. Termos novos (\*) entram no glossário com a aprovação.

### 5.1 Decisão de autorização (`dominio/autorizacao/`, pura)

| Nome | Conteúdo |
|---|---|
| `SituacaoVeiculo`\* | Fotografia do cadastro para uma `chave_comparacao`: `veiculo_id`, `ativo`, `operacao_aberta` (`pesagem_id`, `situacao`) ou `None`, e `agendamentos` abertos (`AgendamentoCandidato`\*: `id`, `status`, `data_prevista`, `tipo_operacao`, `faixa_hora_inicio`, `motorista_ativo`). Vem do repositório (§5.4). |
| `decidir_autorizacao(leitura, situacao_veiculo, agora, fuso_patio)` | `leitura`: `PlacaSelecionada \| RejeicaoLeituraPlaca` (spec 005) ou `FalhaIdentificacao`\* (`FALHA_IMAGEM`, `FALHA_LEITOR`). `agora` com fuso; `fuso_patio` de `PESAGEM_PATIO_FUSO`. Devolve um dos três abaixo. |
| `EntradaAutorizada`\* | `agendamento_id`, `veiculo_id`, `tipo_operacao`. |
| `RetornoAceito`\* | `pesagem_id` da operação aberta em `EM_CARGA_DESCARGA` (RN-018). |
| `EntradaNaoAutorizada`\* | `motivo: MotivoNaoAutorizacao`\*. |
| `MotivoNaoAutorizacao` | Nesta ordem de precedência: `FALHA_IMAGEM`, `FALHA_LEITOR`, `SEM_CANDIDATO`, `PLACA_INVALIDA`, `AMBIGUA`, `CONFIANCA_BAIXA`, `VEICULO_NAO_CADASTRADO`, `VEICULO_INATIVO`, `OPERACAO_JA_ABERTA`, `SEM_AGENDAMENTO`, `AGENDAMENTO_AMBIGUO`, `MOTORISTA_INATIVO`, `ANTES_DA_FAIXA`. |
| `MOTIVOS_SUBSTITUIVEIS`\* | Os que a liberação manual de entrada pode substituir (§6.7): os seis de identificação e `ANTES_DA_FAIXA`. |

Regra (§6.1): com placa selecionada e veículo cadastrado e ativo: se há operação aberta em `EM_CARGA_DESCARGA`, `RetornoAceito` (a volta não reaplica a RN-014, spec 006 §14); em outra situação, `OPERACAO_JA_ABERTA` (RN-008). Sem operação aberta: agendamentos com `status = AGENDADO` e `data_prevista` igual ao dia de `agora` no fuso do pátio; nenhum → `SEM_AGENDAMENTO`; mais de um → `AGENDAMENTO_AMBIGUO`; motorista inativo → `MOTORISTA_INATIVO`; hora atual antes de `faixa_hora_inicio` → `ANTES_DA_FAIXA` (RN-014); senão `EntradaAutorizada`.

### 5.2 Fonte de posição (`lpr/posicao/`)

| Nome | Conteúdo |
|---|---|
| `FontePosicao` (interface) | `async def analisar_posicao() -> LeituraPosicao`. |
| `LeituraPosicao`\* | `resultado: ResultadoPosicao`\* (`CONFIRMADA`, `AUSENTE`, `INCONCLUSIVA`), `capturada_em` (com fuso) e `imagem: ImagemCapturada \| None` (spec 005). Câmera indisponível ou análise incerta → `INCONCLUSIVA` com `imagem = None`. |
| `FontePosicaoSimulada` | `CenarioPosicao`\*: `CONFIRMADA`, `AUSENTE`, `INCONCLUSIVA`; `definir_cenario`; relógio injetado; `atraso_captura_ms` para simular imagem antiga. Devolve imagem sintética sem dado pessoal. |
| Implementação real | **Bloqueada** até o critério de análise ser definido (Q-06, Q-17). Fica em `lpr/`, a única camada com OpenCV. |

### 5.3 Identificação

| Nome | Conteúdo |
|---|---|
| `ReconhecedorPlaca`\* | `Callable[[], Awaitable[LeituraPlaca \| FalhaImagem \| FalhaLeitor]]`. No real, `reconhecer_placa` (spec 005) com a fonte e o leitor da entrada. |
| `ReconhecedorPlacaSimulado` (`lpr/reconhecedor_simulado.py`) | `enfileirar(textos: Sequence[TextoOcr])`: a próxima chamada devolve uma `LeituraPlaca` com imagem sintética e uma ROI com esses textos; sem fila, `FalhaImagem(SEM_IMAGEM)`. Serve aos testes e ao controle do contrato 011. |
| `codificar_jpeg(pixels) -> bytes \| None` (`lpr/codificacao.py`) | Codifica a imagem da decisão para a persistência (RN-022). Só o `lpr` importa OpenCV (P-6). |

### 5.4 Persistência (`orquestracao/repositorios.py`, `Protocol`)

Combinado com a spec 014: repositórios **síncronos**, chamados em `asyncio.to_thread`; unidade de trabalho `with banco.transacao() as t`, com commit ao sair e rollback em exceção. Responsável: id do usuário ou `None` no automático.

| Repositório | Métodos usados |
|---|---|
| `t.veiculos` | `buscar_situacao_por_chave(chave_comparacao)` e `buscar_situacao_por_agendamento(agendamento_id)` → `SituacaoVeiculo \| None` (a orquestração converte para o tipo do domínio, P-4). |
| `t.pesagens` | `criar_operacao(agendamento_id, ponto_controle_id, em, leitura_placa_id, liberacao_manual, responsavel_id, motivo)` (agendamento → `EM_ANDAMENTO`; `ErroOperacaoAberta`, `ErroStatusAgendamento`); `gravar_transicao(pesagem_id, versao_lida, operacao_nova, evento, responsavel_id, hoje, em, aguarda_liberacao_balanca, leitura_placa_id, imagem_id)` (`ErroConflitoVersao`, `ErroBalancaOcupada`; auditoria, `situacao_desde`, efeito no agendamento da spec 006 §6.2 e linha `PENDENTE` da liberação, na mesma transação); `registrar_evento(...)` (rejeições e eventos "registra"); `registrar_comando_cancela(...)` (RF-019); `obter_operacao`; `listar_operacoes_abertas()` por `situacao_desde`; `listar_aguardando_liberacao_balanca()`; `buscar_liberacao_caminhao`, `pedir_liberacao_caminhao` (`ErroLiberacaoIndisponivel` se em curso) e `atualizar_liberacao_caminhao` (`CONCLUIDA` zera a pendência). |
| `t.leituras_placa` | `registrar(NovaLeituraPlaca) -> leitura_placa_id`; `buscar(leitura_placa_id)`. Ligar a leitura a uma pesagem só funciona uma vez (`ErroLeituraJaUsada`). |
| `t.imagens` | `salvar(conteudo_jpeg, origem, capturada_em, roi) -> imagem_id`, na mesma transação da decisão. |
| `t.pontos_controle` | `obter_unico() -> ponto_controle_id` (RF-030: uma balança). |

`OperacaoRegistrada` (spec 014): `pesagem_id`, `agendamento_id`, `ponto_controle_id`, `veiculo_id`, `operacao` (spec 006), `situacao_desde`, `aguarda_liberacao_balanca`. Todas as gravações recebem o instante do relógio da orquestração.

### 5.5 Eventos em memória (`orquestracao/eventos.py`)

`DistribuidorEventos`\*: `assinar() -> asyncio.Queue`, `cancelar(fila)`, `publicar(evento)`. Fila limitada por assinante (100 eventos); cheia, o evento é descartado para aquele assinante e o `GET` corrige (ADR-0005 §4.2). Eventos: `EventoOperacao` (`OperacaoRegistrada` completa, com `versao`), `EventoLeituraPlaca`, `EventoPesoLido` (`peso_kg`, `lida_em`; leitura, não peso aceito; no máximo um por `intervalo_minimo_peso_ms`), `EventoBalanca`, `EventoCancela`, `EventoPosicao`, `EventoIdentificacao` (os quatro só quando o resultado muda) e `EventoLiberacaoCaminhao` (cada etapa, inclusive `PENDENTE`). Rejeições e eventos "registra" vão só à auditoria. Nenhum evento leva imagem, só `imagem_id` (ADR-0005 §4.6).

### 5.6 Configuração (`ConfiguracaoOrquestracao`, validada ao criar; valor ausente ou `≤ 0` impede a partida)

| Variável | Uso |
|---|---|
| `PESAGEM_PATIO_FUSO` | Dia e hora da RN-014 (spec 008 §6.1). |
| `PESAGEM_CAMERA_INTERVALO_ANALISE_MS` | Período dos ciclos de identificação e de posição (RF-034). |
| `PESAGEM_CAMERA_IDADE_MAXIMA_IMAGEM_MS` | Imagem mais velha que isso é incerta (ADR-0005 §4.1). |
| `PESAGEM_BALANCA_INTERVALO_LEITURA_MS` | Período do ciclo da balança. |
| `PESAGEM_OPERACAO_TEMPO_LIMITE_POSICIONAMENTO_MS` | `ENTRADA_LIBERADA`, `RETORNO_LIBERADO`. |
| `PESAGEM_OPERACAO_TEMPO_LIMITE_PESAGEM_MS` | `POSICIONADA_INICIAL`, `POSICIONADA_FINAL`. |
| `PESAGEM_OPERACAO_TEMPO_LIMITE_SAIDA_BALANCA_MS` | `SAIDA_INICIAL_LIBERADA`, `SAIDA_LIBERADA` e a espera da §6.8. |
| `PESAGEM_TEMPO_REAL_INTERVALO_PESO_MS` | Intervalo mínimo do `EventoPesoLido` (contrato 009). |

Nenhum tem valor padrão. Situações com comando pendente não têm temporizador: o comando (spec 004) as encerra.

Os demais parâmetros injetados vêm destas variáveis, já nomeadas nas specs de origem e confirmadas aqui (todas obrigatórias e sem valor padrão, exceto a tolerância e os modos):

| Variável | Parâmetro | Origem |
|---|---|---|
| `PESAGEM_BALANCA_MODO`, `PESAGEM_CANCELA_MODO` | Modo da balança e das cancelas; ausente = `SIMULADO`; `REAL` impede a partida (`ErroModoIndisponivel`) enquanto não houver implementação real. | Spec 004 §5.3, §6.4 |
| `PESAGEM_CAMERA_MODO` | Modo das duas fontes de imagem (identificação e posição); ausente = `SIMULADO`; `REAL` impede a partida (não há fonte real, Q-06/Q-17). | Esta spec |
| `PESAGEM_BALANCA_PESO_MINIMO_KG`, `PESAGEM_BALANCA_PESO_MAXIMO_KG`, `PESAGEM_BALANCA_QUANTIDADE_LEITURAS_ESTAVEIS`, `PESAGEM_BALANCA_VARIACAO_MAXIMA_KG`, `PESAGEM_BALANCA_JANELA_ESTABILIDADE_MS` | `ParametrosAceitacaoPeso` | Spec 002 §11 |
| `PESAGEM_PESAGEM_TOLERANCIA_MOVIMENTACAO_KG` | `ParametrosPesoLiquido`; único com padrão: 20 kg (RN-006). | Spec 002 §11 |
| `PESAGEM_LPR_LIMIAR_CONFIANCA` | `ParametrosLeituraPlaca` | Spec 005 §5.4 |
| `PESAGEM_TEMPO_REAL_HEARTBEAT_MS`, `PESAGEM_TEMPO_REAL_LIMITE_SEM_HEARTBEAT_MS` | Só a API (SSE). | Spec 009 §6.2 |

Os modos entram no estado dos dispositivos (RF-023). Valor ausente ou inválido em variável obrigatória impede a partida (`AMBIENTE.md` §8). Os parâmetros das specs 002 e 005 (`ParametrosAceitacaoPeso`, `ParametrosPesoLiquido`, `ParametrosLeituraPlaca`) são injetados.

## 6. Comportamento normal

Tudo roda em **um processo** (ADR-0002), como tarefas `asyncio`: identificação, posição, balança e fila. Eventos que a spec 006 só **registra** (`POSICAO_*` sem transição, `PESO_REJEITADO`, `BALANCA_FALHA`) vão à máquina e à auditoria só quando o resultado muda em relação ao ciclo anterior; `POSICAO_AUSENTE` em `POSICIONADA_*` é sempre enviado, porque para a operação. OCR, análise de imagem e repositórios rodam em `asyncio.to_thread`; os dispositivos já são assíncronos (spec 004). Isso fecha a D-05 (§13). Uma única trava (`asyncio.Lock`) serializa "aplicar evento → gravar → comandar → gravar o resultado": nenhum dispositivo recebe duas chamadas ao mesmo tempo (spec 004 §7), e dois eventos para a mesma operação nunca se misturam. As leituras de câmera, posição e balança ficam fora da trava.

### 6.1 Identificação (RF-006, RF-009, RF-034)

A cada `intervalo_analise_ms`:

1. Chama o `ReconhecedorPlaca`. `SEM_IMAGEM` significa "nada a analisar": fim do ciclo, sem registro.
2. `FalhaImagem` (outros motivos) ou `FalhaLeitor` → `FalhaIdentificacao`. `LeituraPlaca` → cada `TextoLido` vira `CandidatoPlaca` → `selecionar_placa` (spec 005 §6.3).
3. Com placa selecionada, busca a `SituacaoVeiculo` pela `chave_comparacao`. Aplica `decidir_autorizacao`.
4. **Repetição:** uma `NAO_AUTORIZADA` igual à última registrada (chave da placa e `motivo`) não é registrada nem publicada. Autorizar e aceitar a volta sempre registram: criam ou movem a operação, e o ciclo seguinte já decide diferente (`OPERACAO_JA_ABERTA`); assim o mesmo caminhão entra de novo depois de um cancelamento (RN-009). A última decisão e a sua leitura ficam em memória; depois de um reinício, o primeiro ciclo registra de novo. Assim um caminhão parado na entrada gera um registro, e a mudança de situação (ex.: agendamento criado) é percebida no ciclo seguinte.
5. Com ao menos um candidato, a imagem é codificada (`codificar_jpeg`). Se não codificar, a decisão vira `FALHA_IMAGEM`.
6. Numa única transação: salva a imagem (se houver), registra a `leitura_placa` e:
   - `EntradaAutorizada` → `criar_operacao` em `AGUARDANDO_BALANCA_INICIAL` (spec 006 P-1), ligada à leitura;
   - `RetornoAceito` → `gravar_transicao` com `PLACA_RETORNO_ACEITA` (`EM_CARGA_DESCARGA` → `AGUARDANDO_BALANCA_FINAL`);
   - `EntradaNaoAutorizada` → só a leitura, com o motivo (RN-003).
7. Publica `EventoLeituraPlaca` e, se houver, `EventoOperacao`.

### 6.2 Fila e balança disponível (spec 006 §6.3; RN-019)

Enquanto houver operação em `AGUARDANDO_BALANCA_INICIAL` ou `AGUARDANDO_BALANCA_FINAL`, a cada `intervalo_analise_ms` a orquestração escolhe a mais antiga por `situacao_desde` e envia `BALANCA_DISPONIVEL` **só se**, ao mesmo tempo: nenhuma operação aberta ocupa a balança (§6.3 da spec 006); nenhuma pesagem está com `aguarda_liberacao_balanca` (§6.8); a última posição conhecida é `AUSENTE` e não é antiga (§6.3); e as duas cancelas respondem `FECHADA` ao sensor, consultado na hora. Qualquer outra leitura (`ABERTA`, `DESCONHECIDO`) mantém a fila parada. A gravação de `AUTORIZADA`/`RETORNO_AUTORIZADO` é a reserva: `ErroBalancaOcupada` da spec 014 é a segunda barreira, e a operação fica na fila.

### 6.3 Posição (RF-027)

A cada `intervalo_analise_ms`, se alguma operação espera a câmera (`ENTRADA_LIBERADA`, `RETORNO_LIBERADO`, `POSICIONADA_*`, `SAIDA_*_LIBERADA`) ou a fila precisa saber se a balança está vazia: chama `analisar_posicao`. Se `agora − capturada_em > idade_maxima_imagem_ms`, o resultado conta como `INCONCLUSIVA` (ADR-0005 §4.1). Converte para `POSICAO_CONFIRMADA`, `POSICAO_AUSENTE` ou `POSICAO_INCONCLUSIVA` e aplica à operação que ocupa a balança. Guarda o último resultado para a §6.2 e para a tela, e a imagem mais recente de cada fonte em JPEG (contrato 011, `imagem_atual`). Uma `POSICAO_CONFIRMADA` que faz a operação avançar salva a imagem (RN-022) na mesma transação da transição; sem imagem codificável, o evento vira `POSICAO_INCONCLUSIVA`. O ciclo também aplica os tempos-limite (§6.5) e conduz a espera da §6.8.

### 6.4 Balança (RF-013, RF-014)

Lida só enquanto uma operação está em `POSICIONADA_INICIAL` ou `POSICIONADA_FINAL`, a cada `intervalo_leitura_balanca_ms`:

- `FalhaBalanca` → `BALANCA_FALHA` (registra; RN-005). A série em memória é descartada.
- `LeituraBalanca` → vira `LeituraPeso`, entra na série (só as últimas `quantidade_leituras_estaveis`) e publica `EventoPesoLido` respeitando o intervalo mínimo. `validar_leituras_peso` (spec 002): `PesoAceito` → evento `PesoAceito` da spec 006, que grava o peso e pede `ABRIR` saída (RN-012); rejeição → `PESO_REJEITADO` só quando o motivo muda em relação ao ciclo anterior, e nunca para `LEITURAS_INSUFICIENTES`, que é o estado normal enquanto a série enche.
- Ao entrar em `POSICIONADA_*` (inclusive na retomada), a série recomeça vazia.

### 6.5 Comandos e tempos-limite

- Toda `TransicaoAplicada` é gravada **antes** do comando. Com `AcaoPedida`, a orquestração chama `abrir()`/`fechar()` da cancela indicada, registra o `evento_cancela` e aplica `CANCELA_CONFIRMADA`, `CANCELA_FALHA` ou `CANCELA_SEM_CONFIRMACAO` (RN-007). Nunca há reenvio além da política da spec 004.
- A cada ciclo de posição, para cada operação numa situação com tempo-limite (§5.6): se `agora − situacao_desde ≥ limite`, aplica `TEMPO_ESGOTADO`.
- Ao sair de `FECHANDO_SAIDA_INICIAL` ou `FECHANDO_SAIDA` com `CANCELA_CONFIRMADA`, a balança fica livre (a situação deixa de ocupá-la).

### 6.6 Ações manuais (spec 006 §5.3, §9; RN-011)

`aplicar_acao_manual(pesagem_id, versao_vista, acao: AcaoManual, responsavel_id)`: relê a operação; se `versao_vista` difere da atual, levanta `ErroConflitoVersao` sem efeito (ADR-0005 §4.5; `409 VERSAO_DESATUALIZADA` na spec 009). Aplica pela máquina; rejeição é registrada e devolvida (`409 TRANSICAO_REJEITADA`). A resposta volta com a transição **gravada**; a ação pedida é executada em seguida, numa tarefa sob a mesma trava, e o resultado chega pelos eventos (spec 009 §6.3). Antes de comandar, a tarefa relê a operação e só envia se ela ainda for exatamente a gravada: um `CANCELAR` que passe antes impede o comando (`AGENTS.md` §7.1.3). `CONFIRMAR_POSICAO_MANUAL` e `CONFIRMAR_BALANCA_VAZIA_MANUAL` salvam a última imagem de posição disponível (RN-022). `CANCELAR` numa operação que ocupa a balança grava `aguarda_liberacao_balanca = true`. Quem pode pedir cada ação é verificado pela API (ADR-0004).

### 6.7 Liberação manual de entrada (RN-016, spec 006 P-1)

`liberar_entrada_manual(leitura_placa_id, agendamento_id, responsavel_id, motivo)`, só `ADMINISTRADOR` (pela API). Recusas levantam `ErroLiberacaoEntrada` com o código da spec 009 §6.4, sem efeito: a leitura precisa ser a última registrada (`LEITURA_DESATUALIZADA`), `NAO_AUTORIZADA` e ainda sem pesagem (`LEITURA_NAO_LIBERAVEL`), com motivo em `MOTIVOS_SUBSTITUIVEIS` (`MOTIVO_NAO_SUBSTITUIVEL`). A regra da §5.1 é reaplicada com o veículo do agendamento, ignorando a identificação e a `ANTES_DA_FAIXA`: agendamento `AGENDADO` de hoje, veículo e motorista ativos e sem operação aberta continuam obrigatórios (código = `MotivoNaoAutorizacao`). O administrador responde pela correspondência entre a placa vista e o agendamento. Cria a operação com `liberacao_manual = true`, ligada à leitura, com responsável e motivo.

### 6.8 Caminhão de operação cancelada (spec 006 §6.4; RN-020)

`liberar_caminhao_cancelado(pesagem_id, responsavel_id, motivo)`: só vale para pesagem com `aguarda_liberacao_balanca`; senão levanta `ErroOperacaoNaoOcupaBalanca` (`409 OPERACAO_NAO_OCUPA_BALANCA`); pedido com liberação em curso levanta `ErroLiberacaoIndisponivel` da spec 014 (`409 LIBERACAO_EM_CURSO`). A liberação é persistida (spec 014) e publicada em `EventoLiberacaoCaminhao` a cada etapa: `PENDENTE` (ao cancelar) → `ABRINDO_SAIDA` (gravada antes do comando `ABRIR` saída, registrado com responsável e motivo) → `AGUARDANDO_BALANCA_VAZIA` (o ciclo de posição espera `AUSENTE`, até `tempo_limite_saida_balanca_ms`) → `FECHANDO_SAIDA` (gravada antes de `FECHAR` saída) → `CONCLUIDA`. Comando não confirmado ou tempo esgotado → `FALHOU` com o motivo (`CANCELA_FALHA`, `CANCELA_SEM_CONFIRMACAO`, `TEMPO_ESGOTADO`); a pendência fica, e o pedido pode ser repetido (abrir com a saída já aberta não envia comando, spec 004 CA-012). Enquanto houver pendência, a fila não anda (§6.2).

### 6.9 Controle dos simuladores (contrato 011; só em `SIMULADO`)

Estado inicial dos simuladores, **fixo no código** e sem variável (só a rota do contrato 011 o muda): balança `SEM_RESPOSTA` com `peso_kg = 0` e `amplitude_kg = 0` (nenhum peso é inventado até o administrador definir um), posição `AUSENTE` (no pátio simulado não há caminhão até uma chegada ser simulada), cancelas `CONFIRMADO` com posição inicial `FECHADA` (condição da spec 006 §6.3). Nada disso aciona hardware.

`Simuladores`\*, criado por `criar_simuladores` só quando todos os dispositivos estão em `SIMULADO`: `estado()` (cenários atuais e `chegadas_na_fila`), `definir_balanca(cenario, peso_kg, amplitude_kg)` (troca a instância de `BalancaSimulada`), `definir_cancela(ENTRADA|SAIDA, cenario)`, `definir_posicao(cenario)` e `simular_chegada(textos)` (enfileira no `ReconhecedorPlacaSimulado`). Com algum dispositivo em `REAL` o objeto não existe, e a API responde conforme o contrato (404).

### 6.10 Estado dos dispositivos (RF-023)

`EstadoDispositivos`\*, derivado do último resultado: balança (`OK`, `FALHA` com motivo, `DESCONHECIDO` se nunca lida, instante); cada cancela (último estado do sensor e último comando: comando, resultado, tentativas, instante); posição (último resultado e `capturada_em`); identificação (último resultado); modo de cada dispositivo.

## 7. Comportamento em falha

| Situação (`AGENTS.md` §7.2) | Comportamento |
|---|---|
| Balança sem resposta, corrompida, desconectada | `BALANCA_FALHA` registrado; nenhum peso; a etapa continua até `TEMPO_ESGOTADO` (RN-005). |
| Leitura instável, fora de faixa, malformada | Rejeição da spec 002; `PESO_REJEITADO` registrado; nunca ajustada. |
| Cancela `FALHA` ou `SEM_CONFIRMACAO` | Evento de mesmo nome → `AGUARDANDO_INTERVENCAO`; estado tratado como desconhecido; sem reenvio. |
| Placa inconclusiva, baixa confiança, inválida, ambígua | `NAO_AUTORIZADA` com o motivo e a imagem; nenhuma operação nasce (RN-003). |
| Sem agendamento, outro dia, antes da faixa | `SEM_AGENDAMENTO` / `ANTES_DA_FAIXA`; registrado. |
| Mais de um agendamento ou candidato | `AGENDAMENTO_AMBIGUO` / `AMBIGUA`; nunca escolhe. |
| Câmera indisponível, frame inválido, imagem antiga | Identificação: `FALHA_IMAGEM`. Posição: `POSICAO_INCONCLUSIVA`; não avança; a fila não anda. |
| Transição inválida | `TransicaoRejeitada` registrada (RN-010); sem comando. |
| Falha na gravação (qualquer `ErroPersistencia`) | A transação desfaz tudo: operação não avança, nenhum comando é emitido, nada é autorizado (inclusive a etapa da liberação gravada antes do comando, §6.8). O ciclo registra o tipo do erro e tenta de novo no período seguinte; os ciclos nunca param por falha do banco. Se a falha vier **depois** de um comando já enviado (resultado da cancela, etapa da liberação), só a **gravação** é repetida no ciclo seguinte; o comando nunca. |
| `ErroConflitoVersao` | Relê a operação e reavalia o evento no próximo ciclo; ação manual devolve conflito. |
| Reinício | §7.1. |
| Dois eventos para a mesma operação | Trava única + `versao` na gravação (spec 006 §7.3). Os tempos-limite usam a operação relida sob a trava, nunca uma fotografia anterior do ciclo. |
| Modo `REAL` | Indisponível (spec 004 §6.4): a partida falha, nunca cai para o simulado. |

### 7.1 Retomada (spec 006 §7.2)

Na partida, antes de iniciar os ciclos, para cada operação de `listar_operacoes_abertas()`:

| Situação gravada | Ação |
|---|---|
| Com comando pendente | Consulta o sensor da cancela. Já na posição pedida → `CANCELA_CONFIRMADA`. Posição contrária → repete o comando pela spec 004 e aplica o resultado. `DESCONHECIDO` → `REINICIO_INCONCLUSIVO`, sem comando. |
| `POSICIONADA_*` | Série da balança vazia; continua. |
| `AGUARDANDO_INTERVENCAO`, terminais e demais | Nada muda; os tempos-limite contam de `situacao_desde`. |

Liberação da §6.8 interrompida em `ABRINDO_SAIDA` ou `FECHANDO_SAIDA`: segue a mesma tabela para a saída (sensor na posição pedida → próxima etapa; contrária → repete pela spec 004; `DESCONHECIDO` → `FALHOU` com `CANCELA_SEM_CONFIRMACAO`). Em `AGUARDANDO_BALANCA_VAZIA` o ciclo de posição continua a espera.

## 8. Regras de negócio

RN-002 e RN-014 em `decidir_autorizacao`; RN-003 pela leitura registrada com motivo e imagem; RN-007 e RN-012 pela spec 006, com a gravação antes do comando; RN-008 e RN-019 pela §6.2 e pela spec 014; RN-016 pela §6.7; RN-018 pela §5.1; RN-020 pela §6.8; RN-022 pelas imagens das §6.1, §6.3 e §6.6; RNF-011 pela §6; RNF-013: nenhum log leva placa ou imagem.

## 9. Estados afetados

Os da spec 006, sem mudança. Novo registro `leitura_placa` com `decisao` e `motivo`; nova pendência `aguarda_liberacao_balanca`; etapas da §6.8 só em memória.

## 10. Dados envolvidos

Ver §5.1, §5.4 e §5.5. A `leitura_placa` guarda `placa_lida`, `placa_normalizada`, `formato`, `correcoes`, `confianca`, todas as ROIs com textos, `decisao`, `motivo`, `imagem_id`, `agendamento_id`, `pesagem_id`, `origem`, `capturada_em`, `decidida_em`. Auditoria conforme spec 006 §10.

## 11. Critérios de aceitação

Verificados com os simuladores e a persistência em memória; os de persistência real ficam para a integração com a spec 014.

| CA | Critério |
|---|---|
| CA-001 | **Autorização:** placa válida, veículo ativo, um agendamento `AGENDADO` de hoje, hora dentro ou depois da faixa → `EntradaAutorizada`. |
| CA-002 | Cada motivo de `MotivoNaoAutorizacao` tem um caso que o produz, e com dois motivos vale o primeiro na ordem da §5.1. |
| CA-003 | Agendamento de outro dia dá `SEM_AGENDAMENTO`; hora antes da faixa, `ANTES_DA_FAIXA`; perto da meia-noite, o dia vem do fuso do pátio, não do do servidor (RN-014). |
| CA-004 | Operação aberta em `EM_CARGA_DESCARGA` → `RetornoAceito`, mesmo depois da faixa e em outro dia; em outra situação → `OPERACAO_JA_ABERTA`. |
| CA-005 | **Fluxo completo** de CARGA com simuladores: da chegada da placa a `FINALIZADA`, com 8 comandos na ordem da spec 006, pesos gravados, líquido calculado e agendamento `CONCLUIDO`. |
| CA-006 | Placa não autorizada: leitura registrada com motivo e `imagem_id`, nenhuma operação criada, nenhum comando. |
| CA-007 | Mesma decisão repetida em ciclos seguidos gera um só registro; mudança da situação gera novo registro. |
| CA-008 | `SEM_IMAGEM` não registra nada; `IMAGEM_INVALIDA`, `FONTE_INDISPONIVEL` e `FalhaLeitor` registram `FALHA_IMAGEM`/`FALHA_LEITOR` sem imagem. |
| CA-009 | **Reserva:** dois caminhões autorizados; só o primeiro recebe `BALANCA_DISPONIVEL`; o segundo só depois de o primeiro sair de `FECHANDO_SAIDA_INICIAL`. |
| CA-010 | `BALANCA_DISPONIVEL` não é enviado com posição `AUSENTE` antiga, `INCONCLUSIVA`/`CONFIRMADA`, ou com alguma cancela `ABERTA`/`DESCONHECIDO`. |
| CA-011 | **Retomada:** cada uma das 8 situações com comando pendente, com o sensor na posição pedida → `CANCELA_CONFIRMADA` sem comando; na contrária → um comando; `DESCONHECIDO` → `REINICIO_INCONCLUSIVO` sem comando. |
| CA-012 | Retomada em `POSICIONADA_*` descarta a série; em `AGUARDANDO_INTERVENCAO` e terminais nada muda. |
| CA-013 | **Transação:** gravação que falha ao aplicar `BALANCA_DISPONIVEL` e `PesoAceito` deixa a operação inalterada e não envia comando. |
| CA-014 | **Agendamento:** criação → `EM_ANDAMENTO`; `FINALIZADA` → `CONCLUIDO`; `CANCELADA` → `AGENDADO`. |
| CA-015 | **Liberação do cancelado:** `CANCELAR` em situação que ocupa a balança marca a pendência e para a fila; a liberação envia `ABRIR` saída, espera `AUSENTE`, `FECHAR` saída e conclui; a fila volta a andar. Em pesagem sem pendência → `OPERACAO_NAO_OCUPA_BALANCA`. Com `NAO_MOVE` → `FALHOU`, pendência mantida, repetível. |
| CA-016 | `BALANCA_FALHA` e rejeições não gravam peso; `PESO_REJEITADO` só quando o motivo muda e nunca para `LEITURAS_INSUFICIENTES`; `TEMPO_ESGOTADO` em `POSICIONADA_*` após o limite. |
| CA-017 | Cancela `FALHA`, `NAO_MOVE` e `SENSOR_SEM_RESPOSTA` levam a `AGUARDANDO_INTERVENCAO` com o motivo certo e um só comando enviado; `TENTAR_NOVAMENTE` repete uma vez. |
| CA-018 | Imagem de posição mais velha que o limite vira `POSICAO_INCONCLUSIVA` e não faz a operação avançar. |
| CA-019 | Ação manual com `versao_vista` desatualizada não tem efeito; `CONFIRMAR_POSICAO_MANUAL` salva a imagem e marca `liberacao_manual`. |
| CA-020 | **Liberação manual de entrada:** substitui `CONFIANCA_BAIXA` e `ANTES_DA_FAIXA` e cria a operação com `liberacao_manual`; não substitui `SEM_AGENDAMENTO`, `VEICULO_INATIVO`, `OPERACAO_JA_ABERTA`, nem leitura `AUTORIZADA`. |
| CA-021 | Falha ao codificar a imagem de uma placa válida → `FALHA_IMAGEM`, sem operação. |
| CA-022 | `EventoPesoLido` respeita o intervalo mínimo; assinante com fila cheia perde eventos sem travar a orquestração; nenhum evento contém pixels. |
| CA-023 | `ConfiguracaoOrquestracao` recusa valores ausentes ou `≤ 0`. |
| CA-024 | `Simuladores` troca cenário da balança, das cancelas e da posição e enfileira uma chegada; não existe quando algum dispositivo é `REAL`. |
| CA-025 | Arquitetura (spec 001): `orquestracao` não importa `cv2`, `easyocr`, `serial` nem `fastapi`; `dominio/autorizacao` não importa I/O. |

## 12. Impacto

- **Código novo:** `dominio/autorizacao/decisao.py`; `orquestracao/` (`erros.py`, `configuracao.py`, `repositorios.py`, `eventos.py`, `operacao.py`, `simuladores.py`); `lpr/posicao/` (`interface.py`, `simulada.py`), `lpr/reconhecedor_simulado.py`, `lpr/codificacao.py`. Os três últimos ficam no `lpr` porque usam OpenCV ou criam seus tipos (P-6); pedido ao Maestro para a árvore do `CONVENCOES.md` §2. Em `dominio/operacao/maquina_estados.py` só o alias público `COMANDO_PENDENTE`, para a retomada.
- **Composição (BE-703/BE-705):** a API cria `Orquestracao(...)`, chama `retomar()` e depois `executar()` como tarefa; as ações manuais, as liberações, `estado_dispositivos()`, `imagem_atual()` e `Simuladores` são métodos; o SSE assina o `DistribuidorEventos`.
- **Spec 014:** `situacao_desde`, `aguarda_liberacao_balanca`, `leitura_placa` com os campos da §10, imagens na transação, `obter_unico` do ponto de controle.
- **Contratos 009 e 011:** vocabulário da §5 (decisões, motivos, etapas da §6.8, `EstadoDispositivos`, eventos).
- **`AMBIENTE.md`:** D-05 fechada (§13); Q-17 continua aberta para o critério de análise.
- **Segurança operacional:** nenhuma ação física sem estado gravado; retomada sem reenvio cego; fail-safe em toda dúvida. Nada validado com hardware real.
- **Reversibilidade:** alta; só simuladores.

## 13. Decisões delegadas (2026-11-07)

| ID | Decisão |
|---|---|
| D-05 | Fechada: tarefas `asyncio` em um processo; OCR, análise de imagem e repositórios em `asyncio.to_thread`; dispositivos assíncronos. Reabrir se a latência medida do OCR bloquear a API (R-04). |
| P-1 | A balança só é lida em `POSICIONADA_*`. Menos tráfego serial; o estado da balança fora disso é o último conhecido. |
| P-2 | Leitura registrada só quando a decisão muda (§6.1). |
| P-3 | Eventos que só registram (`PESO_REJEITADO`, `BALANCA_FALHA`, `POSICAO_*` sem transição) só na mudança de resultado; `LEITURAS_INSUFICIENTES` nunca (§6). |
| P-4 | Liberação manual de entrada substitui só identificação e `ANTES_DA_FAIXA` (§6.7). |
| P-5 | Imagem não codificável = `FALHA_IMAGEM`; imagem e decisão na mesma transação (RN-022). |
| P-6 | Caminhão cancelado: pendência e etapas persistidas (spec 014), fila parada até a liberação concluir (§6.8). |
| P-8 | Gravação que falha depois de um comando físico: repete-se só a gravação, nunca o comando (§7). |
| P-9 | A liberação manual de entrada não confere a placa lida com o veículo do agendamento: o administrador responde por isso (§6.7). |
| P-7 | Sem temporizador em situações com comando pendente (§5.6). |

## 14. Perguntas em aberto

| ID | Pergunta | Enquanto não há resposta |
|---|---|---|
| Q-A | Na liberação da §6.8, se as câmeras não confirmarem a balança vazia, o administrador pode confirmar manualmente? | Não: `FALHOU`, repetível. |
| Q-B | `POSICAO_CONFIRMADA` significa "o caminhão desta operação" (spec 006 §5.2). Como a câmera superior distingue o caminhão (Q-17)? | Só um caminhão pode estar na balança (RN-019): o resultado é atribuído à operação que a ocupa. |
| Q-C | Qual câmera identifica a placa e como as câmeras são nomeadas (Q-06)? | Uma fonte de identificação e uma de posição; `origem` é texto. |
| Q-D | `CANCELAR` em `AUTORIZADA`, `ENTRADA_LIBERADA`, `FECHANDO_ENTRADA` (ou as equivalentes do retorno) deixa a entrada aberta ou desconhecida; a liberação da §6.8 só comanda a saída. A liberação deve fechar também a entrada? | Não: a fila fica parada até a entrada responder `FECHADA` ao sensor (§6.2), o que exige ação fora do sistema. Seguro, mas trava a fila. |
