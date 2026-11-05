# Requisitos consolidados

- **Trilha:** Comum
- **Status:** Aprovada (autor, 2026-10-29). Base da C-102, com Q-14 a Q-16; alterações da C-103 (Q-02, Q-04, Q-10, Q-13, marcadas *C-103*) aprovadas no mesmo dia. Requisitos alterados e criados depois indicam a origem na própria linha (última alteração: 2026-11-04)
- **Tarefa:** C-102 (`specs/tarefas-iniciais.md`)
- **Data:** 2026-10-29; atualizado em 2026-11-04

Fontes:

- **[ARTIGO §x]** — artigo do TCC em `docs/artigo/artigo-tcc.pdf` (seção indicada).
- **[AUTOR]** — decisão do autor registrada em `AMBIENTE.md`, `AGENTS.md` ou nas tarefas C-002/C-003 (indicado).
- **[PROPOSTA]** — sugestão ainda não aprovada.

Coluna **Lado**: `Backend`, `Frontend` ou `Ambos` (regra das trilhas, `specs/tarefas-iniciais.md` §0). Coluna **Perguntas**: dúvidas que precisam de resposta antes da spec correspondente (`AMBIENTE.md` §17).

IDs são estáveis: nunca reutilizar; requisito descartado é marcado *Obsoleto*.

---

## 1. Requisitos funcionais (RF)

### 1.1 Cadastros e agendamento

| ID | Requisito | Origem | Lado | Perguntas |
|---|---|---|---|---|
| RF-001 | O sistema deve permitir cadastrar, consultar e manter veículos, com suas respectivas placas. | [ARTIGO §1, §2, §4] | Ambos | — |
| RF-002 | O sistema deve permitir cadastrar, consultar e manter motoristas. | [ARTIGO §1, §2, §4] | Ambos | Q-08 (dados pessoais) |
| RF-003 | O sistema deve permitir cadastrar, consultar e manter transportadoras. | [ARTIGO §1, §2, §4] | Ambos | — |
| RF-004 | O sistema deve permitir que um usuário com permissão ou o motorista no autoatendimento (RF-033) crie agendamentos de operações de carga ou descarga informando veículo, motorista, transportadora (quando houver; spec 007, P-5), tipo de operação, produto, data prevista e faixa de horário (RF-028, RF-029). *C-103* | [ARTIGO §4] + [AUTOR] (criação manual, `AGENTS.md` §2; faixa de horário, Q-13) | Ambos | — |
| RF-005 | O sistema deve permitir consultar e gerenciar os agendamentos cadastrados, incluindo editar e cancelar (restrito ao administrador, RN-013). | [ARTIGO §1 "gerenciamento de agendamentos", §2] + [AUTOR] (Q-16) | Ambos | — |

### 1.2 Identificação e autorização

| ID | Requisito | Origem | Lado | Perguntas |
|---|---|---|---|---|
| RF-006 | Ao chegar o caminhão ao ponto de entrada, o sistema deve obter a imagem da placa a partir de câmera ou de imagens previamente capturadas. | [ARTIGO §2, §3.5, §4] | Backend | Q-06, Q-09 |
| RF-007 | O sistema deve reconhecer a placa na imagem por pré-processamento, localização da região da placa e leitura dos caracteres (OpenCV + EasyOCR). | [ARTIGO §2, §3.1–3.3, §4] | Backend | — |
| RF-008 | O texto reconhecido deve ser tratado (normalizado e validado quanto ao formato) antes de ser comparado com as placas cadastradas. Formatos aceitos: só placas brasileiras, antigo (`AAA9999`) e Mercosul (`AAA9A99`) (RN-017). *C-103* | [ARTIGO §3.3 "o texto reconhecido será tratado e comparado"] + [AUTOR] (Q-10) | Backend | — |
| RF-009 | O sistema deve verificar se a placa reconhecida corresponde a um veículo cadastrado com agendamento válido (ativo) para carga ou descarga. | [ARTIGO §2, §3.1, §4] | Backend | — |
| RF-010 | Quando a entrada for autorizada, o sistema deve liberar a cancela de entrada para o caminhão seguir à balança. | [ARTIGO §4] | Backend | Q-01 |

### 1.3 Cancelas, posicionamento e pesagem

