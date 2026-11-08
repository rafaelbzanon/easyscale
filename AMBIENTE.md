# AMBIENTE.md — Referência técnica do ambiente e da arquitetura planejada

Sistema open-source de automação de pesagem rodoviária com LPR e visão computacional (TCC — IFRS, Veranópolis).

Complementa o `AGENTS.md` (regras de trabalho). **O estado real do repositório está na §0.2; onde houver a marca [PROPOSTA], o documento descreve intenção, não código existente.**

---

## 0. Como ler este documento

### 0.1 Legenda de status

| Marca | Significado |
|---|---|
| **[ARTIGO]** | Requisito/informação descrita no artigo do TCC. |
| **[DEFINIDO]** | Decisão já tomada pelo autor. Não alterar. |
| **[PROPOSTA]** | Sugestão técnica **não aprovada**. |
| **[PENDENTE]** | Decisão em aberto; exige aprovação do autor. |

### 0.2 Estado atual

O desenvolvimento **está em andamento** (atualizado em 2026-11-08). O andamento fica em `specs/tarefas-iniciais.md`, e o estado de cada spec e ADR em `specs/README.md`.

**Já existem:**

- `backend/` — regras de domínio, camada de dispositivos com simuladores, pipeline de LPR e testes automatizados, sem acesso a hardware real.
- Contratos de API aprovados e implementados: `specs/features/`, specs 007 a 013.
- Persistência (spec 014): `backend/src/pesagem/persistencia/` com a migração Alembic `0001`, que é o esquema vigente. O `docs/modelo-dados/schema.sql` virou histórico.
- `docs/decisoes/` — ADRs (ver `specs/README.md`).
- `specs/` — índice, glossário e lista de tarefas.

Desde 2026-11-07: API HTTP (specs 007 a 013), orquestração (spec 015), frontend (specs 016 a 024) e Docker (`backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml`; specs 025 a 027). As demais descrições de estrutura neste documento continuam **[PROPOSTA]** enquanto não forem criadas.

### 0.3 Divergências entre fontes (a resolver/registrar)

| Tema | Artigo | Definição do autor | Tratamento |
|---|---|---|---|
| Frontend | HTML + Tailwind CSS + JavaScript | TypeScript + Tailwind CSS | Prevalece **TypeScript + Tailwind**. Framework: React + Vite (ADR-0007). |
| Interface | Cadastros de veículos, motoristas, transportadoras e agendamentos; tela operacional | Acrescenta visualização de câmeras, ROIs e interpretações do algoritmo (diagnóstico) | Ambos entram no escopo; o segundo **não consta no artigo** e foi formalizado no RF-022 e no RF-023. |
| Agendamento | O artigo lista "criação de agendamentos" como função do sistema | O agendamento é **manual**, por usuário com permissão ou pelo motorista no autoatendimento (RF-033), e não será automatizado | O sistema oferece o meio de criar/gerir agendamentos; **nada no agendamento é automatizado**. A automação cobre as etapas seguintes. |
| Persistência de "documentos" | O artigo não detalha documentos | O autor lista "documentos" entre as necessidades | O significado de "documentos" é **[PENDENTE]** (Q-03). |
| Orientação de posicionamento na balança | Não detalhada no artigo | Faz parte do fluxo esperado | Fora do protótipo (Q-05, 2026-11-04). |

### 0.4 Decisões do autor sobre o `schema.sql` (C-002, 2026-10-29)

| Item C-002 | Decisão | Consequência |
|---|---|---|
| 1 — status do esquema / D-01 | **PostgreSQL** é o banco **[DEFINIDO]** (ADR-0001, Aceita). O `docs/modelo-dados/schema.sql` é **referência [PROPOSTA]**. | Specs de domínio mandam; o esquema é ajustado a elas na spec `persistencia` (BE-502). |
| 3 — pesagem por agendamento | Após uma pesagem **CANCELADA**, o mesmo agendamento **pode** ter nova pesagem **[DEFINIDO]**. A pesagem cancelada permanece no histórico. | O `UNIQUE (agendamento_id)` atual deve virar unicidade apenas entre pesagens não canceladas (BE-502). Regras de quando cancelar: BE-201. |
| 7 — configuração dos equipamentos | O **banco cadastra** os equipamentos (descrição, vínculo com ponto de controle); **variáveis de ambiente** definem modo (`SIMULADO` padrão) e parâmetros de comunicação **[DEFINIDO]**. | `simulada`, `porta_serial`, `baud_rate`, `paridade`, `data_bits`, `stop_bits` (e `endereco_ip`, ver item 8) saem ou deixam de ser fonte de verdade no esquema (BE-301/BE-502). Hoje `simulada DEFAULT FALSE` equivale a "real por padrão" e **não** deve ser usado. |
| 2, 4, 5, 6, 9, 14, 16 | Tratados nas specs e no ADR: item 2 na spec 002; item 4 na spec 006; item 5 na spec 004; item 6 nas specs 003 e 005; item 9 no ADR-0004; item 14 na spec 005; item 16 na RN-006. | O `schema.sql` só é ajustado na BE-502. |
| 8, 10, 12, 13, 15, 17 | Sem decisão; recomendações do agente registradas como **[PROPOSTA]** em `specs/tarefas-iniciais.md` (C-002). O item 8 depende da Q-01. | Tratados na BE-502. |
| 18 — nota fiscal (arquivo legado `nota_fiscal.py`) | **[PENDENTE]**, ligado a Q-03. | Fora do escopo até decisão. |

---

## 1. Objetivo e escopo

### 1.1 Objetivo **[ARTIGO]**

Desenvolver um **protótipo funcional** de sistema web que automatize etapas do processo de pesagem rodoviária de caminhões, integrando: reconhecimento automático de placas, validação por agendamento, leitura de peso da balança, controle de cancelas, registro de pesagens e cálculo do peso líquido — com validação em ambiente controlado (imagens de placas e simulação da comunicação com balança/cancelas quando não houver equipamento físico).

Metas declaradas no artigo: reduzir intervenção humana, aumentar rastreabilidade, segurança e eficiência.

### 1.2 Dentro do escopo

- Cadastros: veículos, motoristas, transportadoras **[ARTIGO]**; produtos e tipos de veículo (decisão do autor, Q-14).
- Agendamento **manual** de operações (tipo de operação, produto, data prevista, etc.) **[ARTIGO]**, com faixas de horário (RF-028, RF-029) e autoatendimento do motorista (RF-033) — o ato de agendar não é automatizado.
- Identificação automática do caminhão por LPR (OpenCV + EasyOCR) **[ARTIGO]**.
- Validação da placa contra agendamento ativo **[ARTIGO]**.
- Controle de cancelas (prompt do autor). A orientação de posicionamento na balança saiu do protótipo (Q-05, 2026-11-04).
- Leitura do peso e registro das pesagens necessárias; cálculo do peso líquido; histórico para consulta e auditoria **[ARTIGO]**.
- Tela operacional (placa, situação do agendamento, peso, etapa atual, comandos das cancelas) **[ARTIGO]**.
- Interface de administração/diagnóstico: imagens das câmeras, ROIs, interpretações do algoritmo (prompt do autor).
- Simulação da balança e das cancelas **[ARTIGO]**.
- Repositório público, com documentação básica de instalação/configuração/execução **[ARTIGO]**; licença **[PENDENTE]**.

### 1.3 Fora do escopo (salvo decisão em contrário)

- Automatizar a criação de agendamentos.
- Qualquer funcionalidade não ligada ao artigo ou a especificação aprovada.
- Integrações com ERPs, emissão de documentos fiscais, cobrança — **não mencionadas no artigo** (confirmar com autor, Q-03).

---

## 2. Fluxo operacional esperado

Base: artigo (seções 3.5 e 4) + decisões do autor. Passos em **itálico** são refinamentos já definidos em spec (specs 002, 006 e 008). A coordenação entre os passos é da BE-601.

