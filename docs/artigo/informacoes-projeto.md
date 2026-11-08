# EasyScale — informações do projeto para o artigo

Consolidação do que foi construído, com que tecnologias, com que escopo e com que resultados, para atualizar o artigo do TCC. Estado do repositório em 2026-11-08.

Cada seção indica, quando aplicável, a fonte no repositório (spec, ADR ou arquivo), para conferência.

---

## 1. Resumo do que foi entregue

Protótipo funcional de sistema web, open-source, que automatiza as etapas da pesagem rodoviária posteriores ao agendamento:

- identificação do caminhão pela placa (OpenCV + EasyOCR);
- validação da placa contra o agendamento do dia;
- controle de duas cancelas (entrada e saída da balança);
- conferência da posição do caminhão na balança pela câmera superior;
- leitura do peso, com aceitação só de leituras válidas e estáveis;
- registro das pesagens inicial e final e cálculo do peso líquido;
- histórico completo e auditável de cada operação.

O sistema funciona de ponta a ponta em **modo simulado**: balança, cancelas e câmeras são substituídas por simuladores configuráveis. A camada de comunicação serial com a balança (PySerial) está implementada, mas nenhum protocolo de equipamento real foi integrado, e nada foi testado com balança, cancela ou câmera físicas.

---

## 2. Escopo

### 2.1 Dentro do escopo (implementado)

| Área | O que existe |
|---|---|
| Cadastros | Veículos (placa antiga e Mercosul), motoristas, transportadoras, produtos e tipos de veículo |
| Agendamento | Criação **manual** por usuário com permissão; faixas de horário com capacidade; sugestão da primeira faixa com vaga; edição e cancelamento só pelo administrador |
| Autoatendimento | Tela de totem em que o próprio motorista agenda, sem login, só pela rede do pátio; confere placa e CPF; na descarga, exige o código da nota |
| Identificação | Pipeline de reconhecimento de placa (pré-processamento, localização, OCR, normalização, seleção conservadora) |
| Autorização | Regra explícita: confiança mínima, formato válido, veículo cadastrado, agendamento único e válido no dia, dentro da faixa |
| Operação | Máquina de estados explícita com 20 situações, do aguardo da balança até `FINALIZADA` ou `CANCELADA` |
| Dispositivos | Interfaces abstratas de balança, cancela e posição, com simuladores; transporte serial da balança (PySerial) pronto para receber protocolos |
| Pesagem | Critério de estabilidade configurável; faixa plausível; cálculo do líquido com tolerância |
| Interface | Tela operacional em tempo real, histórico, diagnóstico do reconhecimento (imagem, ROIs, interpretações), estado dos dispositivos, intervenção manual, usuários |
| Segurança | Login com sessão no banco, três perfis (administrador, operador, auditor), permissões por ação, comportamento à prova de falha |
| Execução | Docker Compose com banco, migração, backend e frontend com HTTPS |

### 2.2 Fora do escopo

- **Automatizar o agendamento.** Ele é sempre uma ação humana (usuário ou motorista no totem).
- **Orientar o posicionamento do caminhão na balança** (semáforo, painel etc.). Decidido fora do protótipo; o procedimento fica com a equipe do pátio. O sistema apenas **verifica** a posição.
- Integração com ERP, emissão de documentos fiscais e cobrança.
- Conferência da nota fiscal: o código da nota é guardado na descarga, mas não é verificado.
- Equipamento real: protocolos de balança, comandos das cancelas e fontes de câmera real.

### 2.3 Mudanças em relação ao artigo (proposta original)

