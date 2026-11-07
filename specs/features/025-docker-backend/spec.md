# Spec 025 — Imagem Docker do backend

- **Trilha:** Backend
- **Status:** Implementada (BE-801, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** BE-801 — `specs/tarefas-iniciais.md`
- **Requisitos:** RNF-004 (reprodutibilidade), RNF-013 (sem segredos), `AGENTS.md` §7.3 (modo simulado por padrão)
- **Decisões:** ADR-0002 (um processo), ADR-0006 (migrações), D-08 e D-09 (modelos do OCR e CPU), spec 005 (P-9, P-10)
- **Código:** `backend/Dockerfile`, `backend/.dockerignore`

---

## 1. Contexto e origem

- `AMBIENTE.md` §6, §7.1 e §7.2 pedem uma imagem do backend, sem modelos nem dados de teste dentro, com o tamanho e o tempo de build registrados.
- O `compose.yaml` não é desta spec (INT-001, spec 027). Aqui só existe a imagem.

## 2. Objetivo

Uma imagem que roda o backend em modo simulado, como usuário sem privilégios, com um único processo `uvicorn`, sem segredo e sem modelo do OCR dentro.

## 3. Fora de escopo

- `compose.yaml`, rede, publicação de porta e banco (spec 027).
- Imagem do frontend (spec 026).
- Execução com hardware real e mapeamento de portas seriais (R-05, Q-07). Nada é mapeado nem configurado aqui.
- GPU (D-09).

## 4. Decisões

### 4.1 Imagem base e versão

`python:3.12.15-slim-trixie`.

| Escolha | Motivo |
|---|---|
| Python 3.12 | É o mínimo suportado (`pyproject.toml`, spec 001 P-2). A imagem prova o mínimo, e não a versão 3.14 do venv de desenvolvimento. |
| 3.12.15 | A imagem foi publicada em 2026-10-06, mais de 14 dias antes de hoje (critério da spec 001 §8). Existe a 3.12.16; não conferi a data dela. |
| Debian (`trixie`), não Alpine | `torch`, `opencv` e `easyocr` publicam pacotes para glibc. Em musl (Alpine) o build compilaria tudo ou falharia. |
| `slim` | Menor que a imagem completa. Todas as dependências têm pacote pronto, então não precisa de compilador. |
| Tag fixa, sem digest | A tag identifica a versão. O digest não foi fixado; a reprodução exata do Debian depende do registro manter a tag. |

### 4.2 Dependências

- O `pyproject.toml` continua a única fonte das versões. O Dockerfile lê `[project].dependencies` e o grupo `lpr` com `tomllib`, porque o pip da imagem (25.0.1) não lê `--group` e o pacote não é instalado (spec 001, Q-B1).
- `torch` e `torchvision` entram primeiro, só para CPU, pelo índice `https://download.pytorch.org/whl/cpu` (D-09, `AMBIENTE.md` §6.1). Depois entram as dependências de execução e o restante do `lpr`.
- O grupo `dev` (pytest, ruff, mypy) e a pasta `tests/` não vão para a imagem.
- A instalação vem antes da cópia de `src/`: mudar código não refaz a camada de dependências.

### 4.3 Modelos e acervo

- Nenhum modelo do EasyOCR e nenhuma imagem do acervo entram na imagem (P-9).
- Os modelos ficam no volume `pesagem-modelos-ocr`, montado em `/modelos-ocr`. O diretório existe na imagem com o dono `pesagem`, então um volume novo herda a permissão. Um `bind mount` precisa de permissão de escrita para o uid 10001 durante o download.
- Só o comando explícito baixa (P-10):

```sh
docker run --rm -v pesagem-modelos-ocr:/modelos-ocr pesagem-backend \
  python -m pesagem.lpr.baixar_modelos /modelos-ocr en
```

- Na operação, monte o mesmo volume com `:ro`. Sem modelo, o leitor falha na criação com `ErroConfiguracaoLpr` e não tenta baixar (P-10).
- A API de hoje não cria o leitor, então a partida não exige os modelos. Quando a orquestração (spec 015) passar a criar, os modelos viram obrigatórios na partida, como a P-10 já diz.

### 4.4 Migração: comando separado

A migração **não** roda na partida. Comando:

```sh
docker run --rm --env-file <arquivo> pesagem-backend alembic upgrade head
```

Motivos:

- Alterar o esquema é uma ação deliberada. Não deve acontecer só porque o contêiner reiniciou.
- Uma migração que falha na partida vira um laço de reinício sem erro claro. Como comando, a falha aparece uma vez, com a saída do Alembic.
- Duas instâncias subindo juntas não disputam a migração.
- O compose (spec 027) pode rodar o comando como serviço de uma execução só, antes do `backend`.

O primeiro administrador também é comando separado (`python -m pesagem.api.criar_administrador`, spec 012 §6.10). Pede a senha no terminal, então exige `docker run -it`.

### 4.5 Execução

- Usuário `pesagem` (uid 10001), shell `nologin` e sem diretório pessoal. Sem `root` na execução.
- `CMD ["uvicorn", "--factory", "pesagem.main:criar_aplicacao", "--host", "0.0.0.0", "--port", "8000"]`. Forma `exec`: o `uvicorn` é o processo 1 e recebe o sinal de parada. Sem `--workers` (ADR-0002).
- Escuta em `0.0.0.0` dentro do contêiner. Quem expõe a porta é o `compose.yaml`; em teste manual, publique só em `127.0.0.1`.
- Modo simulado: a imagem não define variável de hardware, e o backend ainda não tem modo real (`config.py`). Hardware real exigirá configuração explícita, em spec própria.
- Sem segredo na imagem: nenhuma `PESAGEM_*` é definida (`ENV` só tem `PYTHON*`, `PYTHONPATH` e `PIP_*`). O `.dockerignore` deixa `.env`, `.env.*`, `.venv`, caches e `tests/` fora do contexto. As `PESAGEM_*` entram na execução (`--env-file` ou `-e`).
- Sem `HEALTHCHECK`: a API não tem rota de saúde definida. Ver §11.

## 5. Comportamento em falha

| Situação | Resultado |
|---|---|
| `PESAGEM_*` obrigatória ausente | O contêiner sai com `ErroConfiguracao: variável obrigatória ausente: <NOME>` (spec 014 §8). |
| Banco inacessível na migração | O `alembic` sai com erro; nada é alterado. |
| Modelos do OCR ausentes | `ErroConfiguracaoLpr`, sem download (P-10). |

## 6. Medidas

Máquina do autor, Docker 29.9.0, base `python:3.12-slim` já em cache local, rede doméstica, 2026-11-07.

| Medida | Valor |
|---|---|
| Build sem cache (`--no-cache`) | 1 min 10 s (`time docker build --no-cache`) |
| Build com cache, só `src/` alterado | 1,3 s |
| Tamanho da imagem | 2,09 GB (`docker image inspect`: 2 092 065 008 bytes) |
| Camada das dependências | 1,49 GB (`torch` CPU, `easyocr`, `opencv`, SQLAlchemy, FastAPI e outras) |
| Camada do código | 508 kB |
| Modelos no volume (`en`) | 98 MB (`craft_mlt_25k.pth` 83 MB e `english_g2.pth` 15 MB) |

O build frio depende da rede (o `torch` CPU tem 196 MB). Em outra máquina o tempo muda.

## 7. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | `docker build backend/` termina sem erro e a imagem tem `torch` `+cpu`, `easyocr` e `cv2`. |
| CA-002 | O contêiner roda como uid 10001, e o processo 1 é um único `uvicorn`. |
| CA-003 | Com as `PESAGEM_*` e um `postgres:18.6-alpine`, `alembic upgrade head` leva o banco à revisão `0003`. |
| CA-004 | Com o banco migrado, `GET /api/sessoes/atual` sem cookie dá `401` com o corpo `{"erro":{"codigo":"NAO_AUTENTICADO",...,"campos":[]}}` (spec 007 §3.2). |
| CA-005 | `POST /api/sessoes` com login inexistente dá `401 CREDENCIAIS_INVALIDAS`, o que exercita o banco. |
| CA-006 | A imagem não contém modelo, acervo, `tests/`, `.env` nem `PESAGEM_*`. |
| CA-007 | O comando de download preenche o volume, e o leitor abre os modelos com a rede desligada e o volume `:ro`. |
| CA-008 | Com o volume vazio e a rede desligada, o leitor falha com `ErroConfiguracaoLpr` e não baixa nada. |

## 8. Verificação (2026-11-07)

Todos os critérios foram executados nesta data, com saída real: CA-001 a CA-005 e CA-007 a CA-008 passaram. CA-006: `/app` tem só `pyproject.toml` e `src`; nenhuma `PESAGEM_*` no `env` da imagem.

**Não verificado:** `criar_administrador` dentro do contêiner (precisa de terminal interativo, indisponível na sessão); o conjunto de testes do backend em Python 3.12 (a suíte rodou só no 3.14 do venv); o download do idioma `pt`.

## 9. Impacto

- **Compose (spec 027):** usa a imagem, o volume `pesagem-modelos-ocr` em `/modelos-ocr`, o serviço de migração e o `--env-file`.
- **`AMBIENTE.md` §6.1, §7.2 e §0.2:** passam a citar os comandos da §4 e as medidas da §6 (editado pelo Maestro).
- **Backend:** nenhuma mudança de código.

## 10. Riscos

- **Imagem grande (R-12):** 2,09 GB, quase todo `torch`. Aceito; o corte exigiria trocar o EasyOCR.
- **Portas seriais (R-05):** nada é mapeado. No perfil `hardware-real`, o uid 10001 precisaria de permissão no dispositivo; não verificado.
- **Tag sem digest:** ver §4.1.

## 11. Perguntas em aberto

| # | Pergunta | Recomendação |
|---|---|---|
| P-1 | A API deve ter uma rota de saúde (para o `healthcheck` do compose)? Hoje não existe e o contrato não a define. | Não criar sem contrato. O compose pode usar o `GET /api/sessoes/atual` e aceitar `401` como "vivo". Decisão da spec 027. |
| P-2 | Quais idiomas do EasyOCR baixar? A pasta e os idiomas ainda não têm variável em `config.py`. | Definir na spec 015, junto com a criação do leitor. Aqui só o comando e o volume. |
