# Spec 026 — Imagem Docker do frontend

- **Trilha:** Frontend
- **Status:** Implementada (FE-401, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-401 — `specs/tarefas-iniciais.md`
- **Requisitos:** RNF-004 (reprodutibilidade), RNF-013 (sem segredos)
- **Decisões:** ADR-0007 §5 (nada de Node em execução), ADR-0008 §4 (`npm ci`, dist/ estático), ADR-0004 (cookie, mesma origem), ADR-0005 (eventos sem buffer)
- **Contratos usados:** spec 016 §6.1 (rotas), §6.6 e §8.3 (`/api` na mesma origem)
- **Código:** `frontend/Dockerfile`, `frontend/.dockerignore`

---

## 1. Contexto e origem

- O ADR-0007 deixou para esta tarefa a escolha do servidor de arquivos e se ele também é o proxy de `/api` e do HTTPS.
- O cliente HTTP só chama `/api/...` na mesma origem (spec 016 §6.6). O cookie da sessão é `SameSite=Strict` e `Secure` (ADR-0004). Alguém precisa servir a tela e repassar `/api` pela mesma origem.
- O `compose.yaml` não é desta spec (INT-001, spec 027).

## 2. Objetivo

Uma imagem que serve o `dist/` com fallback para `index.html`, sem Node em execução, como usuário sem privilégios, e que também repassa `/api` ao backend. Fazendo as duas coisas, a INT-001 não precisa de um terceiro contêiner.

## 3. Fora de escopo

- `compose.yaml`, rede, porta publicada e variáveis do backend (spec 027).
- **HTTPS** (ADR-0004 P-D). A imagem fala HTTP na porta 8080. Ver §4.4.
- Imagem de desenvolvimento com `vite` (o `npm run dev` roda na máquina, `AMBIENTE.md` §6.1).
- Rodar `npm test`, `npm run lint` e `npm run typecheck` dentro do build. O build da imagem roda só `npm run build`.

## 4. Decisões

### 4.1 Build em dois estágios

1. **`node:22.22.2-alpine`**: `npm ci` a partir do `package-lock.json` e do `.npmrc`, depois `npm run build`. A versão do Node é a do ADR-0007 §4 (22.22.2 ou mais nova) e a da máquina do autor. O `.npmrc` entra porque o projeto precisa de `legacy-peer-deps` (npm 10.9.7). Este estágio não vai para a imagem final.
2. **`caddy:2.11.6-alpine`**: recebe só o `dist/` em `/srv`.

A cópia dos fontes vem depois do `npm ci`: mudar código não refaz a instalação.

### 4.2 Servidor: Caddy 2.11.6

| Critério | Escolha |
|---|---|
| Faz tudo numa peça só | Serve arquivos, repassa `/api` e, depois, faz HTTPS. Servidor só de arquivos obrigaria a INT-001 a ter outro contêiner para o proxy. |
| HTTPS | Obtém e renova certificados sozinho, inclusive com CA interna para nome local. É a forma mais curta de cumprir a P-D da demonstração. |
| Fallback de rota | `try_files {path} /index.html` (spec 016 §6.1: as rotas são do navegador). |
| Licença | Apache-2.0. |
| Tamanho | Imagem final de 94,7 MB. |
| Versão | 2.11.6. A tag foi publicada em 2026-10-04, mais de 14 dias antes de hoje. A 2.11.7 (2026-10-30) e as seguintes ficam fora do critério da spec 001 §8. Tag fixa, sem digest. |

Alternativa descartada: `nginx`. Serve igual, mas o HTTPS exigiria gerar e manter certificados à mão, e o repasse de eventos pede ajuste de buffer. Não verifiquei o `nginx` nesta spec.

### 4.3 Comportamento do servidor

O `Caddyfile` fica dentro do `Dockerfile` (a tarefa só altera esses arquivos). Escuta em `:8080` e tem a API de administração desligada (`admin off`).

| Caminho | Resposta |
|---|---|
| `/api/*` | `reverse_proxy` para `PESAGEM_GERAL_URL_BACKEND`, com `flush_interval -1` e **sem** compressão, para os eventos (SSE, ADR-0005) chegarem sem atraso. O `Origin` e o cookie passam como vieram. |
| Arquivo que existe em `/assets/` | `Cache-Control: public, max-age=31536000, immutable`. O Vite põe o hash no nome. |
| Qualquer outro caminho que não seja arquivo | `index.html`, com `200` e `Cache-Control: no-cache`. Vale para `/login`, `/operacao/123` e para um `/assets/` que não existe. |
| Arquivos estáticos | Compactados com `zstd` ou `gzip`. |

- `PESAGEM_GERAL_URL_BACKEND` é a mesma variável do proxy de desenvolvimento (spec 016 §8.3, `AMBIENTE.md` §8). **Sem valor padrão**: não inventei URL. Sem a variável, o servidor sobe, os arquivos respondem e `/api/*` dá `503`. A tela mostra "Sem resposta válida do servidor" (spec 016 §7).
- O `index.html` com `no-cache` evita que uma versão nova da tela aponte para arquivos de hash antigo.
- Um `/assets/arquivo-inexistente.js` volta como `index.html` (limite do fallback). Não ganha cache longo.

### 4.4 O que fica para a INT-001

- **HTTPS.** A imagem não faz. Para ligar, a INT-001 monta um `Caddyfile` próprio em `/etc/caddy/Caddyfile` (troca `:8080` por um nome de host) e um volume em `/data` para os certificados. **Não verificado nesta spec.** Mantenha os blocos `/api/*` e `handle` da §4.3.
- **Porta.** Publicar a `8080`. Em teste manual, só em `127.0.0.1`.
- **Origem.** O `Origin` que o navegador envia (`http://host:porta` ou `https://host`) precisa estar em `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS` no backend (spec 012 §6.9).
- **Saúde.** `GET /` devolve `200` com o `index.html`. Para o backend, vale a P-1 da spec 025.

### 4.5 Execução

- Usuário `pesagem` (uid 10001), sem privilégios. A porta 8080 não exige `root`.
- Sem Node, npm nem fontes na imagem final. Só `/srv` (`index.html` e `assets/`) e o Caddy.
- Sem segredo: nenhuma `PESAGEM_*` definida na imagem. O `.dockerignore` deixa `node_modules`, `dist`, `.env` e `.env.*` fora do contexto.
- O binário do Caddy tem a capacidade `NET_BIND_SERVICE` no arquivo. Com `cap_drop: ALL`, ele não inicia (`exec /usr/bin/caddy: operation not permitted`). Use `cap_drop: ALL` com `cap_add: NET_BIND_SERVICE`. Com isso, e com `--read-only` e `/tmp` em `tmpfs`, o contêiner subiu e respondeu.

## 5. Comportamento em falha

| Situação | Resultado |
|---|---|
| `PESAGEM_GERAL_URL_BACKEND` ausente | Arquivos respondem; `/api/*` dá `503`. |
| Backend fora do ar | `/api/*` dá `502` ou `503`; a tela trata como "sem resposta válida" (spec 016 §7). |
| `package-lock.json` fora de sincronia com o `package.json` | O `npm ci` falha e o build para. |

## 6. Medidas

Máquina do autor, Docker 29.9.0, rede doméstica, 2026-11-07. O `npm ci` baixou 250 pacotes.

| Medida | Valor |
|---|---|
| Primeiro build (`--no-cache`, baixando as duas imagens base) | 27 s |
| Build sem cache de camadas, bases já locais | 21 s |
| Build com cache, sem mudança no código | 1,5 s |
| Tamanho da imagem final | 94,7 MB (`docker image inspect`: 94 659 641 bytes) |
| `dist/` | 311 kB (`index.html` e `assets/`) |

## 7. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | `docker build frontend/` termina sem erro, com `npm ci` e `npm run build`. |
| CA-002 | A imagem final não tem `node` nem `npm`, e o processo roda como uid 10001. |
| CA-003 | `GET /` dá `200` com o `index.html` e `Cache-Control: no-cache`. |
| CA-004 | `GET /login` e `GET /operacao/123` dão `200` com o mesmo corpo do `index.html`. |
| CA-005 | Um arquivo real de `/assets/` sai com `immutable` e compactado. Um `/assets/` inexistente sai como `index.html` com `no-cache`. |
| CA-006 | Com o backend real, `GET /api/sessoes/atual` pelo servidor dá `401` com o corpo `NAO_AUTENTICADO` (spec 007 §3.2). `POST /api/sessoes` com `Origin` e JSON chega ao backend (`401 CREDENCIAIS_INVALIDAS`). |
| CA-007 | Um fluxo `text/event-stream` pela rota `/api/` chega evento a evento, sem esperar o fim. |
| CA-008 | A imagem não contém `PESAGEM_*`, `.env` nem `node_modules`. |

## 8. Verificação (2026-11-07)

Todos os critérios foram executados nesta data, com saída real, e passaram.

- CA-006: backend da spec 025 (`pesagem-backend`) e `postgres:18.6-alpine` numa rede Docker própria.
- CA-007: com um servidor de teste que emite um evento por segundo. O backend real ainda não tem rota de eventos, então a rota real de SSE não foi exercitada. Chegaram 4 eventos com 1 s de intervalo.
- Dois defeitos achados e corrigidos na verificação: o `header` sem condição substituía o `immutable` (resolvido com `?Cache-Control`), e o `file` do Caddy só enxergava os arquivos com `root` explícito dentro do matcher.

**Não verificado:** HTTPS (§4.4); o Caddy atrás de um proxy externo; navegador real abrindo a tela pelo servidor (só `curl`); o `Origin` com `https://`; digest da base; o build rodando `npm test`, `lint` e `typecheck`.

## 9. Impacto

- **Compose (spec 027):** serviço `frontend` com a imagem, `PESAGEM_GERAL_URL_BACKEND=http://backend:8000`, porta 8080, `cap_drop`/`cap_add` da §4.5 e, para HTTPS, o `Caddyfile` próprio e o volume `/data`.
- **`AMBIENTE.md` §6.1, §7 e §8:** comandos e medidas (editado pelo Maestro).
- **Frontend:** nenhuma mudança de código.

## 10. Riscos

- **O Caddy vira ponto único de entrada.** Se cair, a tela e a API saem juntas. Aceito no protótipo.
- **Tag sem digest** (§4.2).
- **Fallback devolve `200` para qualquer caminho**, inclusive arquivo inexistente. Quem consulta o status não distingue página de erro.

## 11. Perguntas em aberto

| # | Pergunta | Recomendação |
|---|---|---|
| P-1 | O HTTPS da demonstração usa certificado da CA interna do Caddy (o navegador exibe aviso até confiar nela) ou um certificado do autor? | Decidir na INT-001, junto da Q-07 (local da demonstração). A imagem funciona nos dois casos. |
