# Glossário do domínio

- **Trilha:** Comum
- **Status:** Em revisão
- **Tarefa:** C-101 (`specs/tarefas-iniciais.md`)

Fonte única dos termos usados em identificadores: `CONVENCOES.md` §10. Este arquivo explica o **significado** de cada termo; o **identificador** deve ser usado exatamente como está na coluna "Identificador". Termo novo entra aqui **e** no `CONVENCOES.md` §10 na mesma mudança, com aprovação do autor.

Origem: **[ARTIGO]** = descrito no artigo do TCC (`docs/artigo/artigo-tcc.pdf`); **[DEFINIDO]** = decisão do autor; **[PROPOSTA]** = sugestão não aprovada; **[PENDENTE]** = depende de resposta (Q-xx).

---

## 1. Operação e agendamento

| Termo | Identificador | Significado | Origem | Não usar |
|---|---|---|---|---|
| Agendamento | `agendamento` | Registro, criado **manualmente** por usuário com permissão ou pelo motorista no autoatendimento, que prevê a vinda de um veículo para uma operação (veículo, motorista, transportadora quando houver, tipo de operação, produto, data prevista, faixa de horário). O sistema nunca cria agendamento sozinho. | [ARTIGO] + [DEFINIDO] (manual) | `schedule`, `reserva` |
| Status do agendamento | `status` | Situação do agendamento em si: `AGENDADO`, `EM_ANDAMENTO`, `CONCLUIDO`, `CANCELADO`, `EXPIRADO` (spec 008 §6.6). Não confundir com `situacao` da pesagem. Regras de validade: RN-014. | [AUTOR] (specs 006 e 008) | — |
| Operação logística | `operacao` | O fluxo percorrido pelo veículo desde a identificação até a saída, conduzido por uma máquina de estados explícita. Estados e transições: spec 006. | [ARTIGO] (fluxo) + [AUTOR] (máquina de estados, spec 006) | `processo`, `fluxo` |
| Faixa de horário | `faixa_horario` | Intervalo fixo do dia (início e fim), com capacidade máxima de caminhões, configurado pelo administrador. Todo agendamento ocupa uma vaga numa faixa; o cancelamento libera a vaga. Chegada antes da faixa não é liberada; depois da faixa, no mesmo dia, é (RN-014, RN-015). | [AUTOR] (Q-13, 2026-10-29) | `slot`, `janela`, `turno` |
| Agendamento aberto | `AGENDADO` ou `EM_ANDAMENTO` | Agendamento ainda não encerrado. Uma placa só pode ter um (RN-023). | [AUTOR] (spec 008) | `ativo` |
| Origem do agendamento | `origem` | Quem o criou: `USUARIO` ou `AUTOATENDIMENTO`. | [AUTOR] (spec 008) | `canal`, `fonte` |
| Fuso do pátio | `PESAGEM_PATIO_FUSO` | Fuso configurado que define o "hoje" e os horários das faixas. Sem valor padrão. | [AUTOR] (spec 008) | — |
| Produto | `produto` | Item movimentado na operação, informado no agendamento. Tem cadastro próprio. | [ARTIGO §4] (no agendamento) + [AUTOR] (cadastro, Q-14) | `mercadoria`, `item` |
| Tipo de operação | `tipo_operacao` | Natureza da operação: `CARGA` ou `DESCARGA`. | [ARTIGO] | `tipo` |
| Situação | `situacao` | Estado persistido de uma pesagem/operação. Valores em `UPPER_SNAKE_CASE`, idênticos entre spec, código e banco (`CONVENCOES.md` §4.6). Lista final: spec 006 §5.1. | [AUTOR] (spec 006) | `state`, `estado_atual` |
| Situação anterior | `situacao_anterior` | Situação de onde a operação parou para intervenção; é para ela que a operação volta em `TENTAR_NOVAMENTE`. | [AUTOR] (spec 006) | `estado_previo` |
| Motivo de intervenção | `motivo_intervencao` | Por que a operação parou em `AGUARDANDO_INTERVENCAO` (spec 006 §5.4). | [AUTOR] (spec 006) | `erro`, `causa` |
| Versão da operação | `versao` | Número que sobe a cada transição; impede que dois eventos simultâneos avancem a mesma operação. | [AUTOR] (spec 006) | `revision` |
| Ação pedida | `acao_pedida` | Comando de cancela que a máquina de estados pede à orquestração em uma transição. | [AUTOR] (spec 006) | `side_effect` |
| Usuário do sistema | `usuario` | Pessoa com login no sistema, com um perfil (RF-031, RF-032). | [AUTOR] (ADR-0004) | `user` |
| Perfil de acesso | `perfil` | Conjunto de permissões atribuído ao usuário; perfis iniciais `ADMINISTRADOR`, `OPERADOR`, `AUDITOR` (RF-031). | [AUTOR] (ADR-0004) | `role` |
| Decisão de entrada | `decisao` | Resultado da regra pura de autorização (spec 015): `AUTORIZADA`, `RETORNO_ACEITO` (volta, RN-018) ou `NAO_AUTORIZADA`, com `motivo` (`MotivoNaoAutorizacao`). | [AUTOR] (spec 015, delegada) | `resultado_autorizacao` |
| Posição na balança | `FontePosicao`, `LeituraPosicao` | Fonte e resultado da análise da câmera superior (`CONFIRMADA`, `AUSENTE`, `INCONCLUSIVA`); `CenarioPosicao` no simulador (RF-027). | [AUTOR] (spec 015, delegada) | `sensor_posicao` |
| Aguarda liberação da balança | `aguarda_liberacao_balanca` | Pesagem cancelada cujo caminhão ainda ocupa a balança (RN-020, spec 006 §6.4). | [AUTOR] (spec 015, delegada) | `pendente_saida` |
| Situação desde | `situacao_desde` | Instante em que a operação entrou na situação atual; ordena a fila da balança. | [AUTOR] (spec 015, delegada) | `entrou_em` |
| Ações disponíveis | `acoes_disponiveis` | Lista, calculada pelo backend, das ações manuais que a situação atual da pesagem permite; a tela não repete a tabela da spec 006 (spec 009). | [AUTOR] (spec 009, delegada) | `allowed_actions` |
| Estado dos dispositivos | `EstadoDispositivos` | Último resultado conhecido da balança, de cada cancela, da posição e da identificação, com o modo de cada um (RF-023, spec 015). | [AUTOR] (spec 015, delegada) | `status_hardware` |
| Imagem atual | `imagem_atual` | Imagem mais recente de uma câmera, mostrada no diagnóstico e não gravada (ADR-0005, RN-022). | [AUTOR] (spec 011, delegada) | `frame_ao_vivo` |
| Liberação de caminhão | `liberacao_caminhao` | Saída, pedida por operador ou administrador, do caminhão de uma operação cancelada que ainda está na balança (RN-020). | [AUTOR] (spec 014, delegada) | `saida_forcada` |
| Evento da operação | `evento_operacao` | Registro de histórico de uma pesagem: transição, rejeição, comando de cancela, intervenção, com responsável e motivo (RNF-010). | [AUTOR] (spec 014, delegada) | `log_operacao` |
| Tentativa de acesso | `tentativa_acesso` | Contagem de falhas de login ou de autoatendimento por chave, guardada só como hash, para o limite de tentativas. | [AUTOR] (spec 014, delegada) | `rate_limit` |
| Imagem da decisão | `imagem_decisao` | Imagem salva porque fundamentou uma decisão (RN-022); exclusão só apaga os bytes e registra quem e por quê. | [AUTOR] (spec 014, delegada) | `foto`, `snapshot` |
| Autoatendimento | `autoatendimento` | Tela do motorista, sem login, para criar agendamento pela rede do pátio (RF-033). | [AUTOR] (ADR-0004) | `self_service`, `kiosk` |
| Código da nota | `codigo_nota` | Código informado pelo motorista na descarga; é guardado sem verificar a autenticidade (RN-021). | [AUTOR] (ADR-0004) | `chave`, `nf` |
| CPF mascarado | `cpf_mascarado` | CPF com os 3 primeiros dígitos e o verificador ocultos, para quem não pode ver o completo (spec 007). | [AUTOR] (spec 007) | `cpf_parcial` |
| Ponto de controle | `ponto_controle` | Conjunto físico que atende o veículo: balança, câmera e cancela(s) de entrada/saída. Por enquanto, uma balança (RF-030); volume em aberto (Q-12). | [PROPOSTA] (schema de referência) | `estacao` |
| Liberação manual | `liberacao_manual` | Decisão de um usuário autorizado que substitui a decisão automática em caso de exceção; exige responsável e motivo registrados. Só o administrador (Q-04, RN-016); quando: spec 006 §9. | [ARTIGO] (intervenção) + [AUTOR] (regras) | `override` |