1. **Agendamento (manual).** Usuário com permissão, ou o motorista no autoatendimento pela rede do pátio (RF-033, ADR-0004), registra a operação: veículo, motorista, transportadora, tipo (carga/descarga), produto, data prevista **[ARTIGO]**.
2. **Chegada e identificação.** Câmera captura a placa; o módulo de visão computacional lê a placa **[ARTIGO]**.
3. **Validação.** O sistema compara a placa com os cadastros e verifica agendamento válido/ativo **[ARTIGO]**. *Se inconclusivo ou sem agendamento: não autorizar; registrar; encaminhar ao operador.*
4. **Autorização de entrada e cancela.** Se autorizado, a cancela é liberada e o caminhão segue para a balança **[ARTIGO]**.
5. **Posicionamento e pesagem inicial.** O caminhão se posiciona na balança, sem orientação do sistema (Q-05); o sistema identifica a posição pela câmera superior, podendo combinar todas as câmeras (Q-17) e lê o peso via RS232 e o registra como pesagem inicial **[ARTIGO]**. *Só aceitar leitura válida e estável.*
6. **Carga ou descarga.** O caminhão sai da balança pela cancela de saída (spec 006). Operação física fora do sistema; o sistema acompanha a etapa atual **[ARTIGO]**.
7. **Pesagem final.** O caminhão retorna à balança pela cancela de entrada, com nova leitura da placa (RN-018); o peso é registrado como pesagem final **[ARTIGO]**.
8. **Cálculo e histórico.** O sistema calcula o peso líquido e armazena a operação e seus eventos para consulta/auditoria **[ARTIGO]**. *Saída do veículo pela cancela de saída, depois da pesagem aceita e registrada (RN-012).*

> Observação **[DEFINIDO]**: o cálculo usa só as pesagens medidas, sem mapear inicial e final para tara e peso bruto. CARGA: final − inicial; DESCARGA: inicial − final, com tolerância configurável (Q-02, RN-006). A operação tem duas pesagens (spec 006).

### 2.1 Estados da operação **[DEFINIDO]**

A lista final tem 20 situações e está na spec 006 §5.1 (Implementada). Vai de `AGUARDANDO_BALANCA_INICIAL` a `FINALIZADA` ou `CANCELADA`, com `AGUARDANDO_INTERVENCAO` para as exceções. Falhas de identificação não são situações: a operação só nasce depois da autorização, e essas falhas viram eventos (spec 006, P-1).

Requisito do `AGENTS.md`: transições inválidas são rejeitadas e registradas; todo estado de falha leva a um comportamento seguro (ver seção 11.4).

---

## 3. Tecnologias e responsabilidades

### 3.1 Definidas **[DEFINIDO]**

| Tecnologia | Responsabilidade neste projeto |
|---|---|
| **Python + FastAPI** | Backend: API, regras de negócio, orquestração entre interface, banco, visão computacional e comunicação serial **[ARTIGO]**. |
| **TypeScript + Tailwind CSS** | Frontend: cadastros, agendamentos, tela operacional, histórico, monitoramento e diagnóstico. |
| **Docker** | Infraestrutura de desenvolvimento e execução (ver seção 7). |
| **OpenCV** | Captura, pré-processamento e localização da região da placa; geração/desenho de ROIs para diagnóstico **[ARTIGO]**. |
| **EasyOCR** | Leitura dos caracteres da placa (tecnologia inicialmente prevista) **[ARTIGO]**. |
| **PySerial** | Comunicação RS232 com a balança (leitura de peso) e com dispositivos de controle das cancelas (comandos) **[ARTIGO]**. |

### 3.2 Em aberto **[PENDENTE]**

Protocolos detalhados dos equipamentos, execução da captura de câmera (restante da D-05), licença do repositório (D-12).

Já decididos: banco (ADR-0001), arquitetura (ADR-0002), ferramentas do backend (ADR-0003), autenticação (ADR-0004), tempo real (ADR-0005), ORM e migrações (ADR-0006), framework do frontend (ADR-0007) e ferramentas do frontend (ADR-0008). A situação de cada decisão está na §15.

As versões das bibliotecas do backend estão fixadas em `backend/pyproject.toml`, com a justificativa. Versões só devem ser fixadas com justificativa e registradas (ADR ou arquivo de dependências).

---

## 4. Arquitetura lógica proposta **[PROPOSTA]**

O artigo prevê organização **modular**: interface web, API backend, módulo de LPR, módulo de comunicação serial RS232 e banco relacional, para permitir desenvolvimento e validação individual dos componentes **[ARTIGO]**. O desenho abaixo é uma proposta de como organizar isso, não uma arquitetura aprovada.

```
┌─────────────────────┐        HTTP / eventos em tempo real (SSE, ADR-0005)
│  Frontend (TS+TW)   │◄──────────────────────────────────────────┐
│  operação • admin   │                                           │
└─────────┬───────────┘                                           │
          │                                                       │
          ▼                                                       │
┌──────────────────────────────────────────────────────────────────┴───┐
│                       Backend (FastAPI)                              │
│  ┌────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │   API      │  │ Regras de negócio│  │ Orquestração da operação │  │
│  │ (rotas)    │─►│ e validação      │◄─│ (máquina de estados)     │  │
│  └────────────┘  └────────┬─────────┘  └───────┬──────────┬───────┘  │
│                           │                    │          │          │
│                  ┌────────▼────────┐  ┌────────▼───┐  ┌───▼────────┐ │
│                  │  Persistência   │  │  Visão     │  │ Dispositivos│ │
│                  │  (repositórios) │  │ (LPR)      │  │ (serial)    │ │
│                  └────────┬────────┘  └────┬───────┘  └───┬────────┘ │
└───────────────────────────┼────────────────┼──────────────┼──────────┘
                            ▼                ▼              ▼
                    ┌──────────────┐   ┌───────────┐  ┌──────────────┐
                    │ PostgreSQL   │   │ Câmeras / │  │ Balança e    │
                    │ (ADR-0001)   │   │ imagens   │  │ cancelas     │
                    └──────────────┘   │ (ou fonte │  │ (RS232 ou    │
                                       │ simulada) │  │ simulador)   │
                                       └───────────┘  └──────────────┘
```

### 4.1 Responsabilidades por componente

- **Frontend**: apresentar estado e evidências; coletar ações do operador/administrador. **Não contém lógica de decisão de segurança** — decisões de autorização e acionamento são sempre do backend.
- **API**: borda HTTP; validação de entrada; autenticação/autorização (ADR-0004); sem lógica de negócio pesada.
- **Regras de negócio / orquestração**: decide se um veículo é autorizado, qual é a etapa atual, quando aceitar um peso, quando emitir comando à cancela; mantém a máquina de estados da operação; independe de HTTP, serial, câmera e banco para ser testável.
- **Persistência**: armazenar e recuperar cadastros, agendamentos, pesagens, eventos e histórico (ver seção 12). Isolada atrás de uma fronteira clara (SQLAlchemy 2 Core + Alembic, ADR-0006; spec 014).
- **Visão computacional (LPR)**: dada uma fonte de imagem, produzir resultado estruturado (placa candidata, confiança, ROI, imagem de evidência). Não decide autorização; apenas informa.
- **Dispositivos (serial)**: expor operações abstratas (ler peso, comandar cancela, consultar estado quando o equipamento permitir) com implementação **real (PySerial)** e **simulada**, selecionável por configuração.

### 4.2 Princípios arquiteturais **[PROPOSTA]**

1. **Fronteiras explícitas** entre domínio, I/O e infraestrutura.
2. **Fontes substituíveis**: câmera real, arquivo de vídeo e pasta de imagens são intercambiáveis para o módulo de LPR; balança/cancela real e simulada são intercambiáveis para o módulo de dispositivos.
3. **Um único dono por recurso físico**: apenas **um** componente/processo abre cada porta serial (evitar acessos concorrentes).
4. **Operações bloqueantes isoladas**: OCR (pesado), leitura serial e captura de vídeo não devem travar o atendimento de requisições; dispositivos e OCR já têm estratégia, e a captura de câmera é **[PENDENTE]** (D-05, §15).
5. **Fail-safe por padrão** (ver `AGENTS.md`, seção 7).
6. **Sem abstração além do necessário**: as fronteiras acima são justificadas por artigo + segurança + testabilidade; outras exigem justificativa.

### 4.3 Questões de arquitetura em aberto