| Tema | Artigo | Como ficou | Motivo |
|---|---|---|---|
| Interface | HTML + Tailwind + JavaScript | **TypeScript + React + Tailwind CSS**, com Vite | Tipagem estrita e componentização para uma interface com muitas telas e atualização em tempo real |
| Banco | "relacional" | **PostgreSQL** | Restrições avançadas (índices parciais para "uma operação aberta por placa"), concorrência de escrita, transações |
| Agendamento | Cadastro pelo usuário | Usuário **ou** motorista no totem de autoatendimento; faixas de horário com capacidade | Reduzir trabalho do operador mantendo o ato humano de agendar |
| Cancelas | "cancela" | **Duas cancelas**: entrada e saída da balança | Fluxo real do pátio: o caminhão sai pela saída após cada pesagem e volta pela entrada |
| Posição na balança | Não detalhado | **Câmera superior** confirma o caminhão em posição antes de aceitar o peso e de liberar a saída | Evitar peso registrado com o caminhão fora da plataforma |
| Peso bruto e tara | Mencionados na introdução | O cálculo usa só as duas pesagens medidas, sem mapear para tara/bruto | Carga: final − inicial; descarga: inicial − final |
| Perfis | "usuário" e "administrador" | Administrador, operador e auditor, com permissões por ação | Separar quem opera, quem audita e quem intervém |
| Diagnóstico | Não previsto | Tela que mostra imagem, ROIs e interpretações do reconhecimento | Inspeção e explicação das decisões do algoritmo |

---

## 3. Metodologia de desenvolvimento

- **Desenvolvimento orientado por especificação.** Cada funcionalidade passou por: requisitos → especificação (comportamento normal, comportamento em falha, critérios de aceitação verificáveis) → análise de impacto → plano → implementação → testes ligados aos critérios → revisão. Foram escritas **29 especificações** (`specs/features/`).
- **Registro de decisões de arquitetura (ADR).** Oito decisões registradas com contexto, opções consideradas e consequências (`docs/decisoes/`).
- **Rastreabilidade.** Requisitos com identificadores estáveis (RF, RNF, RN); cada teste cita o critério de aceitação ou requisito que verifica.
- **Segurança operacional como prioridade.** Princípio *fail-safe*: em qualquer dúvida o sistema não autoriza, não aciona cancela e não registra peso, e encaminha ao operador.
- **Validação em ambiente controlado**, como previsto no artigo: simuladores de balança, cancelas, posição e câmera, com cenários de falha configuráveis.

### 3.1 Requisitos levantados

`specs/requisitos.md` reúne **34 requisitos funcionais** (RF-001 a RF-034; RF-012 tornou-se fora do escopo), **14 não funcionais** (RNF-001 a RNF-014) e **24 regras de negócio** (RN-001 a RN-024), cada um com a origem (artigo ou decisão do autor).

Principais regras de negócio:

| Regra | Conteúdo |
|---|---|
| RN-001 | Agendamento só por ação humana |
| RN-002 | Entrada só com placa de confiança ≥ limiar, formato válido, veículo cadastrado e ativo, **um único** agendamento válido no dia e estado compatível |
| RN-003 | Leitura inconclusiva, veículo não cadastrado, sem agendamento ou ambiguidade: não autoriza, registra e mostra a evidência ao operador |
| RN-004 | Peso só aceito se bem formado, dentro da faixa e estável; leitura rejeitada nunca é ajustada |
| RN-006 | Líquido: carga = final − inicial; descarga = inicial − final; entre −20 e +20 kg (tolerância configurável) = sem movimentação; abaixo disso, intervenção do administrador |
| RN-007 | Comando de cancela sem confirmação = estado desconhecido; sem retentativa ilimitada |
| RN-008 | Uma operação aberta por veículo |
| RN-012 | Saída só com caminhão em posição **e** pesagem daquela passagem aceita e registrada |
| RN-014 | Agendamento vale no dia; antes da faixa não libera; depois, no mesmo dia, libera |
| RN-016 | Só o administrador substitui uma decisão automática de não autorizar |
| RN-017 | Só placas brasileiras: antiga `AAA9999` e Mercosul `AAA9A99` |
| RN-018 | Na volta, a placa é lida de novo com a mesma exigência |
| RN-019 | Um caminhão por vez na balança |
| RN-022 | Só as imagens usadas em decisões são guardadas, até o administrador pedir a exclusão |

---

## 4. Tecnologias

### 4.1 Backend (Python)

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | ≥ 3.12 (usado com 3.14) | Linguagem do backend |
| FastAPI | 0.162.0 | API HTTP, validação de entrada, rotas |
| Uvicorn | 0.54.0 | Servidor ASGI (um processo) |
| Pydantic | 2.14.1 | Esquemas de entrada e saída da API |
| SQLAlchemy (Core) | 2.1.6 | Acesso ao banco, sem ORM de entidades |
| psycopg | 3.3.6 | Driver PostgreSQL |
| Alembic | 1.20.1 | Migrações do banco, em SQL escrito à mão |
| PySerial | 3.5 | Comunicação serial RS232 com a balança |
| OpenCV (`opencv-python-headless`) | 4.14.0.94 | Pré-processamento, localização da placa, desenho de ROIs, geração da cena simulada |
| EasyOCR | 1.7.2 | Leitura dos caracteres da placa |
| PyTorch / torchvision | 2.14.1 / 0.29.1 (CPU) | Dependência do EasyOCR, sem GPU |
| `hashlib.scrypt` (biblioteca padrão) | — | Hash das senhas |

