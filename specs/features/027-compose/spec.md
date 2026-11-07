# Spec 027 — Compose

- **Trilha:** Integração
- **Status:** Implementada (INT-001, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** INT-001 — `specs/tarefas-iniciais.md`
- **Requisitos:** RNF-003 (modo simulado por padrão), RNF-004 (reprodutibilidade), RNF-013 (sem segredos), `AGENTS.md` §7.3
- **Decisões:** ADR-0002 (um processo), ADR-0004 (cookie `Secure`, HTTPS na demonstração), ADR-0005 (SSE sem buffer), specs 013 §6.1 (IP real atrás do proxy), 025 e 026 (imagens)
- **Código:** `compose.yaml`, `Caddyfile`, `.env.exemplo` (todos na raiz)

---

## 1. Contexto e origem

- As specs 025 e 026 entregaram as imagens e deixaram para cá: banco, migração, rede, HTTPS, proxy, saúde e perfis.
- `specs/features/013` §6.1 exige que o backend só aceite o endereço do cliente vindo do proxy configurado aqui. O ADR-0005 exige proxy sem buffer em `/api/operacao/eventos`. O ADR-0004 exige HTTPS na demonstração (P-D).

## 2. Objetivo

`cp .env.exemplo .env && docker compose up --build` sobe o sistema inteiro em modo simulado, com HTTPS, sem expor o banco nem a API ao host.

## 3. Fora de escopo

- Hardware real. O perfil existe só para marcar o lugar e está bloqueado (§4.5).
- Teste ponta a ponta automatizado (INT-002, spec 028).
- Download dos modelos do OCR como serviço. Segue o comando da spec 025 §4.3.
- Ambiente de produção real, backup do banco e monitoramento.

## 4. Decisões

### 4.1 Serviços e ordem de partida

| Serviço | Imagem | Papel |
|---|---|---|
| `db` | `postgres:18.6-alpine` (a dos testes, ADR-0006 §3.1) | Banco no volume `pesagem-dados-db`. Sem `ports`. |
| `migracao` | `pesagem-backend` | Execução única de `alembic upgrade head`. Roda a cada `up`; é idempotente. |
| `backend` | `pesagem-backend` | `uvicorn` com um processo. Sem `ports`. Espera a `migracao` terminar com sucesso. |
| `frontend` | `pesagem-frontend` | Caddy: HTTPS, tela e proxy de `/api`. Único serviço com porta publicada. |

Ordem: `db` saudável → `migracao` termina → `backend` saudável → `frontend`. O volume `pesagem-modelos-ocr` entra no `backend` em `/modelos-ocr:ro` (spec 025 §4.3). O `backend` roda com `cap_drop: ALL` e `no-new-privileges`. O `frontend` roda com `read_only`, `cap_drop: ALL` e `NET_BIND_SERVICE` (spec 026 §4.5).

A migração é um serviço, e não parte da partida do backend, pelos motivos da spec 025 §4.4. O primeiro administrador continua comando manual (§6.1).

**Reinício do backend.** O `backend` tem `restart: unless-stopped`. Se a orquestração parar, o próprio backend encerra o processo (decisão do Keel, em `main.py`) e o Docker o sobe de novo. A retomada segue a spec 006 §7.2: nenhum comando físico é repetido às cegas. O `db` e o `frontend` também têm `restart: unless-stopped`; a `migracao` e o serviço `hardware-real` ficam em `"no"`. A política só vale para parada que o Docker não considera manual. `docker compose stop` e `docker compose kill` deixam o contêiner parado.

### 4.2 Rede e IP do cliente

- Rede `pesagem`, sub-rede `172.28.0.0/24`. O `frontend` tem o IP fixo `172.28.0.10` (`PESAGEM_IP_PROXY`).
- O `backend` roda com `--proxy-headers --forwarded-allow-ips <PESAGEM_IP_PROXY>`. Só esse IP pode informar o endereço do cliente (spec 013 §6.1). Os outros pedidos têm o endereço de quem conectou.
- O Caddy sobrescreve o `X-Forwarded-For` com o endereço de quem conectou ao `frontend`. Um cabeçalho forjado pelo cliente não chega ao backend.
- Atrás do Docker, uma conexão vinda da própria máquina aparece com o IP do gateway da rede (`172.28.0.1`). Para testar o autoatendimento da máquina, a rede dele precisa cobrir esse IP.

### 4.3 HTTPS

- O Caddy do `frontend` usa o `Caddyfile` da raiz, montado em `/etc/caddy/Caddyfile`. Ele repete os blocos da spec 026 §4.3 e acrescenta o site HTTPS. HTTP/3 e redirecionamento de porta 80 ficam desligados: só a porta TCP é publicada.
- **Padrão: CA interna do Caddy** (`PESAGEM_HTTPS_TLS=internal`). Decisão delegada pelo autor (spec 026 P-1). O navegador avisa até confiar na CA. O certificado raiz fica no volume `pesagem-certificados`:

```sh
docker compose cp frontend:/data/caddy/pki/authorities/local/root.crt ./pesagem-ca.crt
curl --cacert ./pesagem-ca.crt https://localhost:8443/api/sessoes/atual
```

- **Certificado próprio.** Monte a pasta com o certificado e a chave num `compose.override.yaml` (o compose o lê sozinho) e aponte `PESAGEM_HTTPS_TLS` para os dois arquivos, separados por espaço:

```yaml
services:
  frontend:
    volumes:
      - ./certificados:/certs:ro   # o uid 10001 precisa ler os dois arquivos
```

```sh
PESAGEM_HTTPS_TLS=/certs/cert.pem /certs/chave.pem   # no .env
```

  O certificado precisa cobrir o nome de `PESAGEM_HTTPS_HOST`.
- `PESAGEM_HTTPS_HOST` (padrão `localhost`) é o nome ou IP que o navegador usa. `PESAGEM_HTTPS_PORTA` (padrão `8443`) é a porta no host. `PESAGEM_HTTPS_ENDERECO` (padrão `127.0.0.1`) é o endereço do host que recebe a porta; `0.0.0.0` abre para a rede do pátio.
- **Origem.** O `Origin` do navegador (`https://<host>:<porta>`) precisa estar em `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS`. O `.env.exemplo` já traz `https://localhost:8443`. Trocou host ou porta, troque a origem. O cookie sai com `Secure` e `SameSite=Strict` (ADR-0004).

### 4.4 Saúde

- `backend`: `GET /api/sessoes/atual` por dentro do contêiner, sem cookie. `401` é vivo (spec 025 P-1). Qualquer outra resposta, ou falha de conexão, é não saudável. Limite conhecido: o `401` não passa pelo banco, então a saúde não prova que o banco responde.
- `frontend`: `GET /` por HTTPS, sem validar o certificado (o teste é local).
- `db`: `pg_isready`.

### 4.5 Perfis (`CONVENCOES.md` §7.2)

| Perfil | Serviço | O que faz |
|---|---|---|
| (nenhum) | `db`, `migracao`, `backend`, `frontend` | Execução simulada. |
| `dev` | `db-dev` | Banco em `127.0.0.1:5432` (muda com `PESAGEM_BANCO_PORTA_DEV`), volume `pesagem-dados-db-dev`, para o backend e o `npm run dev` rodando na máquina. Use `PESAGEM_BANCO_HOST=127.0.0.1`. |
| `teste` | `db-teste` | Banco descartável em `127.0.0.1:5433`, sem volume. A suíte `pytest` não o usa: ela sobe o seu (`conftest.py`). |
| `hardware-real` | `backend-hardware-real` | **Bloqueado.** Imprime a recusa e sai com erro `1`. O modo `REAL` não existe (Q-01, Q-06) e o backend também recusa a partida. Nada de porta serial ou câmera é mapeado (R-05, Q-07). Quando existir implementação real e spec própria, o serviço ganha `devices` e as variáveis do modo `REAL`. |

Os perfis `dev` e `teste` não sobem com um `docker compose up` simples. Cada um tem volume ou armazenamento próprio, então podem rodar junto com a execução.

### 4.6 Variáveis

O `.env.exemplo` lista todas as `PESAGEM_*` que o backend lê (`config.py`, confirmadas pelo Keel em 2026-11-07), as do compose e do Caddy (`PESAGEM_HTTPS_*`, `PESAGEM_IP_PROXY`, `PESAGEM_BANCO_PORTA_DEV`), uma linha de comentário em cada. Sem segredo real: a senha do banco é um valor para trocar. `PESAGEM_GERAL_URL_BACKEND` do `frontend` é fixa no compose (`http://backend:8000`). Os modos de balança, cancelas e câmeras vêm `SIMULADO`.

Os valores de balança, LPR, tempos-limite e tempo real são **de demonstração**: saíram dos testes de integração ou foram escolhidos só para o sistema subir. Não foram calibrados (`AMBIENTE.md` §8: pendente).

A `PESAGEM_BANCO_SENHA` é lida pelo Postgres só na criação do volume. Trocá-la depois no `.env` faz o backend falhar o login no banco. Para trocar de verdade, altere a senha no banco ou recrie o volume.

## 5. Comportamento em falha

| Situação | Resultado |
|---|---|
| Sem `.env` | O `docker compose` recusa: "required variable PESAGEM_BANCO_NOME is missing a value: copie .env.exemplo para .env". |
| Variável obrigatória do backend ausente (fora as do banco) | A `migracao` passa (ela só lê o banco). O `backend` sai com `ErroConfiguracao: variável obrigatória ausente: <NOME>`, fica não saudável e o `up --wait` falha; o `frontend` não sobe. Verificado com `PESAGEM_PATIO_FUSO`. |
| Migração falha | O `backend` e o `frontend` não sobem; a saída está em `docker compose logs migracao`. |
| Backend não saudável | O `frontend` não sobe. |
| Orquestração para e o backend encerra o processo | O Docker reinicia o `backend` (§4.1); ele volta saudável e a API responde pelo proxy. Enquanto ele cai, o proxy devolve `502`. |
| Origem fora de `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS` | `403 ORIGEM_NAO_PERMITIDA` nos `POST`, `PATCH` e `DELETE`. |
| `docker compose --profile hardware-real up` | O serviço bloqueado sai com erro; nenhum dispositivo é acionado. |
| Certificado próprio ilegível pelo uid 10001 | O Caddy não inicia. |

## 6. Operação

### 6.1 Primeiro administrador

Precisa de terminal (pede a senha sem eco):

```sh
docker compose run --rm migracao python -m pesagem.api.criar_administrador
```

### 6.2 Comandos

```sh
cp .env.exemplo .env                  # troque PESAGEM_BANCO_SENHA
docker compose up -d --build --wait   # sobe e espera a saúde
docker compose logs -f backend
docker compose down                   # mantém os volumes
docker compose down -v                # APAGA banco, modelos e certificados
```

## 7. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | `docker compose config` valida; os serviços de cada perfil aparecem como na §4.5. |
| CA-002 | `docker compose up -d --wait` leva `db`, `backend` e `frontend` a saudáveis e a `migracao` a `Exited (0)`, com `alembic_version` na revisão mais recente. |
| CA-003 | Nenhuma porta do `db` nem do `backend` aparece publicada; só `127.0.0.1:8443`. |
| CA-004 | O primeiro administrador é criado com `docker compose run` em terminal. |
| CA-005 | `GET /api/sessoes/atual` por HTTPS, com a CA do Caddy, dá `401 NAO_AUTENTICADO`; sem a CA, o `curl` recusa. |
| CA-006 | `POST /api/sessoes` com `Origin` correto dá `201` e cookie `HttpOnly; SameSite=Strict; Secure`; sem `Origin`, `403 ORIGEM_NAO_PERMITIDA`; senha errada, `401 CREDENCIAIS_INVALIDAS`. |
| CA-007 | `GET /api/operacao/eventos` por HTTPS entrega o primeiro `heartbeat` na hora e o seguinte no intervalo configurado, sem acumular. |
| CA-008 | Com `PESAGEM_SEGURANCA_AUTOATENDIMENTO_REDES` fora do cliente, o autoatendimento dá `403 REDE_NAO_PERMITIDA`, mesmo com `X-Forwarded-For` forjado. Com a rede do cliente real, `200`. |
| CA-009 | Depois de `docker compose down` e `up`, o login do administrador continua valendo. |
| CA-010 | Certificado próprio via `PESAGEM_HTTPS_TLS` é o que o cliente recebe; voltando ao padrão, o emissor é a CA do Caddy. |
| CA-011 | `--profile hardware-real` sai com erro e a mensagem de bloqueio. |
| CA-012 | O volume `pesagem-modelos-ocr` está montado somente leitura no `backend`; `backend` e `frontend` rodam como uid 10001. |
| CA-013 | Com o processo do `backend` encerrado por `SIGTERM` (o mesmo sinal que o backend envia a si mesmo), o `RestartCount` sobe em 1, o contêiner volta a `running` e `healthy`, e `GET /api/sessoes/atual` pelo proxy dá `401`. |

## 8. Verificação (2026-11-07)

Docker 29.9.0, Compose 5.6.0, Fedora, imagens já em cache. CA-001 a CA-012 foram executados com saída real e passaram. Pontos de atenção:

- CA-004: o `docker compose run` precisa de um pseudoterminal. Na sessão não havia terminal, então um pequeno script em Python abriu um (`pty`) e respondeu aos quatro prompts. O administrador foi criado (`Administrador criado (id 1)`, saída 0). Em terminal normal, é só o comando da §6.1.
- CA-007: o `heartbeat` chegou às `18:53:21` e `18:53:36`, o mesmo horário do campo `enviado_em` do evento (intervalo de 15 s). Foi o canal real do backend, não um servidor de teste. Só `heartbeat` foi observado; sem operação ativa, não há outros eventos.
- CA-008: com `10.0.0.0/8`, o cliente local e o cliente com `X-Forwarded-For: 10.1.2.3` deram `403`. Com `172.28.0.1/32` (o gateway), deu `200`, o que prova que o uvicorn usou o endereço repassado pelo Caddy e não o do proxy (`172.28.0.10`).
- Porta `5432` do perfil `dev`: nesta máquina já estava ocupada por outro contêiner. O teste usou `PESAGEM_BANCO_PORTA_DEV=5434`.

**Não verificado:**

- Login e uso das telas pelo navegador. Só abri `/login` num Chromium sem interface (`--dump-dom`) e a tela de login renderizou. Não cliquei nem digitei.
- Confiança na CA do Caddy instalada no navegador ou no sistema.
- Acesso pela rede (`PESAGEM_HTTPS_ENDERECO=0.0.0.0`) de outra máquina, e o IP real do cliente nesse caso.
- Modo `REAL`, portas seriais, câmeras, GPU.
- Docker Desktop (Windows, macOS) e Podman. Só Docker no Linux.
- Build a frio das duas imagens (as camadas estavam em cache); medidas na spec 025 §6 e 026 §6.
- Teste de carga ou de queda do backend no meio de uma operação.

**CA-013 (2026-11-07, Docker 29.9.0, Compose 5.6.0):** `docker compose config` mostra `restart: unless-stopped` em `backend`, `db` e `frontend` e `'no'` na `migracao`. Com `docker compose exec backend python -c "import os,signal; os.kill(1, signal.SIGTERM)"`, o `RestartCount` foi de 1 para 2, o contêiner passou por `starting` e ficou `running healthy` em cerca de 8 s, e a API pelo proxy respondeu `401`. O encerramento disparado pelo próprio backend, quando a orquestração para, não foi provocado: o teste usou o mesmo sinal por fora. `docker compose kill backend` deixou o contêiner parado (`exited`), como esperado para parada manual.

## 9. Impacto

- **`AMBIENTE.md`:** §6.1 (Compose) e §7 (estratégia) passam a citar `compose.yaml` e os comandos da §6 desta spec; texto proposto no relato ao Maestro.
- **Specs 025 e 026:** nenhuma mudança.
- **Backend e frontend:** nenhuma mudança de código.
- **`.gitignore`:** `.env` já está ignorado.

## 10. Riscos

- **Sub-rede fixa `172.28.0.0/24`:** pode colidir com outra rede da máquina. Troque a sub-rede no `compose.yaml` e `PESAGEM_IP_PROXY` no `.env`.
- **CA interna:** o navegador avisa e o autor precisa confiar na raiz, ou usar certificado próprio (§4.3).
- **Porta aberta na rede:** com `PESAGEM_HTTPS_ENDERECO=0.0.0.0`, o login e a API ficam acessíveis na rede do pátio. A defesa é a sessão, o bloqueio de login e o firewall.
- **Caddyfile duplicado:** o `Caddyfile` da raiz repete os blocos do `Dockerfile` do frontend. Se um mudar e o outro não, a demonstração difere da imagem.
- **Valores de demonstração do `.env.exemplo`:** não servem para uma operação real.
- **Saúde do backend:** não prova que o banco responde (§4.4).

## 11. Perguntas em aberto

| # | Pergunta | Recomendação |
|---|---|---|
| P-1 | Os valores de balança, LPR e tempos do `.env.exemplo` ficam como demonstração até a calibração? | Sim. Calibração é Q-01 e a avaliação do LPR (spec 005 P-4). |
| P-2 | O download dos modelos do OCR deve virar serviço do compose? | Só quando a orquestração criar o leitor (spec 025 P-2). Hoje o modo simulado não usa o EasyOCR. |
| P-3 | Quando houver rota de saúde com banco, o `healthcheck` do backend troca? | Sim, por contrato novo (spec 025 P-1). |