- Monólito modular único ou serviços separados: **[DEFINIDO]** monólito modular — [ADR-0002](docs/decisoes/ADR-0002-monolito-modular.md) (Aceita, 2026-10-29). Portas seriais abertas por um único componente em um único processo; evolução para processo de trabalho separado permitida via D-05 sem novo ADR.
- Como o frontend recebe imagens/ROIs/eventos em tempo real: SSE para eventos e imagens sob demanda (ADR-0005, D-06).

---

## 5. Organização de diretórios **[PROPOSTA]**

> Visão inicial, anterior ao código. A organização vigente é a do `CONVENCOES.md`. Hoje existem `backend/`, `frontend/`, `docs/` e `specs/`; os arquivos Docker ficam na raiz e em cada pasta (`compose.yaml`, `Caddyfile`, `backend/Dockerfile`, `frontend/Dockerfile`).

```
/
├── AGENTS.md
├── AMBIENTE.md
├── README.md                  # hoje só apresenta o projeto; instalação e execução na INT-003 [ARTIGO: doc básica]
├── specs/                     # especificações (ver AGENTS.md §5.1)
├── docs/
│   └── decisoes/              # ADRs
├── backend/                   # Python + FastAPI
│   └── ...                    # módulos: api, domínio/regras, visão (LPR), dispositivos, persistência
├── frontend/                  # TypeScript + Tailwind, React + Vite (ADR-0007)
├── simuladores/               # (opcional) simuladores de balança/cancela e fontes de imagem
├── dados-teste/               # só o README: acervo e gabarito ficam fora do repositório (spec 005 §12.1)
└── (raiz)                     # compose.yaml e Caddyfile (spec 027)
```

Já decididos no `CONVENCOES.md` §2: repositório único e local de simuladores e dados de teste. O acervo real fica fora do repositório (spec 005 §12.1). Falta: autorização e restrições de publicação do acervo (Q-09).

---

## 6. Ambiente de desenvolvimento

**[PROPOSTA]** — a validar:

- Desenvolvimento e execução via **Docker** **[DEFINIDO]**, preferindo orquestração por Compose para subir backend, frontend e banco juntos, com um comando documentado no README (comandos concretos de Docker na §6.1).
- O ambiente deve ser **reproduzível** (objetivo open-source **[ARTIGO]**): um terceiro deve conseguir clonar e executar o protótipo em modo **simulado** sem hardware.
- **Modo simulado como padrão seguro**; hardware real só com configuração explícita.
- Necessidades já previsíveis:
  - Runtime Python e dependências de visão (OpenCV, EasyOCR e o framework de aprendizado profundo que o EasyOCR requer). Imagens Docker com essas dependências tendem a ser **grandes**; o tempo de build e o tamanho devem ser considerados.
  - EasyOCR faz download de modelos de reconhecimento; prever **volume/cache persistente** para os modelos; na operação, nada é baixado (D-08).
  - Node/TypeScript para o frontend, com Vite como ferramenta de build (ADR-0007).
  - Uso de **GPU**: não definido; assumir **CPU** até que se decida o contrário **[PENDENTE]** (D-09).
  - Acesso a portas seriais reais e a câmeras (ver seção 7.3).

### 6.1 Comandos de desenvolvimento

**Backend** — executados em 2026-10-29 (BE-102, Python 3.14.7), a partir de `backend/`. Ferramentas: ADR-0003; esqueleto: spec 001.

```sh
python3 -m venv .venv                 # Python >= 3.12
.venv/bin/pip install --group dev     # requer pip >= 25.1 dentro do venv
# Dependências de execução (o pacote não é instalado, spec 001); sem elas,
# os testes de API, persistência e serial falham na coleta. Verificado em 2026-11-08.
.venv/bin/python -c "import tomllib; print(*tomllib.load(open('pyproject.toml','rb'))['project']['dependencies'], sep='\n')" | .venv/bin/pip install -r /dev/stdin
.venv/bin/pytest                      # testes
.venv/bin/pytest --cov                # testes + cobertura (sem meta mínima)
.venv/bin/ruff check                  # lint
.venv/bin/ruff format --check         # formatação
.venv/bin/mypy                        # tipagem (modo estrito)
```

**LPR** — executados em 2026-10-30 (BE-402, spec 005), a partir de `backend/`. Dependências aprovadas pelo autor em 2026-10-30; `torch`/`torchvision` só para CPU (D-09) vêm do índice do PyTorch e são instalados **antes** do grupo.

```sh
.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 torchvision==0.29.1
.venv/bin/pip install --group lpr
# Download explícito dos modelos (P-10); a operação nunca baixa nada.
# Não executado nesta sessão: os testes usaram modelos que já existiam.
.venv/bin/python -m pesagem.lpr.baixar_modelos <pasta-modelos> <idioma>...
# Avaliação com o acervo (fora do repositório); variáveis no topo de
# tests/avaliacao/test_avaliacao_lpr.py. Sem elas, falha com mensagem clara.
.venv/bin/pytest -m avaliacao -s
```

`pyserial==3.5` está nas dependências de execução desde 2026-11-07 (spec 029): quem já tem o venv precisa reinstalar.

**Persistência** — executados em 2026-11-07 (BE-503, spec 014), a partir de `backend/`:

```sh
PYTHONPATH=src .venv/bin/alembic upgrade head   # com as PESAGEM_BANCO_*; o pacote não é instalado (spec 001)
.venv/bin/pytest tests/integracao               # sobe um contêiner postgres:18.6-alpine (precisa de Docker)
```

**API** — executados em 2026-11-07 (BE-706), a partir de `backend/`, com as `PESAGEM_*` exportadas. Obrigatórias na partida: `PESAGEM_BANCO_HOST`, `_PORTA`, `_NOME`, `_USUARIO`, `_SENHA`; `PESAGEM_PATIO_FUSO`; `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS`, `_SESSAO_TEMPO_SEM_USO_S`, `_LOGIN_TENTATIVAS_MAXIMAS`, `_LOGIN_BLOQUEIO_S`; `PESAGEM_GERAL_TAMANHO_PAGINA_PADRAO`, `_TAMANHO_PAGINA_MAXIMO`. Opcionais juntas (sem elas, o autoatendimento fica desligado): `PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES`, `_TENTATIVAS_MAXIMAS`, `_BLOQUEIO_S`. Desde a BE-703, também as de balança, pesagem, LPR, câmera, tempo real e operação listadas na §8. A migração `0004` semeia o ponto de controle único; sem ele a partida falha.

```sh
PYTHONPATH=src .venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/python -m pesagem.api.criar_administrador   # primeiro administrador; pede nome, login, senha e confirmação, sem eco
PYTHONPATH=src .venv/bin/uvicorn --factory pesagem.main:criar_aplicacao --host 127.0.0.1 --port 8000   # um processo só, sem --workers (ADR-0002)
```

Sem uma variável obrigatória, a partida falha com `ErroConfiguracao: variável obrigatória ausente: <NOME>`.

**Frontend** — executados em 2026-11-07 (FE-102, spec 016), a partir de `frontend/`, com Node 22.22:

```sh
npm ci                                   # instala pelo package-lock.json (ADR-0008)
PESAGEM_GERAL_URL_BACKEND=http://127.0.0.1:8000 npm run dev   # proxy de /api; sem a variável, falha com mensagem clara
npm run build                            # gera dist/
npm test                                 # Vitest
npm run lint                             # ESLint
npm run format                           # Prettier (verificação)
npm run typecheck                        # tsc estrito
```

Proxy do Vite e cookie `Secure` em `http://localhost` verificados contra o backend real em 2026-11-07 (FE-308); SSE pelo proxy do Vite verificado contra a rota real em 2026-11-07 (FE-303), inclusive queda e volta do backend.

**Ponta a ponta** — executado em 2026-11-07 (INT-002, spec 028), a partir de `backend/`:

```sh
.venv/bin/pytest tests/ponta_a_ponta   # 18 testes, ~13 s; precisa de Docker (sobe postgres:18.6-alpine)
```

Verificação final em 2026-11-07 (Maestro): backend `pytest` 972 aprovados e 1 desmarcado (avaliação do LPR), `ruff` e `mypy` limpos; frontend `npm test` 174 aprovados, lint, typecheck, format e build sem erro. Validação pelo navegador (Playwright, compose isolado) dos 11 grupos de casos de uso, sem falha funcional.