Ferramentas de qualidade: **pytest 9.1.1**, pytest-cov 7.1.0, **ruff 0.17.0** (lint e formatação), **mypy 2.4.0** em modo estrito, httpx 0.28.1 (cliente de teste).

### 4.2 Frontend (TypeScript)

| Tecnologia | Versão | Uso |
|---|---|---|
| TypeScript | 6.0.3 | Linguagem, em modo estrito |
| React / React DOM | 19.3.1 | Componentes da interface |
| React Router | 8.5.0 | Navegação entre telas |
| Tailwind CSS | 4.3.3 | Estilos |
| Vite | 8.3.5 | Servidor de desenvolvimento e build |
| Vitest | 5.0.5 | Testes |
| Testing Library | React 16.3.3, DOM 10.4.2 | Testes de componentes pelo comportamento do usuário |
| ESLint / Prettier | 10.13.0 / 3.9.10 | Lint e formatação |

Sem biblioteca de estado nem de componentes visuais: só React, React Router e Tailwind.

### 4.3 Infraestrutura

| Tecnologia | Versão | Uso |
|---|---|---|
| Docker / Docker Compose | 29.x / 5.x | Execução reproduzível |
| PostgreSQL | 18.6 (imagem `postgres:18.6-alpine`) | Banco de dados |
| Caddy | 2.11.6 | Serve o frontend, faz HTTPS (CA interna por padrão) e repassa `/api` ao backend |

---

## 5. Arquitetura

### 5.1 Visão geral

**Monólito modular** (ADR-0002): um único processo de backend, dividido em módulos com fronteiras verificadas por teste automatizado (um teste falha se um módulo importar outro que não deveria).

```
Navegador (React)  ──HTTPS──►  Caddy  ──/api──►  Backend FastAPI (um processo)
   ▲  SSE (eventos)                                 │
   └────────────────────────────────────────────────┤
                                                    ├── dominio/       regras puras (placa, autorização, pesagem, máquina de estados)
                                                    ├── orquestracao/  fluxo da operação, eventos, reserva da balança
                                                    ├── lpr/           fontes de imagem, pipeline OpenCV + EasyOCR, posição
                                                    ├── dispositivos/  balança e cancelas (simuladas; balança serial)
                                                    ├── persistencia/  SQLAlchemy Core + Alembic
                                                    └── api/           rotas, sessão, permissões, validação
                                                             │
                                                        PostgreSQL
```

- **Domínio sem I/O.** Normalização de placa, seleção de placa, decisão de autorização, regras de pesagem e máquina de estados são funções puras, testáveis sem banco, câmera ou serial.
- **Dispositivos atrás de interfaces.** `Balanca`, `Cancela` e a fonte de posição têm implementação simulada e real trocáveis por variável de ambiente. O modo `SIMULADO` é o padrão; o modo `REAL` exige configuração explícita e hoje é recusado na partida.
- **Operações bloqueantes fora do laço da API.** OCR, análise de imagem e acesso ao banco rodam em `asyncio.to_thread`; dispositivos são assíncronos. A análise das câmeras roda continuamente no backend, mesmo sem nenhuma tela aberta.
- **Tempo real por SSE** (Server-Sent Events, ADR-0005): o backend envia eventos da operação; imagens são pedidas sob demanda.

### 5.2 Decisões de arquitetura (ADRs)

| ADR | Decisão |
|---|---|
| 0001 | PostgreSQL como banco |
| 0002 | Monólito modular, um processo, um único dono por porta serial |
| 0003 | pytest, pytest-cov, ruff e mypy estrito no backend |
| 0004 | Sessão no banco com cookie; permissões no código, perfis no banco; autoatendimento sem login, restrito à rede do pátio |
| 0005 | SSE para eventos e imagens sob demanda; análise das imagens em tempo real no backend |
| 0006 | SQLAlchemy 2 Core + psycopg 3 + Alembic, com migrações em SQL |
| 0007 | React + Vite + React Router, Tailwind CSS v4 |
| 0008 | Vitest + Testing Library, ESLint, Prettier, `tsc` estrito |