## 2. Pesagem

| Termo | Identificador | Significado | Origem | Não usar |
|---|---|---|---|---|
| Pesagem | `pesagem` | Registro da operação de pesagem de um veículo para um agendamento, reunindo peso inicial, peso final e peso líquido. Após uma pesagem `CANCELADA`, o mesmo agendamento pode ter nova pesagem. | [ARTIGO] + [DEFINIDO] (nova após cancelada, C-002) | `weighing`, `pesagem_operacao` |
| Peso inicial | `peso_inicial_kg` | Peso lido na primeira passagem pela balança, em kg, aceito conforme as regras de aceitação (BE-202). | [ARTIGO] | `peso1`, `peso_entrada` |
| Peso final | `peso_final_kg` | Peso lido na segunda passagem pela balança, após carga/descarga, em kg. | [ARTIGO] | `peso1`, `peso_entrada` |
| Tara | `tara_kg` | Peso do veículo vazio, em kg. Não entra no cálculo do peso líquido (Q-02, RN-006). A tara cadastrada no veículo **não** substitui peso medido sem regra aprovada. | [ARTIGO] (termo) + [AUTOR] (uso, RN-006) | `peso_vazio` |
| Peso bruto | `peso_bruto_kg` | Peso do veículo carregado, em kg. Não entra no cálculo do peso líquido (Q-02, RN-006). | [ARTIGO] (termo) | — |
| Peso líquido | `peso_liquido_kg` | Peso da carga, em kg, calculado a partir das pesagens inicial e final. CARGA: final − inicial; DESCARGA: inicial − final; tolerância de ±20 kg (configurável) para "sem carga nem descarga" (RN-006). Detalhes: spec `regras-pesagem` (BE-202). | [ARTIGO] (termo) + [AUTOR] (regra, Q-02) | `net_weight` |
| Tolerância de movimentação | `tolerancia_movimentacao_kg` | Faixa, em kg e configurável, em torno de zero dentro da qual o peso líquido conta como "sem carga nem descarga". Cobre queima de combustível e instabilidade da balança. Valor do autor: 20 kg. | [AUTOR] (Q-02, 2026-10-29) | `margem`, `folga` |
| Classificação do peso líquido | `COM_MOVIMENTACAO` / `SEM_MOVIMENTACAO` / `NEGATIVO_FORA_TOLERANCIA` | Resultado do cálculo do líquido (spec 002 §6.2). `SEM_MOVIMENTACAO`: o caminhão entrou e saiu sem carregar nem descarregar. `NEGATIVO_FORA_TOLERANCIA`: não aceito; o administrador intervém. | [AUTOR] (Q-02) + spec 002 | `VAZIO`, `ZERADO` |