Verificação em 2026-11-08 (Python 3.14.9, Node 26.13.0): backend com 1002 testes coletados, 882 aprovados e 120 com erro, todos de integração e ponta a ponta, porque o Docker do host não conseguiu criar a rede do contêiner do banco (kernel em execução sem os módulos instalados; problema da máquina, não do código); `ruff` e `mypy` limpos. Frontend `npm test` 176 aprovados, lint, typecheck, format e build sem erro.

**Docker do backend** — executados em 2026-11-07 (BE-801, spec 025), a partir de `backend/`:

```sh
docker build -t pesagem-backend .                                   # 1m10s sem cache; imagem de 2,09 GB
docker run --rm --env-file <arquivo> pesagem-backend alembic upgrade head   # migração é comando separado
docker run -d --env-file <arquivo> -p 127.0.0.1:8000:8000 pesagem-backend
docker run --rm -v pesagem-modelos-ocr:/modelos-ocr pesagem-backend python -m pesagem.lpr.baixar_modelos /modelos-ocr en
```

**Docker do frontend** — executados em 2026-11-07 (FE-401, spec 026), a partir de `frontend/`:

```sh
docker build -t pesagem-frontend .      # 27 s; imagem de 94,7 MB (Caddy 2.11.6 servindo o dist/)
docker run -d -e PESAGEM_GERAL_URL_BACKEND=http://<backend>:8000 -p 127.0.0.1:8080:8080 pesagem-frontend
```

**Compose** — executados em 2026-11-07 (INT-001, spec 027), a partir da raiz, Docker 29.9.0 e Compose 5.6.0:

```sh
cp .env.exemplo .env                  # troque PESAGEM_BANCO_SENHA; modo SIMULADO
docker compose up -d --build --wait   # db, migracao (única), backend, frontend (HTTPS em https://localhost:8443)
docker compose run --rm migracao python -m pesagem.api.criar_administrador   # primeiro administrador; precisa de terminal
docker compose cp frontend:/data/caddy/pki/authorities/local/root.crt ./pesagem-ca.crt   # CA interna do Caddy
curl --cacert ./pesagem-ca.crt https://localhost:8443/api/sessoes/atual   # 401 sem cookie = vivo
docker compose --profile dev up -d db-dev      # banco em 127.0.0.1:5432 para backend e npm run dev na máquina
docker compose --profile teste up -d db-teste  # banco descartável em 127.0.0.1:5433
docker compose down                   # mantém os volumes; -v apaga banco, modelos e certificados
```

Só o `frontend` publica porta (127.0.0.1:8443); banco e backend ficam na rede do compose. O perfil `hardware-real` está bloqueado (modo REAL indisponível, Q-01). Os valores de balança, LPR e tempos do `.env.exemplo` são de demonstração, não calibrados (spec 027 P-1).

---

## 7. Containerização e execução com Docker

### 7.1 Estratégia **[PROPOSTA]**

| Serviço | Papel | Observação |
|---|---|---|
| `backend` | FastAPI + módulos de LPR e dispositivos | Pode concentrar LPR e serial inicialmente (monólito modular). Separar só com justificativa. |
| `frontend` | Interface TypeScript + Tailwind | Em desenvolvimento, servidor de desenvolvimento; em execução, Caddy com HTTPS (CA interna por padrão) servindo o `dist/` e repassando `/api` ao backend (specs 026 e 027). |
| `db` | PostgreSQL (ADR-0001) | Acesso e migrações: ADR-0006. Serviço `migracao`: execução única de `alembic upgrade head` antes do backend (spec 027 §4.1). |
| (opcional) `simulador-*` | Balança/cancela/câmera simulados | Útil para demonstração e testes. |

- Perfis/ativações distintos para **desenvolvimento**, **testes** e **execução com hardware real** (ex.: o modo real só com dispositivos mapeados e variáveis explícitas).
- Dados do banco e modelos do EasyOCR em **volumes persistentes**.
- Configuração exclusivamente por variáveis de ambiente (seção 8); segredos fora do repositório.

### 7.2 Considerações sobre imagens e build **[PROPOSTA]**

- Evitar incluir modelos/dados de teste grandes na imagem; usar volumes.
- Tamanho e tempo medidos do backend: spec 025 §6.
- Perfis: (nenhum) = execução simulada; `dev` = `db-dev`; `teste` = `db-teste`; `hardware-real` = bloqueado (spec 027 §4.5). Execução: spec 027.

### 7.3 Acesso a dispositivos a partir de contêiner — **risco**

- **Portas seriais**: o contêiner precisa de acesso ao dispositivo do host (mapeamento de dispositivo). Em Linux isso é direto; em Docker Desktop (Windows/macOS) o acesso a portas seriais/USB **costuma exigir soluções adicionais** e pode ser limitado. **A verificar** conforme o SO do ambiente real (Q-07). Impacta a decisão de rodar o backend em contêiner no equipamento que ficará ligado à balança.
- **Câmeras**: câmeras de rede (por ex., via protocolo de streaming de rede) funcionam sem mapeamento de dispositivo; câmeras USB locais exigem mapeamento. O tipo de câmera é **[PENDENTE]** (Q-06).
- Em ambos os casos, os testes automatizados **não** devem depender desses mapeamentos (usar simulação).

---

## 8. Configuração por variáveis de ambiente

**[PROPOSTA]** — os **nomes** abaixo são ilustrativos, não um contrato. Definir de fato na spec correspondente. Não colocar segredos/valores reais no repositório; fornecer apenas um arquivo de exemplo quando houver.

| Grupo | Exemplos de configuração necessária | Observação |
|---|---|---|
| Geral | ambiente (dev/teste/execução), nível de log; `PESAGEM_GERAL_TAMANHO_PAGINA_PADRAO` e `_TAMANHO_PAGINA_MAXIMO` (spec 007 §3.3); `PESAGEM_HTTPS_HOST`, `_PORTA`, `_ENDERECO`, `_TLS` e `PESAGEM_IP_PROXY` (lidas só pelo `compose.yaml` e pelo `Caddyfile`, spec 027 §4.3); `PESAGEM_BANCO_PORTA_DEV` (porta do perfil `dev`); `PESAGEM_GERAL_URL_BACKEND` (destino do proxy de `/api` no `npm run dev` e na imagem do frontend, sem valor padrão; specs 016 e 026) | Em desenvolvimento, a origem do Vite precisa estar em `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS` (spec 012 §6.9). |
| Pátio | `PESAGEM_PATIO_FUSO`: fuso que define o "hoje" e os horários das faixas | Obrigatório, sem valor padrão (spec 008 §6.1). |
| Banco | parâmetros de conexão | PostgreSQL (ADR-0001). |
| Câmeras | origem da imagem (câmera de rede, dispositivo local, arquivo de vídeo, pasta de imagens), taxa de captura | Fonte substituível para testes.  Em uso (BE-703): `PESAGEM_CAMERA_MODO` (ausente = `SIMULADO`; `REAL` impede a partida, Q-06), `_INTERVALO_ANALISE_MS`, `_IDADE_MAXIMA_IMAGEM_MS`. |
| LPR | limiar de confiança, idiomas/modelos do OCR, parâmetros de pré-processamento, local de cache dos modelos | Valores de limiar **[PENDENTE]**: definir empiricamente com dados de teste.  Em uso: `PESAGEM_LPR_LIMIAR_CONFIANCA`. Pasta e idiomas dos modelos só quando houver câmera real (proposta do Keel: `PESAGEM_LPR_PASTA_MODELOS`, `PESAGEM_LPR_IDIOMAS`). |
| Balança | modo (real/simulado), porta, parâmetros seriais (taxa, bits, paridade, parada), timeout, parâmetros de estabilidade | Valores e protocolo dependem do equipamento (**[PENDENTE]**).  Em uso (BE-703): `PESAGEM_BALANCA_MODO` (ausente = `SIMULADO`; `REAL` impede a partida enquanto não houver protocolo registrado, spec 029), `_PESO_MINIMO_KG`, `_PESO_MAXIMO_KG`, `_QUANTIDADE_LEITURAS_ESTAVEIS`, `_VARIACAO_MAXIMA_KG`, `_JANELA_ESTABILIDADE_MS`, `_INTERVALO_LEITURA_MS`; `PESAGEM_PESAGEM_TOLERANCIA_MOVIMENTACAO_KG` (padrão 20, valor do autor, RN-006); só com `PESAGEM_BALANCA_MODO=REAL` (spec 029 §6.3, sem valor padrão): `PESAGEM_BALANCA_PROTOCOLO` (nome no registro de protocolos, hoje vazio), `_PORTA`, `_BAUD_RATE` (valores de `serial.Serial.BAUDRATES`), `_PARIDADE` (`N`, `E`, `O`, `M`, `S`), `_DATA_BITS` (5 a 8), `_STOP_BITS` (`1`, `1.5`, `2`), `_TIMEOUT_MS`, `_INTERVALO_TENTATIVA_MS`. |
| Cancelas | modo (real/simulado), porta/canal, timeout, política de retentativa | Idem.  Em uso: `PESAGEM_CANCELA_MODO` (ausente = `SIMULADO`; `REAL` impede a partida). |
| Segurança | `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS`, `_SESSAO_TEMPO_SEM_USO_S`, `_LOGIN_TENTATIVAS_MAXIMAS`, `_LOGIN_BLOQUEIO_S`, `_AUTOATENDIMENTO_REDES` (sem configuração, a rota fica desligada), `_AUTOATENDIMENTO_TENTATIVAS_MAXIMAS`, `_AUTOATENDIMENTO_BLOQUEIO_S` | ADR-0004; definidas nas specs 012 e 013. |
| Tempo real | `PESAGEM_TEMPO_REAL_HEARTBEAT_MS`, `_LIMITE_SEM_HEARTBEAT_MS`, `_INTERVALO_PESO_MS`, `_INTERVALO_IMAGEM_MS`; análise: `PESAGEM_CAMERA_INTERVALO_ANALISE_MS`, `PESAGEM_CAMERA_IDADE_MAXIMA_IMAGEM_MS`; balança: `PESAGEM_BALANCA_INTERVALO_LEITURA_MS` | ADR-0005; definidas nas specs 009, 011 e 015, sem valor padrão. |
| Operação | `PESAGEM_OPERACAO_TEMPO_LIMITE_POSICIONAMENTO_MS`, `_TEMPO_LIMITE_PESAGEM_MS`, `_TEMPO_LIMITE_SAIDA_BALANCA_MS` | Tempos-limite das etapas (spec 015), sem valor padrão. |
| Retenção/privacidade | — | Sem prazo: as imagens das decisões ficam até o administrador pedir a exclusão (RN-022). Adequação à LGPD **[PENDENTE]** (Q-08). |