| ID | Requisito | Origem | Lado | Perguntas |
|---|---|---|---|---|
| RF-011 | O sistema deve enviar comandos de abertura e fechamento às cancelas por comunicação serial RS232 (PySerial), ou à sua simulação. | [ARTIGO §1, §2, §3.4, §4] | Backend | Q-01 |
| RF-012 | **Fora do protótipo (Q-05, 2026-11-04):** o sistema não orienta o posicionamento; o procedimento fica com a equipe. Texto anterior: "O sistema deve orientar o posicionamento do caminhão na balança." | [AUTOR] (`AGENTS.md` §2 item 4) — não consta no artigo | Ambos | — |
| RF-013 | O sistema deve ler o peso informado pela balança por comunicação serial RS232 (PySerial), ou por sua simulação. | [ARTIGO §1, §2, §3.4, §4] | Backend | Q-01 |
| RF-014 | O sistema deve registrar o peso lido como pesagem inicial ou final, conforme a etapa da operação. | [ARTIGO §1, §3.5, §4] | Backend | — |
| RF-015 | O sistema deve acompanhar a etapa atual da operação, incluindo o período de carga ou descarga entre as pesagens. | [ARTIGO §3.5 "acompanha a operação", §4 "etapa atual"] | Ambos | — |
| RF-016 | O sistema deve calcular automaticamente o peso líquido da operação a partir das pesagens inicial e final. | [ARTIGO §1, §2, §3.5, §4] | Backend | — |
| RF-017 | Ao final da operação, o sistema deve liberar a saída do caminhão comandando a cancela de saída, conforme RN-012. | [ARTIGO §1 "entrada, pesagem e saída", §3.5 "liberação do caminhão", §4] + [AUTOR] (Q-15: existem cancelas de entrada e de saída) | Backend | Q-01 |

### 1.4 Registro, histórico e interface