### 5.3 Banco de dados

22 tabelas criadas pela migração inicial: `perfil`, `perfil_permissao`, `usuario`, `sessao`, `tentativa_acesso`, `transportadora`, `motorista`, `tipo_veiculo`, `veiculo`, `produto`, `balanca`, `cancela`, `ponto_controle`, `camera`, `faixa_horario`, `agendamento`, `pesagem`, `imagem_decisao`, `leitura_placa`, `liberacao_caminhao`, `evento_operacao`, `registro_auditoria`. Quatro migrações no total.

Regras garantidas no banco por índices únicos parciais, e não só no código: uma pesagem não cancelada por agendamento, uma operação aberta por veículo, um agendamento aberto por veículo e uma única operação com a balança reservada. As imagens de evidência ficam no próprio banco (`bytea`), gravadas na mesma transação da decisão.

---

## 6. Módulos em detalhe

### 6.1 Reconhecimento de placa (LPR)

Segue as etapas de ALPR descritas no artigo (Du et al., 2013):

1. **Aquisição.** Fonte de imagem substituível: pasta de imagens (testes e avaliação) ou câmera simulada. Imagem mais velha que um limite configurável é descartada.
2. **Pré-processamento (OpenCV).** Conversão para tons de cinza e detecção de bordas (Canny).
3. **Localização.** Retângulo envolvente de cada contorno; ficam os de área e proporção largura/altura dentro de parâmetros configuráveis, da maior área para a menor, até um máximo de ROIs.
4. **Leitura (EasyOCR).** Cada ROI é lida; cada texto devolvido vira um candidato. O EasyOCR roda em CPU, com modelos baixados uma única vez por comando explícito (a operação nunca baixa nada). Não se restringe o alfabeto do OCR, porque isso trocaria um caractere estranho por um "parecido" e poderia formar uma placa válida errada.
5. **Confiança.** Convertida para decimal com 3 casas, truncada para baixo (nunca aumenta).
6. **Normalização** (função pura). Aceita só os formatos antigo e Mercosul. Corrige confusões típicas do OCR por posição (letra × dígito): O/0, I/1, B/8, S/5, Z/2, G/6, A/4 e T/7, registrando cada correção aplicada. Placas antiga e Mercosul equivalentes são comparadas pela tabela de conversão oficial da Resolução CONTRAN nº 780/2019. As correções valem só para leituras da câmera, nunca para placa digitada.
7. **Seleção conservadora.** Sem candidato válido → rejeita. Mais de uma placa distinta → **ambígua**, nunca escolhe sozinho. Confiança do grupo = a **menor** entre as leituras da mesma placa. Abaixo do limiar → rejeita.

O pipeline devolve todas as interpretações, inclusive as rejeitadas, para a tela de diagnóstico.

### 6.2 Posição do caminhão

A câmera superior informa se o caminhão está em posição: `CONFIRMADA`, `AUSENTE` ou `INCONCLUSIVA`. O peso só é lido com o caminhão confirmado em posição, e a cancela de saída só fecha com a balança vazia. O critério real de análise da imagem ainda não foi definido; hoje a fonte de posição é simulada.

### 6.3 Balança

- Interface abstrata com simulador de cenários: `ESTAVEL`, `INSTAVEL`, `SEM_RESPOSTA`, `QUADRO_CORROMPIDO`, `DESCONECTADA`.
- **Critério de estabilidade** decidido pelo software: N leituras seguidas com variação máxima configurada, dentro de uma janela de tempo; peso entre um mínimo e um máximo plausíveis. Todos os parâmetros vêm de configuração, sem valor padrão no código.
- **`BalancaSerial`** (PySerial): transporte serial com timeout em toda leitura e escrita; parâmetros (porta, baud rate, paridade, bits de dados e de parada, timeout) por variável de ambiente. Os protocolos de cada modelo de indicador entram num registro (nome → implementação), hoje vazio. Há um roteiro documentado para integrar um modelo a partir do manual e de quadros reais capturados (`docs/equipamentos/README.md`).