Regras: padrão **simulado/seguro**; valores obrigatórios ausentes devem causar falha de inicialização clara, não um valor "chutado".

**[DEFINIDO]** (C-002, item 7): modo e parâmetros de comunicação de balança e cancelas vêm **destas variáveis**, não do banco; o banco apenas cadastra os equipamentos.

---

## 9. Câmeras, OpenCV e EasyOCR

### 9.1 Pipeline previsto **[ARTIGO]**

Aquisição/carregamento da imagem → pré-processamento → localização da região da placa → leitura dos caracteres (OCR) → comparação da placa reconhecida com os dados cadastrados. Etapas gerais de ALPR (aquisição, extração da placa, segmentação, reconhecimento) conforme literatura citada no artigo.

### 9.2 Integração

A fonte por pasta de imagens, o resultado estruturado, a normalização e a seleção da placa já estão implementados (specs 003 e 005). Câmeras reais e a calibração com o acervo ainda faltam.

- **Fonte de imagem abstrata**: câmera (rede/USB), vídeo gravado ou pasta de imagens, com a mesma interface para o restante do sistema.
- **Resultado estruturado** do LPR (spec 005): texto bruto lido, placa normalizada, confiança, ROI/coordenadas, imagem de evidência, marca de tempo, câmera de origem.
- **Normalização e validação** da placa lida antes de consultar agendamentos: padrões de placa do Brasil (formato antigo e formato Mercosul) e correções de confusões típicas de OCR (ex.: O/0, I/1, B/8) devem ser tratados **com regras explícitas e testadas**, sem "adivinhar" silenciosamente. Só placas brasileiras, formato antigo e Mercosul (Q-10, RN-017); as correções só valem para leituras de câmera, nunca para placa digitada (spec 007 §6.1).
- **Critério de aceitação**: confiança mínima + validade de formato + correspondência única com agendamento. Qualquer falha → **não autorizar** (fail-safe). A seleção da placa é conservadora (spec 005); leituras repetidas entre imagens ficam para a BE-601, sempre com a imagem mais recente (RF-034, ADR-0005).
- **Desempenho**: OCR é custoso; o ciclo de captura/inferência não deve bloquear a API (D-05). Em CPU, medir latência real antes de prometer tempo de resposta (RNF a definir).
- **Fatores de qualidade** citados na literatura do artigo: iluminação, resolução, ângulo, distância, sujeira, reflexos, variação de modelos de placa. Devem orientar o conjunto de testes e o posicionamento das câmeras (Q-06).
- A literatura do artigo descreve o EasyOCR como OCR baseado em aprendizado profundo; **EasyOCR é a tecnologia "inicialmente prevista"**: a arquitetura deve manter o OCR atrás de uma fronteira para permitir avaliar alternativas sem reescrever o sistema, **sem** com isso criar abstração especulativa além dessa fronteira.

### 9.3 Quantidade e posição das câmeras (parcial)

O sistema terá câmeras na frente, atrás e superior; a superior identifica a posição do caminhão, podendo combinar todas as câmeras (Q-06 e Q-17, 2026-11-04). Não definidos: tipo, resolução e uso das câmeras da frente e de trás. Impacta o desenho da tela de monitoramento e do LPR (Q-06).

---

## 10. Interface: requisitos para monitoramento e administração

Requisitos: RF-020 a RF-024, RF-033. Itens com **[ARTIGO]** estão no artigo; os demais são decisões do autor. As telas têm spec própria na trilha D.

### 10.1 Telas/áreas funcionais

1. **Cadastros e agendamentos** (veículos, motoristas, transportadoras, produtos, tipos de veículo, faixas de horário e agendamentos; criação **manual**) **[ARTIGO]** + decisões do autor. Inclui o autoatendimento do motorista, sem login (RF-033).
2. **Tela operacional em tempo real**: chegada do caminhão, placa reconhecida, autorização de entrada, situação do agendamento, peso lido, etapa atual, comandos das cancelas **[ARTIGO]**.
3. **Histórico e auditoria**: consulta de operações, pesagens, peso líquido e eventos **[ARTIGO]**.
4. **Diagnóstico/administração da visão computacional**:
   - Visualização das imagens das câmeras, atualizadas periodicamente (ADR-0005).
   - Visualização das **ROIs** usadas pelo algoritmo, sobrepostas à imagem.
   - Visualização das **interpretações do algoritmo**: texto lido, placa normalizada, confiança, decisão resultante e motivo de rejeição/aceitação.
   - Consulta ao histórico de reconhecimentos, incluindo leituras inconclusivas.
5. **Estado dos dispositivos**: situação da comunicação com balança e cancelas (conectado/erro/simulado), última leitura de peso, último comando e resultado.
6. **Intervenção manual** em casos de exceção (ação, quem pode executar, registro obrigatório): permissões em RN-016, RN-020, spec 006 §9 e ADR-0004 §4.3. Toda intervenção deve ser rastreável.
7. **Indicação visível do modo** (real vs. simulado) para evitar confusão operacional.

### 10.2 Requisitos transversais **[PROPOSTA]**

- Atualização com baixa latência da tela operacional (SSE, ADR-0005).
- Estados de falha claros e inequívocos para o operador.
- Perfis de acesso: `ADMINISTRADOR`, `OPERADOR` e `AUDITOR`, com possibilidade de novos perfis (Q-11, RF-031); autenticação e autorização: ADR-0004.
- Usabilidade simples e objetiva **[ARTIGO]**.
- Interface não toma decisões de segurança; apenas apresenta e solicita ações.

---

## 11. Comunicação com balança e cancelas (RS232 / PySerial)

### 11.1 O que o artigo estabelece **[ARTIGO]**