| ID | Requisito | Origem | Lado | Perguntas |
|---|---|---|---|---|
| RF-018 | O sistema deve armazenar as informações da operação e manter o histórico das pesagens para consulta e auditoria. | [ARTIGO §2, §3.5, §4] | Backend | Q-08 |
| RF-019 | O sistema deve registrar eventos de cancela e registros do sistema. | [ARTIGO §2, §4 ("eventos de cancela e registros do sistema")] | Backend | — |
| RF-020 | A interface deve permitir consultar o histórico de pesagens e de operações realizadas. | [ARTIGO §1, §2, §3.6, §4] | Ambos | — |
| RF-021 | A interface deve oferecer uma tela operacional, em tempo real, com: chegada do caminhão, placa reconhecida, autorização de entrada, situação do agendamento, peso lido, etapa atual e comandos relacionados às cancelas. | [ARTIGO §2, §4] | Ambos | — |
| RF-022 | A interface deve permitir visualizar imagens das câmeras, as ROIs usadas pelo algoritmo e as interpretações do reconhecimento (texto lido, placa normalizada, confiança, decisão e motivo). | [AUTOR] (`AGENTS.md` §2, `AMBIENTE.md` §10.1 item 4) — não consta no artigo | Ambos | Q-06, Q-08 |
| RF-023 | A interface deve mostrar o estado dos dispositivos (comunicação com balança e cancelas, última leitura de peso, último comando e resultado) e indicar de forma visível se o modo é real ou simulado. | [AUTOR] (`AMBIENTE.md` §10.1 itens 5 e 7) — não consta no artigo | Ambos | — |
| RF-024 | O sistema deve permitir intervenção manual do **administrador** em situações de exceção, com registro rastreável (RN-016). *C-103* | [AUTOR] (`AGENTS.md` §7.2, `AMBIENTE.md` §10.1 item 6; Q-04) | Ambos | — |
| RF-025 | O sistema deve permitir cadastrar, consultar e manter produtos, usados no agendamento. | [AUTOR] (Q-14, 2026-10-29); o artigo cita "produto" no agendamento (§4) sem prever o cadastro | Ambos | — |
| RF-026 | O sistema deve permitir cadastrar, consultar e manter tipos de veículo, usados no cadastro de veículos. | [AUTOR] (Q-14, 2026-10-29) — não consta no artigo | Ambos | — |
| RF-027 | O sistema deve verificar se o caminhão está identificado dentro do perímetro correto da balança antes de aceitar a pesagem e de liberar a saída. A posição é identificada pela câmera superior, podendo combinar as imagens de todas as câmeras (Q-17, 2026-11-04). | [AUTOR] (Q-15, 2026-10-29; Q-17, 2026-11-04) — não consta no artigo | Backend | Q-06 |
| RF-028 | O administrador deve poder cadastrar e manter as **faixas de horário** do dia (início, fim e capacidade máxima de caminhões). *C-103* | [AUTOR] (Q-13, 2026-10-29) — não consta no artigo | Ambos | — |
| RF-029 | Ao criar o agendamento, o usuário escolhe uma faixa de horário com vaga, ou o sistema propõe a primeira faixa com vaga no dia; a criação continua manual (RN-001). *C-103* | [AUTOR] (Q-13, 2026-10-29) — não consta no artigo | Ambos | — |
| RF-030 | O sistema deve suportar diferentes modelos de balança, cada um com seu protocolo implementado no sistema e escolhido por configuração. Por enquanto opera uma balança, com um caminhão sobre ela por vez e várias operações abertas ao mesmo tempo, no máximo uma por placa (spec 006, P-4, 2026-11-04). | [AUTOR] (spec 004, P-8, 2026-10-29; spec 006, P-4, 2026-11-04) — não consta no artigo | Backend | Q-01 (modelos e protocolos concretos) |
| RF-031 | O controle de acesso deve permitir mais usuários e novos perfis com permissões diferentes. Perfis iniciais: `ADMINISTRADOR`, `OPERADOR` e `AUDITOR`. | [AUTOR] (Q-11, 2026-11-04) — não consta no artigo | Ambos | — |
| RF-032 | O administrador deve poder criar e desativar usuários e redefinir senhas. | [AUTOR] (ADR-0004, 2026-11-04) — não consta no artigo | Ambos | — |
| RF-033 | O motorista deve poder criar um agendamento em uma tela própria, sem login e sem operador, por totem ou pela rede do pátio. Na descarga, informa também o código da nota, digitado ou escaneado. | [AUTOR] (ADR-0004, 2026-11-04) — não consta no artigo | Ambos | Q-03 |
| RF-034 | O sistema deve analisar as imagens das câmeras em tempo real durante a operação, mesmo sem nenhuma tela aberta, usando sempre a imagem mais recente. | [AUTOR] (ADR-0005, 2026-11-04) — não consta no artigo | Backend | Q-06, Q-07, D-05 |

---

## 2. Requisitos não funcionais (RNF)

