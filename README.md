# EasyScale

Sistema open-source para automatizar a pesagem rodoviária de caminhões, com leitura de placa por visão computacional. Projeto de TCC do IFRS, campus Veranópolis.

## Tecnologias

### Backend
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571.svg?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-000?style=for-the-badge&logo=postgresql)

### Frontend
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)

### OCR
![OpenCV](https://img.shields.io/badge/opencv-%23white.svg?style=for-the-badge&logo=opencv&logoColor=white)
- EasyOCR

### Infraestrutura
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

## O que o sistema faz

O sistema cuida das etapas que vêm depois do agendamento:

1. O agendamento é sempre manual. Quem o cria é um usuário com permissão ou o próprio motorista, no autoatendimento. Nada o cria sozinho.
2. Quando o caminhão chega, a câmera lê a placa. O sistema compara a placa com os cadastros e procura um agendamento válido para o dia. Se a leitura for duvidosa ou não houver agendamento, ninguém entra: o sistema registra o caso e chama o operador.
3. Com a entrada autorizada, a cancela de entrada abre. O sistema confere pela câmera superior se o caminhão está na posição certa e só então lê o peso, que precisa ser válido e estável. Esse é o peso inicial.
4. O caminhão sai pela cancela de saída para a carga ou descarga. Essa etapa acontece fora do sistema, que apenas acompanha em que ponto a operação está.
5. Na volta, a placa é lida de novo e o caminhão é pesado outra vez. O peso líquido sai da diferença entre as duas pesagens: final menos inicial na carga, inicial menos final na descarga.
6. A operação e seus eventos ficam guardados para consulta e auditoria.

A interface também mostra a operação em tempo real, o histórico, as imagens e as leituras da câmera (para diagnóstico) e as intervenções manuais do administrador.

## Estado do projeto

É um protótipo. Backend, banco, orquestração, frontend e Docker existem e rodam, mas só em modo `SIMULADO`.

- Nada foi validado com balança, cancela ou câmera reais. Os testes mostram que a lógica do sistema funciona com simuladores. Eles não dizem nada sobre o equipamento.
- O modo `REAL` de balança, cancelas e câmeras está bloqueado. Com ele ativado, o backend recusa a partida. Faltam os protocolos de comunicação com os equipamentos (Q-01) e a definição das câmeras e do critério de análise da posição do caminhão (Q-06).
- O reconhecimento de placa com OpenCV e EasyOCR está no código (`backend/src/pesagem/lpr/`) e nos testes, mas a demonstração usa a câmera simulada: as placas chegam por uma rota da API.

O andamento detalhado fica em [`specs/tarefas-iniciais.md`](specs/tarefas-iniciais.md).

## Instalação

Há dois caminhos. Para usar ou demonstrar o sistema, suba tudo pelo Docker ([Como rodar em modo simulado](#como-rodar-em-modo-simulado)). Para mexer no código, prepare o ambiente na máquina ([Ambiente de desenvolvimento local](#ambiente-de-desenvolvimento-local)). Os dois rodam só em modo `SIMULADO` e não precisam de hardware.

### Pré-requisitos

| Para | Precisa de | Versões já usadas |
|---|---|---|
| Rodar pelo Docker | Docker e Docker Compose | Docker 29.9, Compose 5.6 e 5.7 |
| Desenvolver o backend | Python 3.12 ou mais novo, com `venv` | 3.14.7 e 3.14.9 |
| Desenvolver o frontend | Node 22.22.2 ou mais novo, com npm | Node 22.22 e 26.13 |
| Testes de banco e banco de desenvolvimento | Docker (sobe o PostgreSQL) | — |
| Roteiro de demonstração | `curl` e `jq` | — |

No Linux, o Docker acessa portas seriais sem complicação. No Windows e no macOS esse acesso é limitado (`AMBIENTE.md`, R-05), mas isso só importa para equipamento real, que ainda não é suportado.

### Obter o código

```sh
git clone https://github.com/rafaelbzanon/easyscale.git
cd easyscale
cp .env.exemplo .env    # troque PESAGEM_BANCO_SENHA antes de subir o banco
```

O `.env` serve aos dois caminhos e não vai para o git. Veja a seção [Configuração](#configuração).

## Como rodar em modo simulado

Na raiz do repositório, com o `.env` criado:

```sh
docker compose up -d --build --wait   # banco, migração, backend e frontend
```

A primeira subida constrói as imagens e demora. Só o frontend publica porta, em `https://localhost:8443`. O banco e a API ficam na rede interna do compose.

### Primeiro administrador

O sistema nasce sem usuários. Crie o primeiro administrador com o comando abaixo, que precisa de terminal. Ele pede nome, login e a senha duas vezes, sem eco, e só funciona enquanto não existir administrador ativo.

```sh
docker compose run --rm migracao python -m pesagem.api.criar_administrador
```

### HTTPS e certificado

O HTTPS usa a CA interna do Caddy, então o navegador avisa até você confiar nela. Para copiar o certificado raiz e testar pelo terminal:

```sh
docker compose cp frontend:/data/caddy/pki/authorities/local/root.crt ./pesagem-ca.crt
curl --cacert ./pesagem-ca.crt https://localhost:8443/api/sessoes/atual   # 401 sem cookie = no ar
```

Para usar um certificado próprio, siga a [spec 027](specs/features/027-compose/spec.md), seção 4.3. Esse caminho não foi exercitado.

### Parar

```sh
docker compose down      # mantém banco, modelos e certificados
docker compose down -v   # apaga tudo isso também
```

## Demonstração pelos simuladores

No modo simulado, o administrador controla a câmera, a balança e as cancelas pela API (permissão `CONTROLAR_SIMULADORES`, rotas em `/api/simuladores`, [spec 011](specs/features/011-contrato-api-diagnostico/spec.md), seção 6.4). Essas rotas só existem quando todos os dispositivos estão em `SIMULADO`. Elas não abrem cancela nem gravam peso: só mudam o que o simulador devolve, e o fluxo normal do sistema faz o resto.

O roteiro abaixo cadastra um caminhão, agenda uma carga e leva a operação até `FINALIZADA`, pela API. Rode no mesmo diretório do `pesagem-ca.crt`, com o login do administrador criado acima.

```sh
read -rsp 'Senha do admin: ' SENHA; echo
API=https://localhost:8443/api
c() { curl -sS --cacert ./pesagem-ca.crt -b /tmp/pesagem-cookies -c /tmp/pesagem-cookies \
  -H 'Origin: https://localhost:8443' -H 'Content-Type: application/json' "$@"; }
espera() { for _ in $(seq 40); do
  [ "$(c $API/pesagens/$1 | jq -r .situacao)" = "$2" ] && return; sleep 1; done
  echo "não chegou a $2" >&2; return 1; }

c -X POST $API/sessoes -d "{\"login\":\"admin\",\"senha\":\"$SENHA\"}" | jq -c .usuario

# Cadastros e agendamento manual (faixa do dia inteiro, para a demonstração).
HOJE=$(TZ=America/Sao_Paulo date +%F)
MOT=$(c -X POST $API/motoristas -d '{"nome":"Ana Lima","cpf":"52998224725"}' | jq .id)
TIPO=$(c -X POST $API/tipos-veiculo -d '{"descricao":"Truck"}' | jq .id)
PROD=$(c -X POST $API/produtos -d '{"codigo":"SOJA","descricao":"Soja"}' | jq .id)
c -X POST $API/faixas-horario -d '{"hora_inicio":"00:00","hora_fim":"23:59","capacidade":5}' > /dev/null
VEIC=$(c -X POST $API/veiculos -d "{\"placa\":\"ABC1D23\",\"tipo_veiculo_id\":$TIPO}" | jq .id)
c -X POST $API/agendamentos -d "{\"veiculo_id\":$VEIC,\"motorista_id\":$MOT,\"produto_id\":$PROD,\"tipo_operacao\":\"CARGA\",\"data_prevista\":\"$HOJE\"}" | jq -c '{id,status,placa}'

# A câmera simulada "vê" a placa ABC1D23 com confiança 0.95.
chegada() { c -X POST $API/simuladores/chegadas -d '{"textos":[{"texto":"ABC1D23","confianca":"0.950"}]}' > /dev/null; sleep 3
  c $API/operacao/estado | jq -r '.ultima_leitura_placa | "\(.decisao) pesagem \(.pesagem_id)"'; }
chegada
P=$(c $API/operacao/estado | jq .ultima_leitura_placa.pesagem_id)
espera $P ENTRADA_LIBERADA

# Caminhão em posição, peso inicial estável de 15000 kg, saída da balança.
c -X POST $API/simuladores/posicao -d '{"cenario":"CONFIRMADA"}' > /dev/null; espera $P POSICIONADA_INICIAL
c -X POST $API/simuladores/balanca -d '{"cenario":"ESTAVEL","peso_kg":"15000","amplitude_kg":null}' > /dev/null; espera $P SAIDA_INICIAL_LIBERADA
c -X POST $API/simuladores/posicao -d '{"cenario":"AUSENTE"}' > /dev/null; espera $P EM_CARGA_DESCARGA

# Volta com 45000 kg. A balança só é lida com o caminhão em posição, então troque o peso antes.
chegada
espera $P RETORNO_LIBERADO
c -X POST $API/simuladores/balanca -d '{"cenario":"ESTAVEL","peso_kg":"45000","amplitude_kg":null}' > /dev/null
c -X POST $API/simuladores/posicao -d '{"cenario":"CONFIRMADA"}' > /dev/null; espera $P SAIDA_LIBERADA
c -X POST $API/simuladores/posicao -d '{"cenario":"AUSENTE"}' > /dev/null; espera $P FINALIZADA
c $API/pesagens/$P | jq -c '{situacao,peso_inicial_kg,peso_final_kg,peso_liquido_kg,classificacao}'
```

No fim, o roteiro mostra a pesagem finalizada com o peso líquido de 30000 kg. O histórico completo da operação está em `GET /api/pesagens/{id}/eventos`.

Para ver as falhas, troque o cenário antes do passo correspondente. A balança aceita `SEM_RESPOSTA`, `INSTAVEL`, `QUADRO_CORROMPIDO` e `DESCONECTADA`. As cancelas aceitam `FALHA`, `NAO_MOVE` e `SENSOR_SEM_RESPOSTA`. A posição aceita `INCONCLUSIVA`. Uma placa com confiança baixa, uma placa sem agendamento ou uma lista vazia de textos também mostram as recusas. Todos os cenários estão na spec 011, seção 5.5. Nas falhas, o sistema não autoriza, não grava peso e espera uma ação do operador.

## Ambiente de desenvolvimento local

Aqui o backend e o frontend rodam na máquina, e só o banco fica no Docker. A referência completa dos comandos está no [`AMBIENTE.md`](AMBIENTE.md), seção 6.1, e as regras de organização do código no [`CONVENCOES.md`](CONVENCOES.md).

### 1. Backend: ambiente virtual e dependências

A partir de `backend/`:

```sh
python3 -m venv .venv
.venv/bin/pip install --group dev    # ferramentas de teste e lint; exige pip 25.1 ou mais novo no venv

# Dependências de execução. O pacote não é instalado (spec 001); sem elas,
# a API e boa parte dos testes falham com ModuleNotFoundError.
.venv/bin/python -c "import tomllib; print(*tomllib.load(open('pyproject.toml','rb'))['project']['dependencies'], sep='\n')" | .venv/bin/pip install -r /dev/stdin

# Visão computacional. O torch só para CPU vem antes, do índice do PyTorch;
# senão o pip baixa a versão com CUDA, muito maior.
.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 torchvision==0.29.1
.venv/bin/pip install --group lpr
```

O grupo `lpr` é obrigatório mesmo em modo simulado, porque a câmera simulada usa o OpenCV. Os modelos do EasyOCR só são necessários para a avaliação com imagens reais (`AMBIENTE.md` §6.1).

### 2. Banco de desenvolvimento

Na raiz, com o `.env` criado:

```sh
docker compose --profile dev up -d db-dev    # PostgreSQL em 127.0.0.1:5432, volume próprio
```

Se a porta 5432 da máquina estiver ocupada, defina `PESAGEM_BANCO_PORTA_DEV` e `PESAGEM_BANCO_PORTA` com outra porta no `.env`.

### 3. Backend: variáveis, migrações e primeiro administrador

O backend lê a configuração do ambiente. No mesmo terminal em que ele vai rodar, a partir de `backend/`:

```sh
set -a; . ../.env; set +a                 # exporta todas as variáveis do .env
export PESAGEM_BANCO_HOST=127.0.0.1       # no .env o host é o serviço `db` do compose
export PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS=http://localhost:5173   # origem do npm run dev

PYTHONPATH=src .venv/bin/alembic upgrade head
PYTHONPATH=src .venv/bin/python -m pesagem.api.criar_administrador   # pede nome, login e senha
PYTHONPATH=src .venv/bin/uvicorn --factory pesagem.main:criar_aplicacao --host 127.0.0.1 --port 8000
```

Rode o backend em um processo só, sem `--workers` (ADR-0002). Se faltar uma variável obrigatória, a partida para com `ErroConfiguracao: variável obrigatória ausente: <NOME>`.

### 4. Frontend

Em outro terminal, a partir de `frontend/`:

```sh
npm ci                                                        # instala pelo package-lock.json
PESAGEM_GERAL_URL_BACKEND=http://127.0.0.1:8000 npm run dev   # repassa /api ao backend
```

Abra o endereço que o Vite mostrar (normalmente `http://localhost:5173`) e entre com o administrador criado no passo 3. Se o Vite usar outra porta, ajuste `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS` e reinicie o backend.

### 5. Conferir a instalação

Rode os testes da seção [Testes](#testes). Com tudo instalado, nenhum deve falhar na coleta.

Para desligar o banco de desenvolvimento: `docker compose --profile dev down`. O volume `pesagem-dados-db-dev` continua; `-v` apaga.

### Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` (ou `sqlalchemy`, `alembic`, `serial`) | Venv sem as dependências de execução | Rode o comando de dependências de execução do passo 1 |
| `ModuleNotFoundError: No module named 'cv2'` | Falta o grupo `lpr` | Instale o torch para CPU e depois o grupo `lpr` (passo 1) |
| `ErroConfiguracao: variável obrigatória ausente` | Variáveis não exportadas neste terminal | Repita o `set -a; . ../.env; set +a` do passo 3 |
| Alembic ou backend: `Is the server running on that host…` | Banco fora do ar ou host errado | Suba o `db-dev` (passo 2) e confira `PESAGEM_BANCO_HOST=127.0.0.1` |
| Docker: `failed to add the host <=> sandbox pair interfaces: operation not supported` | O kernel foi atualizado e a máquina não foi reiniciada, então faltam os módulos de rede do kernel em execução | Reinicie a máquina |
| `npm run dev` para com `Defina PESAGEM_GERAL_URL_BACKEND…` | Variável do proxy ausente | Passe a variável como no passo 4 |

## Testes

Backend, a partir de `backend/`, com o ambiente virtual pronto como no [passo 1](#1-backend-ambiente-virtual-e-dependências). Os testes de persistência e de API sobem um PostgreSQL em contêiner, então precisam de Docker e falham sem ele.

```sh
.venv/bin/pytest                        # tudo
.venv/bin/pytest tests/ponta_a_ponta    # fluxo completo e falhas, só pela API
.venv/bin/mypy                          # tipagem
```

Frontend, a partir de `frontend/`:

```sh
npm test
npm run typecheck
```

Os testes de ponta a ponta usam os simuladores e provam a lógica do sistema, não o comportamento de equipamento real.

## Configuração

Toda a configuração é por variáveis de ambiente, no `.env` copiado do [`.env.exemplo`](.env.exemplo). O arquivo `.env` não vai para o git.

- Troque `PESAGEM_BANCO_SENHA`. Ela só vale na criação do volume do banco.
- Os valores de balança, reconhecimento de placa, tempos-limite e tempo real do `.env.exemplo` servem para a demonstração. Ninguém os calibrou com equipamento nem com imagens reais de placas.
- Se mudar o host ou a porta do HTTPS, ajuste também `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS`.
- O autoatendimento do motorista fica desligado enquanto `PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES` estiver vazia.

## Documentação

- [`specs/`](specs/README.md): índice das especificações, requisitos (`requisitos.md`), glossário e uma pasta por funcionalidade em `specs/features/`.
- [`docs/decisoes/`](docs/decisoes): decisões de arquitetura (ADR), como banco, autenticação e tempo real.
- [`AMBIENTE.md`](AMBIENTE.md): referência técnica e comandos.
- [`AGENTS.md`](AGENTS.md): regras de trabalho para agentes de IA neste repositório.

## Licença

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

O repositório traz um arquivo [`LICENSE`](LICENSE) com o texto da licença MIT. A escolha final da licença (D-12) ainda está pendente com o autor.