- Comunicação serial RS232 via **PySerial** para leitura do peso da balança e envio de comandos de abertura/fechamento de cancelas.
- Parâmetros configuráveis: porta, taxa de transmissão, tempo de espera (timeout).
- Na ausência dos equipamentos físicos, **simulação** do comportamento esperado.

### 11.2 O que **não** está definido **[PENDENTE]**

Marca/modelo da balança e do indicador de pesagem; formato do quadro/protocolo de dados; parâmetros seriais; comandos e resposta das cancelas/controlador; adaptadores (RS232↔USB). **Não inventar nenhum desses itens.** Enquanto não houver informação, o desenvolvimento usa **interfaces abstratas + simuladores** (Q-01).

Já informados pelo autor: duas cancelas, uma antes e outra depois da balança (spec 006); sensor de status com cabo dedicado em cada cancela (spec 004); sensores de barreira que agem direto na cancela e não são lidos pelo sistema (spec 006); estabilidade do peso decidida pelo software, com parâmetros sem valor padrão (spec 002).

### 11.3 Integração

Interfaces e simuladores estão implementados (spec 004). A `BalancaSerial` existe (spec 029, PySerial 3.5), mas o registro de protocolos está vazio, então o modo `REAL` da balança é recusado na partida até existir um protocolo com quadros reais (roteiro em `docs/equipamentos/README.md`). `CancelaSerial` continua bloqueada pela Q-01 e pela spec 029 P-1.

- Módulo de dispositivos com contrato abstrato (conceito): *ler peso*, *comandar cancela*, *consultar estado/saúde*; implementações **real** (PySerial) e **simulada** (ver seção 14.2).
- Parsing do quadro da balança isolado em componente puro (sem I/O), testado com quadros de exemplo reais assim que existirem.
- Aceitação de peso condicionada a: leitura bem formada, dentro de faixa plausível e **estável** (critério a definir com o protocolo real).
- Timeouts em todas as operações; políticas de retentativa limitadas e explícitas.
- Um único dono por porta serial.

### 11.4 Segurança operacional (resumo; regras completas no `AGENTS.md` §7)

Em dúvida, o sistema **não autoriza, não aciona e não registra peso**. Falhas de comunicação, reconhecimento inconclusivo, ausência de agendamento, estados inválidos, reinício no meio da operação e concorrência devem ter comportamento seguro **especificado e testado**. O software **não** deve ser a única barreira física; o autor confirmou que existem intertravamentos, sensores de presença e parada de emergência independentes do software (Q-04), o que não foi validado com hardware real.

---

## 12. Necessidades de persistência (sem esquema)

> O esquema de referência está em `docs/modelo-dados/schema.sql`, e o final sai da BE-502. **Não será definido aqui** esquema relacional, entidades finais, atributos ou diagrama. Abaixo estão apenas **necessidades de armazenamento**, derivadas do artigo, para orientar a escolha do banco e a elaboração das specs.

| Necessidade | Origem | Observações |
|---|---|---|
| Veículos (com placa) | **[ARTIGO]** | Placa precisa ser consultável de forma rápida e consistente. |
| Motoristas | **[ARTIGO]** | Podem conter dados pessoais (LGPD). |
| Transportadoras | **[ARTIGO]** | — |
| Agendamentos (operação, veículo, motorista, transportadora, tipo, produto, data prevista, situação) | **[ARTIGO]** | Criação manual. Regras: RN-013 a RN-015, RN-023, RN-024 e spec 008. Faixas de horário entram aqui. |
| Pesagens (inicial/final e demais necessárias) e peso líquido | **[ARTIGO]** | Registro atômico e sem duplicidade; precisão numérica adequada. |
| Eventos de cancela | **[ARTIGO]** | Comandos, resultados e falhas. |
| Registros/eventos do sistema (reconhecimentos, decisões, falhas, intervenções) | **[ARTIGO]** | Base de auditoria/rastreabilidade. |
| Histórico das operações | **[ARTIGO]** | Consulta e auditoria. |
| "Documentos" | prompt do autor | Significado **[PENDENTE]** (Q-03). |
| Imagens de evidência / resultados de LPR | decorrente dos requisitos de diagnóstico (prompt) | Só as imagens das decisões, até o administrador pedir a exclusão (RN-022). Armazenar no banco, no sistema de arquivos ou outro? **[PENDENTE]** (BE-502). |
| Usuários, perfis e sessões | decorrente de "usuário autorizado" e "administrador" | ADR-0004; tabelas na BE-502. |

Requisitos não funcionais de dados **[PROPOSTA]**: integridade referencial; transações para registrar pesagens/estado; histórico imutável ou auditável (política a definir: exclusão lógica, versionamento); restrições que impeçam inconsistências (por ex., mais de uma operação aberta para o mesmo veículo, RN-008; mais de um agendamento aberto para a mesma placa, RN-023); backup e restauração.

---

## 13. Banco de dados — avaliação que fundamentou a decisão

**Status: [DEFINIDO] — PostgreSQL** (decisão do autor em 2026-10-29, C-002). Registro formal: `docs/decisoes/ADR-0001-banco-de-dados.md` (Aceita). A análise abaixo fica como fundamentação. O artigo exige apenas um **banco relacional** **[ARTIGO]**; as três opções abaixo atendem.

### 13.1 Critérios **[PROPOSTA]**

Integridade e restrições; concorrência de escrita (pesagens, eventos, LPR contínuo); consistência transacional; auditoria/histórico; reprodutibilidade com Docker; simplicidade de operação para um protótipo/TCC; suporte no ecossistema Python/FastAPI (dependerá do ORM, D-02); licença compatível com open-source; familiaridade do autor (informação não disponível); recursos da máquina de execução (não informados).

### 13.2 Comparativo

| Aspecto | PostgreSQL | MySQL / MariaDB | SQLite |
|---|---|---|---|
| Modelo | Cliente-servidor, relacional | Cliente-servidor, relacional | Embutido em arquivo, relacional |
| Integridade/restrições | Recursos ricos (restrições, índices parciais, tipos variados), úteis para garantir regras como unicidade condicional de operação ativa | Adequado; alguns recursos avançados de restrição/índice são mais limitados (por exemplo, não há índices parciais nativos) | Suporta restrições básicas; tipagem mais flexível/menos rígida, o que exige disciplina |
| Concorrência de escrita | Boa; adequada a múltiplos escritores (API + processos de LPR/eventos) | Boa | Limitada: um escritor por vez; suficiente para carga baixa, mas risco com escritas concorrentes frequentes |
| Dados semiestruturados (ex.: detalhes de leitura do LPR/eventos) | Suporte nativo a JSON/JSONB | Suporte a JSON | Suporte básico a JSON |
| Docker / reprodutibilidade | Imagem oficial; serviço separado no Compose | Idem | Sem serviço extra (arquivo); mais simples |
| Complexidade operacional | Moderada (serviço, usuários, backup) | Moderada | Mínima |
| Backup/restauração | Ferramentas maduras | Ferramentas maduras | Cópia do arquivo (cuidados com consistência) |
| Adequação a evolução além do protótipo | Alta | Alta | Baixa/média |
| Licença | Open-source permissiva | MySQL: open-source com versão comercial da Oracle; MariaDB: open-source | Domínio público |

### 13.3 Limitações a considerar

- **PostgreSQL**: exige serviço dedicado e mais configuração; consome mais recursos que SQLite; atenção ao dimensionamento se rodar no mesmo equipamento que o OCR (CPU/memória disputadas).
- **MySQL/MariaDB**: sem diferença decisiva de capacidade para este escopo, mas menos recursos de restrição avançada; há duas variantes com diferenças sutis (escolha adicional).
- **SQLite**: risco com escritas concorrentes e com garantias de integridade por tipagem flexível; testar em SQLite e executar em outro motor mascara diferenças de comportamento.

### 13.4 Recomendação preliminar (histórico; decidida na D-01)

**PostgreSQL** é a opção que mais se alinha aos requisitos deste projeto: auditoria e rastreabilidade (histórico confiável), integridade em um sistema com consequências físicas, escritas concorrentes (API + reconhecimento contínuo + eventos de dispositivos), recursos de restrição para impedir estados inconsistentes e fácil reprodutibilidade via Docker. O autor confirmou essa escolha em 2026-10-29 (D-01, ADR-0001).