| ID | Requisito | Origem | Lado | Perguntas |
|---|---|---|---|---|
| RNF-001 | O sistema deve ser organizado em módulos — interface web, API backend, reconhecimento de placas, comunicação serial RS232 e banco de dados relacional — que possam ser desenvolvidos e testados separadamente. | [ARTIGO §2, §4] | Ambos | — |
| RNF-002 | A interface deve oferecer navegação simples e objetiva. | [ARTIGO §2 "usabilidade", §4] | Frontend | — |
| RNF-003 | A comunicação com balança e cancelas deve poder ser simulada quando não houver equipamento físico; implementações real e simulada devem ser trocáveis por configuração, com modo `SIMULADO` como padrão e hardware real só com configuração explícita. | [ARTIGO §1, §2, §4] + [AUTOR] (C-002 item 7; `AGENTS.md` §7.3) | Backend | Q-01 |
| RNF-004 | Os dados devem ser armazenados em banco de dados relacional PostgreSQL. | [ARTIGO §2, §4 (relacional)] + [AUTOR] (D-01, C-002) | Backend | — |
| RNF-005 | Os parâmetros de comunicação serial (porta, taxa de transmissão, tempo de espera) devem ser configuráveis, e toda leitura/escrita serial deve ter tempo de espera definido. | [ARTIGO §3.4] + [AUTOR] (`AGENTS.md` §7.3) | Backend | Q-01 |
| RNF-006 | O código-fonte deve ficar em repositório público, com documentação básica de instalação, configuração e execução. | [ARTIGO §4] | Ambos | D-12 (licença) |
| RNF-007 | O protótipo deve ser executável via Docker, em modo simulado, sem hardware real. | [AUTOR] (tecnologia [DEFINIDO]; `AMBIENTE.md` §6) | Ambos | Q-07 |
| RNF-008 | Tecnologias obrigatórias: Python + FastAPI (backend), OpenCV + EasyOCR (LPR), PySerial (RS232), TypeScript + Tailwind CSS (frontend), Docker. | [ARTIGO §1, §2, §4] + [AUTOR] (`AGENTS.md` §3; TypeScript prevalece sobre o JavaScript do artigo) | Ambos | — |
| RNF-009 | Em qualquer dúvida o sistema não autoriza, não aciona e não registra peso, mantendo estado seguro e encaminhando ao operador (fail-safe). | [AUTOR] (`AGENTS.md` §7.1) | Backend | — |
| RNF-010 | Eventos relevantes (reconhecimentos, decisões de autorização, comandos, leituras de peso aceitas, falhas, intervenções manuais) devem ser registráveis para auditoria. | [ARTIGO §1, §3.5 (rastreabilidade)] + [AUTOR] (`AGENTS.md` §7.1.6) | Backend | — |
| RNF-011 | OCR, leitura serial e captura de imagem não devem bloquear o atendimento de requisições da API. | [AUTOR] (`AGENTS.md` §10) | Backend | D-05 |
| RNF-012 | O módulo de reconhecimento deve ser avaliado com imagens em diferentes condições de enquadramento e iluminação, de forma reprodutível sem câmera conectada. | [ARTIGO §2, §3.1] + [AUTOR] (`AGENTS.md` §8) | Backend | Q-09 |
| RNF-013 | Dados pessoais (placas, motoristas) e imagens não devem ser registrados nem expostos além do necessário. | [AUTOR] (`AGENTS.md` §7.3) | Ambos | Q-08 |
| RNF-014 | Decisões de segurança (autorização, aceitação de peso, acionamento de cancela) ficam no backend; a interface apenas apresenta e solicita ações. | [AUTOR] (`AGENTS.md` §7.3; S-5) | Ambos | — |

---

## 3. Regras de negócio (RN)