## 3. Reconhecimento de placa (LPR)

| Termo | Identificador | Significado | Origem | Não usar |
|---|---|---|---|---|
| Leitura de placa | `leitura_placa` | Resultado do pipeline para uma imagem: origem, instante, a imagem (só em memória) e, para cada ROI, os textos lidos com a confiança. Normalização, limiar e decisão vêm depois, no domínio e na orquestração. Campos: spec 005 §5.2. | [ARTIGO] + [AUTOR] (spec 005) | `reconhecimento` |
| Placa lida | `placa_lida` | Texto **bruto** devolvido pelo OCR, antes de qualquer correção. | [AUTOR] (spec 003) | `texto_ocr` |
| Placa normalizada | `placa_normalizada` | Placa após normalização e validação de formato por regras explícitas (BE-203). Só ela é comparada com cadastros e agendamentos. Formatos aceitos: Q-10. | [AUTOR] (spec 003) | `placa_limpa` |
| Chave de comparação | `chave_comparacao` | Forma da placa usada para comparar com o cadastro. Para placa antiga, a posição 5 vira letra (0→A … 9→J, Res. CONTRAN 780/2019, Anexo II); para placa Mercosul, é a própria placa. Assim `ABC1234` e `ABC1C34` são o mesmo veículo. Não substitui a `placa_normalizada`. | [AUTOR] (spec 003, P-3) | `placa_canonica`, `placa_convertida` |
| Confiança | `confianca` | Grau de certeza informado pelo OCR, de 0 a 1, com 3 casas e **truncada para baixo** (truncar nunca aumenta a confiança). O limiar vem de configuração, sem valor padrão, e é inclusivo (RN-002). | [AUTOR] (spec 005, P-3 e P-4) | `score` |
| Texto lido | `texto_lido` | Texto que o OCR devolveu para uma ROI, com a confiança já validada e convertida. Cada texto é um candidato separado (spec 005, P-2). | [AUTOR] (spec 005) | `texto_ocr` |
| Candidato a placa | `candidato_placa` | Texto lido e confiança, entregues à seleção da placa no domínio. | [AUTOR] (spec 005 §5.3) | `palpite` |
| Placa selecionada | `placa_selecionada` | Placa escolhida pela seleção: um único veículo (pela chave de comparação), com a menor confiança entre as leituras dele, no limiar ou acima. Duas placas diferentes nunca são escolhidas automaticamente (spec 005 §6.3). | [AUTOR] (spec 005, P-5) | `placa_vencedora` |
| Acervo | `acervo` | Conjunto real de imagens de pesagens usado na avaliação do LPR. Contém dados pessoais e fica **fora do repositório** (spec 005 §12.1, Q-09). | [AUTOR] (spec 005, P-7) | `dataset` |
| Gabarito | `gabarito` | Arquivo `gabarito.csv` com a placa esperada de cada imagem do acervo (vazia quando nenhuma placa é esperada). Também fica fora do repositório (spec 005 §6.4). | [AUTOR] (spec 005) | `ground_truth` |
| Região de interesse | `roi` | Área da imagem usada pelo algoritmo (ex.: região da placa), exibida no diagnóstico. | [ARTIGO] (diagnóstico pedido pelo autor) | `regiao` |