Pontos levantados antes do ADR, que seguem úteis para a execução real:

1. Confirmar recursos disponíveis no equipamento real de execução (CPU/memória/disco) e se há outros serviços concorrendo (OCR).
2. Confirmar se haverá mais de um processo escrevendo simultaneamente (previsto: sim).
3. Confirmar necessidades de retenção e armazenamento de imagens (Q-08).
4. Verificar familiaridade do autor e suporte do ORM escolhido (D-02).
5. Decidir se SQLite será usado **apenas** para algum fim específico (por exemplo, testes rápidos de unidade) — **não recomendado** como substituto de testes de persistência contra o motor real.

**Fallback**: se o equipamento for muito restrito ou a operação for estritamente de usuário único, SQLite poderia ser considerado em um protótipo mínimo, aceitando suas limitações. Não é a recomendação.

---

## 14. Estratégia de testes **[PROPOSTA]**

Backend: pytest (ADR-0003); há testes unitários, de integração (`tests/integracao`) e ponta a ponta (`tests/ponta_a_ponta`), esses dois com PostgreSQL em contêiner, e a avaliação do LPR, fora da execução padrão. Frontend: Vitest + Testing Library, ESLint, Prettier e `tsc` estrito (ADR-0008). Princípio: **todo teste automatizado roda sem hardware real**.

### 14.1 Níveis

1. **Unitários**: regras de negócio, normalização/validação de placa, cálculo do peso líquido, máquina de estados, parsing de quadros da balança.
2. **Integração**: API + banco (mesmo motor de execução), orquestração com dispositivos e câmera simulados.
3. **Ponta a ponta com simuladores**: fluxo completo (agendamento manual → identificação → autorização → pesagem inicial → pesagem final → peso líquido) e cenários de falha.
4. **Testes manuais/assistidos com hardware real**: quando disponível; registrados separadamente; **só eles** validam o comportamento real do equipamento.

### 14.2 Simulação de equipamentos

- **Simulador de balança**: gera leituras configuráveis (estável, instável, fora de faixa, quadro corrompido, atraso, silêncio/timeout, desconexão).
- **Simulador de cancela**: responde a comandos com sucesso, atraso, falha ou ausência de resposta.
- **Portas seriais virtuais**: o PySerial oferece manipuladores de URL (por exemplo, `loop://` e `socket://`) que permitem testar a camada serial sem porta física; pares de portas virtuais no SO são outra opção — sua adoção é **[PROPOSTA]** a validar.
- A mesma interface abstrata de dispositivos deve ser exercitada com real e simulado.

### 14.3 Visão computacional sem câmera

- **Conjunto de referência** de imagens/vídeos de placas com resultado esperado (ground truth), cobrindo variações de iluminação, ângulo, distância, sujeira, reflexos e tipos de placa (fatores citados na literatura do artigo).
- **Fonte de imagem substituível** (pasta de imagens ou arquivo de vídeo) para repetir testes de forma determinística.
- Métricas a definir (acerto por placa, por caractere, taxa de rejeição segura vs. aceitação incorreta). **Dar maior peso a falsos positivos de autorização do que a falsos negativos** (um falso positivo pode autorizar o veículo errado; um falso negativo exige intervenção manual). Meta numérica **[PENDENTE]**, definir com dados reais.
- Separar testes **do pipeline** (pré-processamento/ROI) dos **do OCR** para facilitar o diagnóstico.
- Licenças e privacidade das imagens de teste (Q-09).

### 14.4 Cenários mínimos de validação **[ARTIGO]**

Veículo com agendamento válido; veículo sem agendamento; falha no reconhecimento da placa; leitura de peso pela comunicação serial; falha de comunicação com a balança; acionamento de cancela; finalização da operação com cálculo do peso líquido. Cada um deve virar critério(s) de aceitação em spec, acrescidos dos casos de falha do `AGENTS.md` §7.2.

---

## 15. Decisões técnicas

| ID | Decisão | Situação / observação |
|---|---|---|
| D-01 | Banco de dados | **Decidido: PostgreSQL** (autor, 2026-10-29). ADR-0001 Aceita. |
| D-02 | ORM e ferramenta de migração | **Decidido (autor, 2026-11-07):** SQLAlchemy 2 Core síncrono (em `asyncio.to_thread`) + psycopg 3 + Alembic, migrações em SQL escrito à mão. ADR-0006. |
| D-03 | Framework do frontend (TypeScript + Tailwind) | **Decidido (autor, 2026-11-07):** React + Vite + React Router, Tailwind CSS v4. ADR-0007. |
| D-04 | Autenticação/autorização e perfis | **Decidido:** ADR-0004 (Aceita, 2026-11-04): sessão no banco com cookie; permissões no código e perfis no banco; autoatendimento do motorista sem login, só pela rede do pátio. |
| D-05 | Estratégia de execução de OCR/serial/captura sem bloquear a API (tarefas em background, worker/processo separado, threads) | **Decidida (2026-11-07, spec 015 §13, delegada):** tarefas asyncio em um processo; OCR, análise de imagem e repositórios em `asyncio.to_thread`; dispositivos assíncronos. Reabrir se a latência medida bloquear a API (R-04). Histórico: **Parcial (2026-10-29, spec 004 P-1):** interfaces dos dispositivos assíncronas (PySerial em `asyncio.to_thread`). OCR: `LeitorPlaca` síncrono chamado em `asyncio.to_thread` (spec 005 P-9); reabrir se a latência medida for alta. Captura de câmera continua em aberto (Q-06). |
| D-06 | Transporte de imagens/eventos em tempo real para a interface | **Decidido:** ADR-0005 (Aceita, 2026-11-04): SSE para eventos e imagens sob demanda; a análise das imagens é em tempo real no backend (RF-034). |
| D-07 | Monólito modular vs. serviços separados | **Decidido**: monólito modular — ADR-0002 (Aceita, 2026-10-29). |
| D-08 | Estratégia de modelos do EasyOCR (cache, modo offline) | **Decidido (2026-10-29, spec 005 P-10):** modelos baixados uma vez, por comando explícito, para uma pasta configurada; operação sem download (modelos ausentes impedem a partida); CPU (D-09). |
| D-09 | Uso de GPU | Não definido; assumir CPU. |
| D-10 | Idioma/convenção de nomes no código | **Decidido:** `CONVENCOES.md` aprovado pelo autor (2026-10-29, C-003). |
| D-11 | Ferramentas de teste, lint, formatação e tipagem estática | **Backend decidido** — ADR-0003 (Aceita, 2026-10-29): pytest, pytest-cov, ruff, mypy estrito; `venv` + `pip`. Frontend decidido (autor, 2026-11-07): Vitest + Testing Library, ESLint + Prettier, `tsc` estrito — ADR-0008. |
| D-12 | Licença do repositório | Não definida. O `LICENSE` MIT e o selo no `README.md` já existem no repositório, sem decisão registrada (C-001). |
| D-13 | Armazenamento e retenção de imagens de evidência | **Parcial (2026-11-04):** só as imagens das decisões, guardadas até o administrador pedir a exclusão (RN-022). **Onde (2026-11-07, delegada):** `bytea` no banco, gravado na mesma transação da decisão (spec 014 §10). Falta a adequação à LGPD (Q-08). |
| D-14 | Protocolos de balança e cancelas | Dependem de informações do equipamento (Q-01). |

---

## 16. Riscos