| ID | Regra | Origem | Lado | Perguntas |
|---|---|---|---|---|
| RN-001 | Agendamentos são criados somente por ação humana: por usuário com permissão (ADR-0004) ou pelo motorista no autoatendimento (RF-033, RN-021). O sistema nunca cria agendamento automaticamente. | [ARTIGO §4] + [AUTOR] (`AGENTS.md` §2, §12; ADR-0004, 2026-11-04) | Backend | — |
| RN-002 | A entrada só é autorizada quando, cumulativamente: a placa foi reconhecida com confiança igual ou superior ao limiar configurado; a placa normalizada tem formato válido; corresponde a um veículo cadastrado e ativo (spec 007); existe **um único** agendamento válido para ele; e o estado da operação permite a autorização. | [ARTIGO §2 "autoriza apenas veículos previamente cadastrados e com agendamento válido"] + [AUTOR] (`AGENTS.md` §7.1.2) | Backend | — |
| RN-003 | Reconhecimento inconclusivo, veículo não cadastrado, ausência de agendamento ou mais de um candidato: não autorizar, registrar o evento e encaminhar ao operador com a evidência (imagem, ROI, leitura). | [ARTIGO §2 (cenários)] + [AUTOR] (`AGENTS.md` §7.2) | Backend | — |
| RN-004 | Uma leitura de peso só é aceita se estiver bem formada, dentro de faixa plausível e estável; os parâmetros vêm de configuração. Leitura rejeitada nunca é ajustada nem preenchida. | [AUTOR] (`AGENTS.md` §7.2) | Backend | Q-01 |
| RN-005 | Em falha ou tempo esgotado na comunicação com a balança, o peso não é registrado; a falha é sinalizada e o estado seguro é mantido. | [ARTIGO §2 (cenário)] + [AUTOR] (`AGENTS.md` §7.2) | Backend | — |
| RN-006 | O peso líquido é calculado a partir das pesagens inicial e final efetivamente medidas; nenhum valor não medido (ex.: tara cadastrada no veículo) as substitui sem regra aprovada. Fórmula: **CARGA** → `peso_final_kg − peso_inicial_kg`; **DESCARGA** → `peso_inicial_kg − peso_final_kg`. **Tolerância de movimentação**, configurável (valor do autor: **20 kg**, para cobrir queima de combustível e instabilidade da balança): se o líquido estiver entre −20 e +20 kg, inclusive, a operação é aceita como **sem carga nem descarga**, ou seja, o caminhão entrou e saiu sem movimentar carga. Líquido **abaixo da tolerância negativa** não é aceito e vai para o administrador. Os pesos medidos e o líquido calculado são registrados como lidos, **nunca ajustados para zero** (RN-004); a forma de registrar a classificação "sem movimentação" é definida na BE-202. *C-103* | [ARTIGO §1, §4] + [AUTOR] (`AGENTS.md` §7.2; Q-02) | Backend | — |
| RN-007 | Comando à cancela só é emitido se o estado da operação permitir; comando sem confirmação é tratado como estado desconhecido; retentativas só com política definida e nunca ilimitadas. | [AUTOR] (`AGENTS.md` §7.1.3–7.1.4) | Backend | Q-01 |
| RN-008 | Um veículo não pode ter mais de uma operação/pesagem em andamento ao mesmo tempo; placas diferentes podem ter operações abertas simultaneamente. | [AUTOR] (spec 006, P-4, 2026-11-04) | Backend | — |
| RN-009 | Após uma pesagem `CANCELADA`, o mesmo agendamento pode receber nova pesagem; a pesagem cancelada permanece no histórico. | [AUTOR] (C-002 item 3, `AMBIENTE.md` §0.4) | Backend | — |
| RN-010 | Transições de estado inválidas são rejeitadas e registradas, nunca corrigidas silenciosamente. | [AUTOR] (`AGENTS.md` §7.1.5) | Backend | — |
| RN-011 | Toda intervenção manual registra o responsável e o motivo. | [AUTOR] (`AMBIENTE.md` §10.1 item 6) | Backend | — |
| RN-012 | A cancela de saída só é liberada quando, cumulativamente, o caminhão foi identificado no perímetro correto da balança **e** a pesagem daquela passagem foi aceita e registrada. Ela abre depois da pesagem inicial, para o caminhão seguir à carga ou descarga, e depois da pesagem final, para a saída definitiva; só a pesagem final encerra a operação (Q-17 e spec 006, 2026-11-04). Caso contrário, a cancela de saída permanece fechada e a situação é encaminhada ao operador. | [AUTOR] (Q-15, 2026-10-29; Q-17, 2026-11-04) + [AUTOR] (`AGENTS.md` §7.1) | Backend | — |
| RN-013 | Somente o administrador do sistema pode editar ou cancelar agendamentos. O cancelamento registra o responsável e o motivo. | [AUTOR] (Q-16, 2026-10-29; spec 008, P-4, 2026-11-04) | Backend | — |
| RN-014 | Um agendamento só vale no seu dia (`data_prevista`). Placa identificada **antes** do início da faixa de horário: não autoriza, registra e encaminha. **Depois** do fim da faixa, no mesmo dia: pode autorizar, se as demais condições da RN-002 forem atendidas. Em **outro dia**: não autoriza. *C-103* | [AUTOR] (Q-13, 2026-10-29) | Backend | — |
| RN-015 | Uma faixa de horário não aceita mais agendamentos do que a sua capacidade; agendamentos cancelados liberam a vaga. *C-103* | [AUTOR] (Q-13; liberação da vaga ao cancelar aprovada em 2026-10-29) | Backend | — |
| RN-016 | Somente o administrador pode fazer liberação manual, ou seja, substituir uma decisão automática de não autorizar. *C-103* | [AUTOR] (Q-04, 2026-10-29) | Backend | — |
| RN-017 | Placa válida tem só um de dois formatos brasileiros: antigo `AAA9999` ou Mercosul `AAA9A99`. Qualquer outro formato é rejeitado e encaminhado. *C-103* | [AUTOR] (Q-10, 2026-10-29) | Backend | — |
| RN-018 | Na volta para a pesagem final, a cancela de entrada só abre se a placa, lida com a mesma exigência de confiança e formato da RN-002, corresponder à operação aberta daquele veículo que está em carga ou descarga. Sem isso, a cancela não abre e o caso é encaminhado. | [AUTOR] (spec 006, P-2a, 2026-11-04) | Backend | — |
| RN-019 | A balança recebe um caminhão por vez: a cancela de entrada só abre com a balança livre e reservada para aquela operação. | [AUTOR] (spec 006, P-4a, 2026-11-04) | Backend | — |
| RN-020 | O operador ou o administrador podem liberar, com responsável e motivo, um caminhão que está na balança e teve a operação cancelada. Isso não substitui decisão de autorização (RN-016). | [AUTOR] (spec 006, P-7, 2026-11-04) | Backend | — |
| RN-021 | No autoatendimento, o agendamento só é criado se a placa e o CPF corresponderem a um veículo e a um motorista cadastrados. Caso contrário, nada é criado, e a resposta não revela o que falhou. As regras de faixa (RN-014, RN-015) continuam valendo. O código da nota é guardado sem verificar a autenticidade. | [AUTOR] (ADR-0004, 2026-11-04) | Backend | — |
| RN-022 | Só são salvas as imagens usadas nas decisões (placa aceita ou rejeitada, posição confirmada, intervenções). Elas ficam guardadas até o administrador pedir a exclusão, que registra o responsável e o motivo e não apaga os demais dados da operação. O `AUDITOR` vê essas imagens, mas não as imagens em tempo real. | [AUTOR] (Q-08, 2026-11-04) | Backend | Q-08 (LGPD) |
| RN-023 | Uma placa não pode ter dois agendamentos abertos (`AGENDADO` ou `EM_ANDAMENTO`) ao mesmo tempo, em nenhuma data. Um novo agendamento, inclusive no mesmo dia, só é aceito depois que o anterior estiver encerrado (`CONCLUIDO`, `CANCELADO` ou `EXPIRADO`). | [AUTOR] (spec 008, P-2, 2026-11-04) | Backend | — |
| RN-024 | Uma faixa de horário já encerrada no dia não aceita novos agendamentos. Quem já tinha agendamento e chega depois da faixa segue a RN-014. | [AUTOR] (spec 008, P-3, 2026-11-04) | Backend | — |