### 6.4 Cancelas

- Duas cancelas, de entrada e de saída, cada uma com sensor de status.
- O comando só é emitido se o estado da operação permitir. O resultado é confirmado pelo sensor; **sem confirmação, o estado passa a desconhecido** (nunca é assumido aberto nem fechado) e a operação para à espera de intervenção.
- Simulador com cenários `FALHA`, `NAO_MOVE` e `SENSOR_SEM_RESPOSTA`.
- A implementação serial da cancela não foi feita, porque depende do controlador real e de como o sensor chega ao computador.

### 6.5 Máquina de estados da operação

20 situações explícitas. Fluxo normal:

`AGUARDANDO_BALANCA_INICIAL` → `AUTORIZADA` → `ENTRADA_LIBERADA` → `FECHANDO_ENTRADA` → `POSICIONADA_INICIAL` → `PESO_INICIAL_OK` → `SAIDA_INICIAL_LIBERADA` → `FECHANDO_SAIDA_INICIAL` → `EM_CARGA_DESCARGA` → `AGUARDANDO_BALANCA_FINAL` → `RETORNO_AUTORIZADO` → `RETORNO_LIBERADO` → `FECHANDO_ENTRADA_RETORNO` → `POSICIONADA_FINAL` → `PESO_FINAL_OK` → `SAIDA_LIBERADA` → `FECHANDO_SAIDA` → `FINALIZADA`

Além delas: `AGUARDANDO_INTERVENCAO`, uma parada segura sem comandos que guarda a situação anterior e o motivo, e `CANCELADA`.

- Transições inválidas são rejeitadas e registradas, nunca corrigidas em silêncio.
- Controle de concorrência por versão: uma ação com versão desatualizada é recusada.
- **Retomada após reinício:** o estado vem do banco; um comando de cancela interrompido não é reenviado às cegas.
- A balança é reservada para uma operação por vez, em ordem de chegada.
- Falhas de identificação não criam operação: viram eventos com evidência.

### 6.6 Interface

| Tela | Conteúdo |
|---|---|
| Login | Única tela aberta sem sessão, além do totem |
| Cadastros | Veículos, motoristas, transportadoras, produtos, tipos de veículo |
| Agendamentos | Lista do dia, faixas de horário, criação manual com sugestão de faixa, edição e cancelamento pelo administrador |
| Autoatendimento (totem) | Passo a passo com teclado na tela, conferência com CPF mascarado; volta ao início após 60 s sem uso |
| Operação | Em tempo real: placa reconhecida, decisão, situação do agendamento, peso lido (marcado "não é peso aceito" até ser aceito), etapa, cancelas |
| Histórico | Pesagens, peso líquido e todos os eventos de cada operação |
| Diagnóstico | Imagem da câmera com as ROIs sobrepostas, texto lido, placa normalizada, formato, confiança, decisão e motivo |
| Dispositivos e intervenção | Estado da balança, cancelas, posição e identificação; tentar comando de novo, liberação manual, liberar caminhão cancelado (sempre com motivo) |
| Usuários | Criar, desativar, redefinir senha; perfis |