| ID | Risco | Mitigação proposta |
|---|---|---|
| R-01 | Acionar cancela indevidamente (ex.: sobre veículo) ou autorizar o veículo errado | Fail-safe, estados explícitos, confirmação de resultado, intertravamentos físicos (Q-04, não validados com hardware real), testes de falha. |
| R-02 | Protocolo da balança/cancela desconhecido ou mal documentado | Interfaces abstratas + simuladores; obter documentação/quadros reais cedo (Q-01). |
| R-03 | Leitura incorreta de placa (iluminação, sujeira, ângulo) | Normalização explícita, limiar de confiança, seleção conservadora (spec 005), revisão humana, conjunto de testes representativo. |
| R-04 | Desempenho do EasyOCR em CPU / bloqueio da API | Medir cedo; isolar execução (D-05); considerar GPU apenas se necessário. |
| R-05 | Acesso a portas seriais/USB dentro de contêiner (especialmente Windows/macOS) | Verificar SO real (Q-07); desenhar para poder executar a camada de dispositivos fora do contêiner se necessário. |
| R-06 | Peso registrado em leitura instável/errada | Critério de estabilidade, faixa plausível, validação cruzada, rejeição segura. |
| R-07 | Falta de hardware real durante o desenvolvimento → simulação divergir do equipamento | Registrar que simulação não valida equipamento; testes assistidos com hardware quando possível. |
| R-08 | Dados pessoais (placas, motoristas, imagens) e LGPD | Minimização, CPF mascarado, imagens só das decisões, controle de acesso (RN-022, ADR-0004); adequação à LGPD em aberto (Q-08). |
| R-09 | Escopo crescer além do protótipo do TCC | Controle via specs aprovadas; fora de escopo explícito. |
| R-10 | Queda/reinício do sistema no meio da operação | Persistir estado; retomada segura sem reenviar comandos físicos às cegas. |
| R-11 | Concorrência (eventos duplicados para a mesma operação) | Transações e restrições no banco; idempotência onde aplicável. |
| R-12 | Imagens Docker pesadas e builds lentos | Documentar; volumes de cache; evitar dependências desnecessárias. |

---

## 17. Perguntas a esclarecer antes da implementação

| ID | Pergunta |
|---|---|
| Q-01 | Há balança/indicador e cancelas reais disponíveis (marca/modelo)? Existe documentação do protocolo ou amostras de quadros? Se não, a validação será 100% simulada? — **Parcial (2026-10-29, BE-301):** as cancelas têm sensor de status com cabo dedicado. O sistema deve aceitar várias balanças, com protocolos diferentes (detalhes na spec 004, P-8). Protocolos, quadros e modelos continuam em aberto. |
| Q-02 | Regra exata das pesagens: cargas e descargas têm sempre duas pesagens? Como mapear "inicial/final" para tara/bruto em cada tipo de operação? Como é calculado o peso líquido e existem tolerâncias ou limites? — **Respondida (2026-10-29):** peso líquido = |peso final − peso inicial|, para carga e descarga, sem mapear inicial/final para tara/bruto. Complemento: CARGA = final − inicial; DESCARGA = inicial − final; líquido entre −20 e +20 kg (tolerância configurável) = sem carga nem descarga; abaixo de −20 kg → o administrador intervém (RN-006). |
| Q-03 | O que são "documentos" na persistência (ex.: documentos do motorista/veículo, notas, comprovantes de pesagem)? Há emissão de comprovante? — **Parcial (2026-11-04):** na descarga, o motorista informa o código da nota (RF-033). O restante continua em aberto. |
| Q-04 | Qual é o comportamento desejado para intervenção manual (quem, quando, com que registro)? Há intertravamentos físicos/sensores de presença e botão de emergência independentes do software? — **Respondida (2026-10-29):** só o administrador faz liberação manual. Existem intertravamentos físicos, sensores de presença e parada de emergência independentes do software; o software não depende deles (RN-016). Os sensores de barreira agem direto nas cancelas e não são lidos pelo sistema (spec 006, 2026-11-04). |
| Q-05 | Como será a "orientação de posicionamento do caminhão na balança" (semáforo, painel, mensagem na interface, sensores)? — **Respondida (2026-11-04):** fora do protótipo; o procedimento fica com a equipe; RF-012. |
| Q-06 | Quantas câmeras, de que tipo (rede/USB), onde ficarão, e qual a resolução? — **Parcial (2026-11-04):** câmeras na frente, atrás e superior; a superior identifica a posição, podendo combinar todas as câmeras (Q-17). Faltam o tipo, a resolução e o uso das câmeras da frente e de trás. |
| Q-07 | Qual sistema operacional e equipamento executarão o sistema no ambiente real/de demonstração? Há GPU? |
| Q-08 | Imagens de evidência: guardar? Por quanto tempo? Quem pode acessá-las? Há necessidade de adequação à LGPD além do básico? — **Parcial (2026-11-04):** só as imagens das decisões, até o administrador pedir a exclusão; o `AUDITOR` vê as das decisões, mas não as em tempo real (RN-022). Falta a adequação à LGPD. |
| Q-09 | De onde virão as imagens de teste (próprias, públicas)? Há restrições de licença/privacidade? — **Parcial (2026-10-29, spec 005 P-7):** ainda não há imagens. O autor vai obter o acervo da empresa (imagens reais de pesagens). Ele fica fora do repositório; falta confirmar a autorização e as restrições de publicação. Os testes automáticos usam imagens sintéticas. |
| Q-10 | O escopo de placas é apenas o padrão brasileiro (formato antigo e Mercosul)? — **Respondida (2026-10-29):** só placas brasileiras, formato antigo (AAA9999) e Mercosul (AAA9A99). |
| Q-11 | Quantos usuários/perfis e como será o controle de acesso? — **Respondida (2026-11-04):** por enquanto `ADMINISTRADOR`, `OPERADOR` e `AUDITOR`; deve permitir mais usuários e perfis com permissões diferentes (RF-031). O `docs/modelo-dados/schema.sql` só admite dois (rever na BE-502). A estratégia foi decidida na CT-001 (ADR-0004). |
| Q-12 | Volume esperado de operações simultâneas (um ponto de pesagem? uma ou várias balanças)? — **Parcial (2026-11-04, spec 006):** por enquanto uma balança, com um caminhão sobre ela por vez e várias operações abertas, no máximo uma por placa (RF-030, RN-008, RN-019). Falta o volume esperado. |
| Q-13 | O que acontece se o veículo chegar fora do horário/data do agendamento? Regras de "agendamento válido" (janela de tempo, status). — **Respondida (2026-10-29):** o agendamento só vale para o dia; quem agenda escolhe uma janela de horários para entrar na fila ou é colocado no primeiro horário disponível. Complemento: faixas fixas com capacidade, configuradas pelo administrador; antes da faixa não libera; depois, no mesmo dia, libera (RF-028, RF-029, RN-014, RN-015). **Complementada (2026-11-04, spec 008):** faixa encerrada não aceita novos agendamentos (RN-024), e a placa só pode ter um agendamento aberto (RN-023). |
| Q-14 | O artigo inclui "produto" no agendamento, mas não lista cadastro de produtos (nem de tipos de veículo, presentes no esquema de referência). Esses cadastros fazem parte do escopo? (C-102) — **Respondida (2026-10-29):** sim; RF-025, RF-026. |
| Q-15 | Como é liberada a saída do caminhão: há cancela de saída comandada pelo sistema, ou a saída é apenas registrada? (C-102) — **Respondida (2026-10-29):** há cancela de entrada e de saída; a de saída só libera após o caminhão ser identificado no perímetro correto da balança e estar pesado; RF-017, RF-027, RN-012. **Complementada (2026-11-04, spec 006):** a saída abre depois de cada pesagem, e o caminhão volta pela entrada para a pesagem final. |
| Q-16 | "Gerenciar agendamentos" inclui editar e cancelar? Quem pode fazer isso e em que estados? (C-102) — **Respondida (2026-10-29):** apenas o administrador do sistema; RN-013. |
| Q-17 | Como o sistema identifica que o caminhão está "no perímetro correto da balança" (sensores de presença, câmera, confirmação do operador)? "Estar pesado" significa pesagem final aceita e registrada? (C-102) — **Respondida (2026-11-04):** a câmera superior identifica a posição, podendo combinar todas as câmeras; "estar pesado" = pesagem final aceita e registrada; RF-027, RN-012. O critério de análise das imagens será definido em spec. |

---

## 18. Consistência com o `AGENTS.md`

- O `AGENTS.md` define **como** trabalhar (SDD, testes, segurança, relato); este arquivo define **o quê** e **com quê**.
- Em caso de aparente conflito, **pare e pergunte** ao autor; não escolha por conta própria.
- Qualquer item **[PROPOSTA]** só vira **[DEFINIDO]** com aprovação explícita; ao ocorrer, atualize este documento e registre o ADR correspondente.
- Este documento deve ser atualizado quando decisões pendentes forem resolvidas e quando comandos, diretórios e serviços reais passarem a existir.