---

## 4. Cenários de validação do artigo

Cenários de teste em ambiente controlado previstos no **[ARTIGO §2]**, ligados aos requisitos que verificam. Cada um vira critério(s) de aceitação nas specs correspondentes, acrescido dos casos de falha do `AGENTS.md` §7.2.

| # | Cenário | Requisitos verificados |
|---|---|---|
| 1 | Veículo com agendamento válido | RF-006, RF-007, RF-008, RF-009, RF-010, RN-002 |
| 2 | Veículo sem agendamento | RF-009, RN-003 |
| 3 | Falha no reconhecimento da placa | RF-007, RF-008, RN-003 |
| 4 | Leitura de peso pela comunicação serial | RF-013, RF-014, RN-004 |
| 5 | Falha de comunicação com a balança | RN-005, RNF-005, RNF-009 |
| 6 | Acionamento de cancela | RF-011, RF-017, RN-007, RN-012 |
| 7 | Finalização da operação com cálculo do peso líquido | RF-016, RF-018, RN-006 |

Critérios de análise por módulo, também do **[ARTIGO §2]**:

| Módulo | Critério do artigo | Requisitos |
|---|---|---|
| Cadastro | Dados de veículos, motoristas, transportadoras e agendamentos são salvos, consultados e utilizados corretamente. | RF-001 a RF-005, RF-025, RF-026 |
| Reconhecimento de placas | Identifica os caracteres nas imagens testadas e os relaciona aos registros do banco. | RF-007, RF-008, RF-009, RNF-012 |
| Agendamento | Autoriza apenas veículos previamente cadastrados e com agendamento válido. | RF-009, RN-002, RN-003 |
| Pesagem | Leitura ou simulação dos dados recebidos pela comunicação serial. | RF-013, RNF-003 |
| Cancelas | Envio correto dos comandos de abertura e fechamento. | RF-011 |
| Operação | Registra as informações, mantém o histórico e calcula o peso líquido a partir das pesagens inicial e final. | RF-016, RF-018 |

---

## 5. Perguntas em aberto

Lista completa: `AMBIENTE.md` §17 (Q-01 a Q-17). Respostas que afetam requisitos, inclusive as de perguntas surgidas na leitura do artigo:

| ID | Pergunta | Resposta do autor (2026-10-29) | Requisitos |
|---|---|---|---|
| Q-14 | Cadastros de produtos e de tipos de veículo fazem parte do escopo? | Sim. | RF-025, RF-026 |
| Q-15 | Como é liberada a saída do caminhão? | Existem cancela de entrada e de saída. A de saída só libera após o caminhão ser identificado no perímetro correto da balança e estar pesado. | RF-017, RF-027, RN-012 |
| Q-16 | Quem pode editar e cancelar agendamentos? | Apenas o administrador do sistema. | RF-005, RN-013 |
| Q-02 | Regra das pesagens e do peso líquido | CARGA: final − inicial; DESCARGA: inicial − final. Dentro de ±20 kg (configurável) conta como sem carga nem descarga; abaixo disso, o administrador intervém. | RN-006 |
| Q-04 | Intervenção manual e segurança física | Só o administrador faz liberação manual. Existem intertravamentos físicos, sensores de presença e parada de emergência independentes do software, mas o software não depende deles (`AGENTS.md` §7.1.7). | RF-024, RN-016 |
| Q-10 | Padrões de placa | Só brasileiras: antigo e Mercosul. | RF-008, RN-017 |
| Q-13 | Validade do agendamento | Vale só no dia. Faixas fixas com capacidade; quem agenda escolhe a faixa ou recebe a primeira com vaga. Antes da faixa não libera; depois, no mesmo dia, libera. | RF-004, RF-028, RF-029, RN-014, RN-015 |
| Q-17 | Como o sistema identifica que o caminhão está "no perímetro correto da balança" (sensores de presença, câmera, confirmação do operador)? E "estar pesado" significa pesagem final aceita e registrada? | **Respondida (2026-11-04):** a câmera superior identifica a posição, podendo combinar as imagens de todas as câmeras; "estar pesado" = pesagem final aceita e registrada. O critério de análise das imagens será definido em spec. | RF-027, RN-012 |
| Q-05 | Orientação de posicionamento na balança | **Respondida (2026-11-04):** fora do protótipo; o procedimento fica com a equipe. | RF-012 |
| Q-11 | Usuários, perfis e controle de acesso | **Respondida (2026-11-04):** por enquanto, `ADMINISTRADOR`, `OPERADOR` (acompanha e solicita ações) e `AUDITOR` (só consulta). Deve permitir mais usuários e perfis com permissões diferentes (RF-031). A estratégia de autenticação foi decidida na CT-001 (ADR-0004). | RN-001, RN-013, RF-031 |
| Q-12 | Volume e pontos de pesagem | **Parcial (2026-11-04, spec 006):** por enquanto uma balança, com um caminhão por vez e várias operações abertas, no máximo uma por placa. **Aberto:** volume esperado. | RF-030, RN-008, RN-019 |
| Q-08 | Imagens de evidência | **Parcial (2026-11-04):** só as imagens das decisões são salvas, até o administrador pedir a exclusão; o `AUDITOR` vê as das decisões, mas não as em tempo real. **Aberta:** adequação à LGPD. | RF-018, RF-022, RN-022, RNF-013 |

## 6. Divergências entre o artigo e as decisões do autor

| Tema | Artigo | Decisão vigente |
|---|---|---|
| Início da automação | §3.5: "a automação inicia-se no agendamento" | Agendamento é **manual**; a automação cobre as etapas seguintes (`AGENTS.md` §2). RN-001. |
| Quem agenda | §4: usuário autorizado | Também o motorista, no autoatendimento, sem login (RF-033, RN-021, ADR-0004). Continua sendo ação humana. |
| Interface | §2, §4: HTML + Tailwind CSS + JavaScript | TypeScript + Tailwind CSS (`AGENTS.md` §3). RNF-008. |
| Diagnóstico de visão computacional, estado dos dispositivos, orientação de posicionamento | Não mencionados | Incluídos por decisão do autor (RF-022, RF-023). A orientação de posicionamento (RF-012) saiu do protótipo (Q-05, 2026-11-04). |
| Licença | §4: "poderá ser definida uma licença" | `LICENSE` MIT já existe no repositório, mas D-12 consta como pendente (C-001). |