- Indicação permanente do modo (**SIMULADO**/**REAL**) no cabeçalho.
- Se o servidor parar de responder, a tela mostra "Tela desatualizada", bloqueia as ações e deixa o modo como desconhecido.
- Nenhuma decisão de segurança fica no frontend: a interface só mostra e pede ações.

### 6.7 API

Cerca de 55 operações HTTP (`/api/...`): sessões, usuários e perfis, cadastros, faixas de horário, agendamentos, autoatendimento, operação (estado e eventos SSE), pesagens e eventos, diagnóstico (leituras de placa, imagens de decisão, dispositivos, imagem atual da câmera), liberações manuais e, só em modo simulado, controle dos simuladores (chegada de placa, balança, posição, cancelas).

### 6.8 Segurança da aplicação

- Senhas com `scrypt`; sessão no banco; cookie `HttpOnly`, `Secure`, `SameSite=Strict`, restrito a `/api`; expiração por inatividade.
- Bloqueio de login após tentativas falhas; conferência do cabeçalho `Origin` nas operações de escrita.
- Autoatendimento só a partir de redes configuradas, com bloqueio por tentativas; a resposta não revela se o erro foi na placa ou no CPF.
- CPF mascarado na interface; imagens guardadas só quando usadas em decisões.
- HTTPS obrigatório na execução pelo Compose; só o frontend publica porta; banco e backend ficam na rede interna.

---

## 7. Resultados

### 7.1 Testes automatizados

| Conjunto | Quantidade | O que cobre |
|---|---|---|
| Backend, unitários | 861 | Domínio (611), dispositivos (74), orquestração (69), LPR (52), configuração e fronteiras entre módulos |
| Backend, integração | 104 | API + PostgreSQL real em contêiner, repositórios, migrações |
| Backend, ponta a ponta | 18 | Fluxo completo pela API, do login à operação finalizada, e cenários de falha |
| Backend, LPR (pasta `avaliacao`) | 19 | Infraestrutura da avaliação do reconhecimento; a avaliação com acervo real fica fora da execução padrão |
| **Total backend** | **1002** | |
| Frontend | 176 (18 arquivos) | Telas, componentes, cliente da API |

**Execução registrada em 2026-11-07:** todos os testes aprovados no backend e no frontend; ruff, mypy estrito, ESLint, Prettier, `tsc` estrito e build sem erro.

**Reexecução em 2026-11-08:** unitários e demais testes sem banco aprovados (882); frontend 176 aprovados; lint, tipagem e build sem erro. Os testes que sobem PostgreSQL em contêiner não rodaram por um problema de rede do Docker na máquina de desenvolvimento, sem relação com o código.

### 7.2 Cenários de validação do artigo

Os sete cenários previstos na metodologia do artigo estão cobertos pelos testes ponta a ponta com simuladores e pela validação pela interface:

| Cenário do artigo | Resultado com simuladores |
|---|---|
| Veículo com agendamento válido | Entrada autorizada, cancela aberta com confirmação, operação criada |
| Veículo sem agendamento | "Não autorizada" com o motivo; nenhuma pesagem criada; evento registrado |
| Falha no reconhecimento da placa | Confiança baixa, formato inválido, ambiguidade ou nenhum texto: não autoriza; evidência para o operador; liberação manual só pelo administrador |
| Leitura de peso pela comunicação serial | Peso estável aceito e registrado (15.000 kg na pesagem inicial da demonstração) |
| Falha de comunicação com a balança | Sem resposta, instável, quadro corrompido ou desconectada: nenhum peso aceito, falha sinalizada, operação parada em estado seguro |
| Acionamento de cancela | Comandos confirmados pelo sensor; sem confirmação, estado desconhecido e intervenção manual |
| Finalização com peso líquido | 45.000 − 15.000 = 30.000 kg na carga; descarga = inicial − final; sem movimentação dentro da tolerância |

Cenários de falha adicionais testados: transição inválida rejeitada, ação com versão desatualizada recusada, posição inconclusiva não avança, líquido negativo vai ao administrador, um caminhão por vez na balança, cancelamento com o caminhão na balança, mesma placa voltando após cancelamento, placa não reconhecida na volta.

### 7.3 Validação pela interface

Os 11 grupos de casos de uso (login, cadastros, agendamento, autoatendimento, operação, histórico, diagnóstico, falhas, intervenção, dispositivos, controle de acesso) foram percorridos pelo navegador, com o sistema completo no Docker Compose em modo simulado, sem falha funcional. As 19 capturas de tela estão em `docs/artigo/capturas/`, com a descrição e os requisitos de cada uma no `README.md` da pasta.

### 7.4 Execução e implantação

| Item | Medida (2026-11-07) |
|---|---|
| Imagem Docker do backend | 2,09 GB; build sem cache em 1 min 10 s (o tamanho vem do PyTorch e do EasyOCR) |
| Imagem Docker do frontend | 94,7 MB (Caddy servindo os arquivos estáticos); build em 27 s |
| Bundle do frontend | JS 366,8 kB (109,8 kB gzip); CSS 15,4 kB (4,1 kB gzip) |
| Subida completa | `docker compose up -d --build --wait`: banco, migração, backend e frontend com HTTPS |
| Testes ponta a ponta | 18 testes em cerca de 13 s |

### 7.5 Contribuição

Em relação aos trabalhos relacionados, que se concentram na identificação veicular, o protótipo integra o reconhecimento de placas a um fluxo operacional completo de pesagem, com:

- autorização por agendamento;
- controle de duas cancelas com confirmação;
- conferência de posição;
- critério de estabilidade do peso;
- máquina de estados com parada segura e intervenção rastreável;
- histórico auditável;
- uma tela de diagnóstico que explica cada decisão do algoritmo.

Tudo é reproduzível sem hardware.

---

## 8. Limitações e trabalhos futuros

| Limitação | Situação |
|---|---|
| Sem equipamento real | Nenhum teste com balança, cancela ou câmera físicas. Os simuladores validam a lógica do sistema, não o equipamento |
| Protocolo da balança | Transporte serial pronto; falta o protocolo do modelo de indicador (manual e quadros reais) |
| Cancela serial | Não implementada; depende do controlador e da ligação do sensor de status |
| Câmeras reais | Tipo, resolução e uso das câmeras da frente e de trás ainda não definidos; a demonstração usa câmera simulada com cena sintética |
| Posição pela câmera superior | Critério de análise da imagem não definido; fonte de posição simulada |
| Avaliação do OCR | Ainda **sem acervo de imagens reais** com gabarito; por isso não há taxa de acerto medida e o limiar de confiança (0,800 no exemplo) não foi calibrado. A infraestrutura de avaliação já existe e dá mais peso a falsos positivos de autorização do que a falsos negativos |
| Parâmetros de demonstração | Limites de peso, estabilidade, tempos-limite e limiar do OCR não foram calibrados |
| Desempenho | Latência do EasyOCR em CPU não medida com imagens reais |
| LGPD | Minimização aplicada (CPF mascarado, imagens só das decisões), mas a adequação formal está em aberto |
| Escala | Uma balança, um caminhão por vez sobre ela, várias operações abertas |

Trabalhos futuros: integrar o protocolo de um indicador real e a cancela serial; montar o acervo de imagens reais e medir o reconhecimento; definir as câmeras e o critério de posição; teste assistido e registrado com equipamento; avaliar GPU se a latência medida exigir.

---

## 9. Repositório e execução

- Código aberto em repositório público (`github.com/rafaelbzanon/easyscale`), com o arquivo `LICENSE` (texto da licença MIT; escolha final da licença ainda em aberto).
- Documentação: `README.md` (instalação, execução pelo Docker, ambiente de desenvolvimento, roteiro de demonstração), `specs/` (requisitos, glossário e as 29 especificações), `docs/decisoes/` (ADRs), `AMBIENTE.md` (referência técnica e comandos), `CONVENCOES.md` (organização do código).
- Execução em modo simulado: `cp .env.exemplo .env` e `docker compose up -d --build --wait`; interface em `https://localhost:8443`.

---

## 10. Sugestões de atualização por seção do artigo

| Seção do artigo | O que atualizar |
|---|---|
| Resumo / Abstract | Trocar "pretende-se utilizar" e "será realizada" por passado; citar PostgreSQL, React/TypeScript, Docker; resumir os resultados (§7) e as limitações (§8) |
| 1. Introdução | Manter os objetivos; incluir o agendamento por autoatendimento e a interface de diagnóstico, se forem tratados como contribuição |
| 2. Metodologia | Descrever o desenvolvimento orientado por especificação, os ADRs e a pirâmide de testes (§3, §7.1); trocar "HTML, Tailwind CSS e JavaScript" por "TypeScript, React e Tailwind CSS" |
| 3.2 / 3.3 | Pode citar as técnicas efetivamente usadas: tons de cinza, Canny, contornos e proporção; EasyOCR em CPU sem restrição de alfabeto |
| 3.6 Sistemas web | Acrescentar SSE para tempo real e sessão com cookie |
| 4. Produto | Atualizar com a arquitetura (§5), as duas cancelas, a conferência de posição, a máquina de estados, as telas (§6.6) e as capturas |
| Nova seção: Resultados | §7: testes, cenários do artigo, validação pela interface, figuras |
| Nova seção: Considerações finais | §7.5 e §8 |
| Referências | Acrescentar documentação de PostgreSQL, React, Tailwind, Docker e a Resolução CONTRAN nº 780/2019, se forem citados |