## 4. Equipamentos

| Termo | Identificador | Significado | Origem | Não usar |
|---|---|---|---|---|
| Balança | `balanca` | Equipamento que fornece o peso do veículo (RS232 / PySerial). O banco cadastra; o modo (`SIMULADO`/`REAL`) e a comunicação vêm de variáveis de ambiente. Protocolo: Q-01. | [ARTIGO] + [DEFINIDO] (configuração, C-002) | `scale` |
| Cancela | `cancela` | Barreira física comandada pelo sistema. Há cancela de **entrada** e de **saída** (Q-15); a de entrada fica antes da balança e a de saída, depois dela; a de saída só libera após o caminhão ser identificado no perímetro correto da balança e a pesagem daquela passagem ser aceita e registrada (RN-012). Comando sem confirmação = estado desconhecido. Configuração como na balança. | [ARTIGO] + [DEFINIDO] (configuração, C-002) | `gate` |
| Tipo de veículo | `tipo_veiculo` | Classificação do veículo usada no seu cadastro. Tem cadastro próprio. | [AUTOR] (Q-14) | `categoria_veiculo` |
| Câmera | `camera` | Fonte de imagens para o LPR (rede, USB, vídeo gravado ou pasta de imagens, substituíveis). Há câmeras na frente, atrás e superior; a superior identifica a posição do caminhão, podendo combinar todas as câmeras (Q-17). Tipo e resolução: Q-06. | [ARTIGO] | — |
| Tentativas | `tentativas` | Quantas vezes uma leitura da balança ou um comando de cancela foi tentado numa chamada: no máximo 2 (0 quando a cancela já estava na posição pedida). Registrado para auditoria (spec 004 §6.2). | [AUTOR] (spec 004, P-5) | `retries` |
| Evento de cancela | `evento_cancela` | Registro de cada comando enviado a uma cancela, com motivo, resultado e instante. | [ARTIGO] (eventos) + [PROPOSTA] (campos) | `log_cancela` |
