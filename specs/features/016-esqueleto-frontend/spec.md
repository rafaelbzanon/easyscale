# Spec 016 — Esqueleto do frontend

- **Trilha:** Frontend
- **Status:** Implementada (FE-102, 2026-11-07; aprovação delegada, revisão final do autor pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-101 (spec e plano), FE-102 (implementação) — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-023 (modo visível), RNF-002, RNF-008, RNF-013, RNF-014
- **Decisões:** ADR-0004 (sessão por cookie, `401` e `403`), ADR-0005 (tela desatualizada), ADR-0007 (framework), ADR-0008 (ferramentas)
- **Contratos usados:** spec 007 §3 (formato de erro), spec 009 §5.4 e §5.5 (modo dos dispositivos), spec 012 §4.1, §5.2 e §6.9 (sessão e CSRF)
- **Direção visual:** `frontend/PRODUCT.md` e o surface brief em `frontend/.impeccable/surfaces/`
- **Plano:** [`plano.md`](plano.md)

---

## 1. Contexto e origem

- As telas (FE-301 a FE-308) precisam de um lugar para o código, de um cliente HTTP que siga os contratos e de comandos de build e teste funcionando (`AGENTS.md` §8).
- O framework e as ferramentas estão decididos (ADR-0007, ADR-0008).
- O `AMBIENTE.md` §10.1 item 7 pede indicação visível do modo real ou simulado. O ADR-0005 pede aviso claro e bloqueio de ações quando a tela fica desatualizada.
- O ADR-0004 §5 define o comportamento do frontend: não guarda credencial, volta ao login no `401` e mostra falta de permissão no `403`.

## 2. Objetivo

Criar o mínimo para começar as telas: a estrutura de pastas, a casca visual comum (telas internas e totem), o cliente HTTP, o indicador de modo, o componente de bloqueio por tela desatualizada e o proxy de desenvolvimento. Todos os comandos do ADR-0008 devem rodar sem erro.

## 3. Fora de escopo

- Telas de negócio: login, cadastros, agendamentos, operação, histórico, diagnóstico, autoatendimento (FE-301 a FE-308). As rotas `/login` e `/autoatendimento` existem só como casca, com um texto dizendo qual tarefa as completa.
- Canal de eventos SSE e o cálculo de "desatualizada" pelo `heartbeat`: ficam na FE-303. Esta spec entrega só o componente que bloqueia as ações quando recebe esse estado.
- Navegação entre telas: o menu entra quando a primeira tela existir. Sem itens que levam a telas inexistentes.
- Tipos dos contratos 007 a 013, além dos usados aqui: FE-201.
- `Dockerfile` (FE-401) e `compose.yaml` (INT-001).

## 4. Atores

Quem desenvolve, e os usuários finais só pela casca: operador, administrador e auditor nas telas internas; motorista no totem.

## 5. Pré-condições

- Node 22.22.2 ou mais novo e npm (ADR-0007 §4).
- Para `npm run dev`: a variável `PESAGEM_GERAL_URL_BACKEND` com a URL do backend (§8.3).

## 6. Comportamento normal

### 6.1 Rotas

| Rota | Casca | Sessão |
|---|---|---|
| `/login` | Telas internas, sem cabeçalho de usuário | Não exige |
| `/autoatendimento` | Totem | Não exige (ADR-0004 §4.4) |
| `/` e demais | Telas internas | Exige: consulta `GET /api/sessoes/atual` ao abrir |
| Rota desconhecida | Telas internas | Mostra "Página não encontrada" |

### 6.2 Casca das telas internas

1. Ao abrir uma rota protegida, a casca consulta `GET /api/sessoes/atual` e mostra "Carregando…" até a resposta. Só depois mostra o conteúdo.
2. O cabeçalho mostra "EasyScale", a placa de modo (§6.4), o nome do usuário e o botão "Sair".
3. "Sair" envia `DELETE /api/sessoes/atual` e vai para `/login`, com qualquer resposta (spec 012 §6.4).
4. As permissões da sessão servem só para esconder o que o usuário não pode usar (spec 012 §5.2). Quem decide é o backend.

### 6.3 Casca do totem

Tela cheia, sem cabeçalho de usuário e sem placa de modo (o motorista não tem sessão e não pode consultar o estado). Alvos de toque grandes (§8.4). O conteúdo entra na FE-307.

### 6.4 Placa de modo

- Fonte: `dispositivos` em `GET /api/operacao/estado` (spec 009 §5.5), que exige `CONSULTAR_OPERACAO`. Os quatro campos `modo` são os de `balanca`, `cancelas[]`, `posicao` e `identificacao`.
- A casca consulta o estado ao abrir e a cada mudança de rota. O modo muda só com reinício do backend, e a FE-303 o mantém atualizado pelos eventos.

| Situação | Placa |
|---|---|
| Todos os `modo` são `SIMULADO` | "SIMULADO · nenhum equipamento físico" |
| Algum `modo` é `REAL` | "REAL · equipamento físico: " e a lista dos dispositivos em `REAL` (ex.: "balança, cancela de entrada") |
| Sem `CONSULTAR_OPERACAO`, erro na consulta, resposta ainda não chegou ou campo ausente | "MODO DESCONHECIDO" |

Em dúvida, a placa diz desconhecido. Ela nunca mostra `SIMULADO` sem ter lido os quatro campos.

### 6.5 Área de ações bloqueável

Componente que envolve os botões de ação de uma tela. Recebe `bloqueada`. Com `bloqueada` verdadeiro, todos os controles dentro dele ficam desabilitados e aparece a faixa zebrada com o texto "Tela desatualizada. Ações bloqueadas até reconectar." Com falso, a faixa some e os controles voltam. Quem calcula o estado é a tela (FE-303, spec 009 §6.2).

### 6.6 Cliente HTTP

- Toda chamada vai para `/api/...` na mesma origem, com `credentials: "same-origin"`. Nada de token, senha ou identificador de sessão em `localStorage`, `sessionStorage` ou variável global (ADR-0004).
- `POST`, `PATCH` e `DELETE` sempre enviam `Content-Type: application/json` e corpo JSON, `{}` quando não há corpo útil (spec 012 §6.9). O navegador envia o `Origin` sozinho.
- Resposta `2xx`: devolve o JSON; `204` devolve vazio.
- Resposta de erro com o corpo da spec 007 §3.2: lança um erro com o `status` e o objeto `erro` (`codigo`, `mensagem`, `campos`). As telas decidem pelo `codigo`, nunca pelo texto.

## 7. Comportamento em falha

| Situação | Comportamento esperado |
|---|---|
| `401` com `codigo` `NAO_AUTENTICADO` em qualquer chamada | Vai para `/login`. Nenhuma tela supõe que a ação deu certo. |
| `401` com outro `codigo` (ex.: `CREDENCIAIS_INVALIDAS` no login) | Lança o erro para a tela tratar. Não redireciona. |
| `403` com `codigo` `SEM_PERMISSAO` | A tela mostra "Você não tem permissão para esta ação." O backend decide; a tela não tenta de novo. |
| `403 ORIGEM_NAO_PERMITIDA` ou `415 TIPO_CONTEUDO_INVALIDO` | Erro de configuração. Mostra a `mensagem` do backend como erro genérico. Não é tratado como falta de permissão. |
| Corpo de erro fora do formato (ex.: página HTML de um proxy) | Lança erro com `status` e `erro` nulo. A tela mostra "Sem resposta válida do servidor." |
| Rede caída ou backend fora (`fetch` falha) | Lança erro com `status` 0 e `erro` nulo. Mesma mensagem. Nada é dado como salvo. |
| `GET /api/operacao/estado` falha ou demora | Placa "MODO DESCONHECIDO". |
| `GET /api/sessoes/atual` falha sem ser `401` | A casca mostra o erro e o botão "Tentar de novo". Não mostra o conteúdo protegido. |
| `npm run dev` sem `PESAGEM_GERAL_URL_BACKEND` | O servidor de desenvolvimento não inicia e a mensagem nomeia a variável. Sem URL padrão inventada. |

## 8. Regras e dados

### 8.1 Estrutura (`CONVENCOES.md` §2 e §8)

```
frontend/
├── package.json, package-lock.json, .npmrc, vite.config.ts, tsconfig.json,
│   eslint.config.js, .prettierrc.json, .prettierignore, .gitignore, index.html
├── PRODUCT.md                      # produto, para o impeccable
├── DESIGN.md                       # sistema de design, escrito no fim da FE-102
└── src/
    ├── main.tsx                    # ponto de entrada
    ├── rotas.tsx                   # rotas, separadas para os testes
    ├── configuracao-testes.ts      # jest-dom e limpeza entre testes
    ├── paginas/                    # PaginaLogin, PaginaInicio, PaginaTotem, PaginaNaoEncontrada (cascas)
    ├── componentes/                # LayoutBase, LayoutTotem, Cabecalho, PlacaModo, AreaAcoes,
    │                               # MensagemErro, Botao, SimboloEstado
    ├── api/                        # cliente-api.ts, sessao.ts, operacao.ts
    ├── tipos/                      # comum.ts (spec 007 §3), sessao.ts (012), operacao.ts (009)
    └── estilos/                    # global.css com os tokens (@theme)
```

Os testes ficam ao lado do arquivo testado (ADR-0008 §4.1). Nenhuma pasta vazia.

### 8.2 Tipos

Espelham o contrato, com campos em `snake_case` (S-6). Nesta tarefa, só os usados aqui: o erro e a lista da spec 007 §3, o usuário atual da spec 012 §5.2 e o `modo` dos dispositivos da spec 009 §5.4. O resto entra na FE-201.

### 8.3 Proxy de desenvolvimento

- O `vite.config.ts` repassa `/api` para `PESAGEM_GERAL_URL_BACKEND`, sem buffer, para o SSE funcionar.
- O proxy não troca o `Origin`. Em desenvolvimento, a origem do navegador (ex.: `http://localhost:5173`) precisa estar em `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS` no backend (spec 012 §6.9).
- O cookie da sessão é `Secure` (spec 012 §6.1). Os navegadores aceitam cookie `Secure` em `http://localhost`, mas isso não foi verificado com o backend, que ainda não existe.

### 8.4 Sistema de design

A direção é a sinalização de segurança do pátio (surface brief). Na casca:

- Cor só com função. Vermelho: falha e `REAL`. Amarelo: atenção e desconhecido. Verde: ok. Azul: só a ação disponível agora e o modo `SIMULADO`. Fundo concreto claro, texto quase preto, cabeçalho asfalto com a faixa amarela embaixo.
- Estado nunca só por cor: sempre palavra e forma (triângulo de atenção, círculo de falha, quadrado de ok).
- Fonte do sistema, sem dependência nova; números tabulares; placa de veículo sempre em fonte monoespaçada.
- Fios de 1px, sem sombra. Contraste mínimo WCAG AA.
- Totem: alvos de toque de pelo menos 64 px de altura e texto base maior.
- O zebrado aparece só no bloqueio da §6.5.

## 9. Critérios de aceitação

| CA | Critério | Como verificar |
|---|---|---|
| CA-001 | `npm run build`, `npm test`, `npm run lint`, `npm run format` e `npm run typecheck` terminam sem erro. | Executar e anexar a saída. |
| CA-002 | O cliente envia `Content-Type: application/json` e corpo `{}` em `POST`, `PATCH` e `DELETE` sem corpo, e `credentials: "same-origin"` em todas. | Teste com `fetch` simulado. |
| CA-003 | `401 NAO_AUTENTICADO` chama o redirecionamento para o login; `401 CREDENCIAIS_INVALIDAS` não chama. | Teste. |
| CA-004 | `403 SEM_PERMISSAO` vira erro com o `codigo`, e a mensagem de falta de permissão aparece. | Teste. |
| CA-005 | Corpo de erro fora do formato e falha de rede viram erro com `erro` nulo (status do servidor ou 0). | Teste. |
| CA-006 | Placa de modo: todos `SIMULADO` mostra simulado; um `REAL` mostra real com a lista; falha, ausência ou campo faltando mostra desconhecido. | Teste com respostas tipadas pela spec 009. |
| CA-007 | Área de ações bloqueada: todos os botões ficam desabilitados e a faixa aparece; desbloqueada, voltam. | Teste com `toBeDisabled`. |
| CA-008 | Rota protegida sem sessão (`401` em `/api/sessoes/atual`) vai para `/login`, sem mostrar o conteúdo. | Teste. |
| CA-009 | Nenhum código grava em `localStorage`, `sessionStorage` ou `document.cookie`. | Busca no código (`grep`) no relato. |
| CA-010 | `npm run dev` sem `PESAGEM_GERAL_URL_BACKEND` não inicia e nomeia a variável. | Executar e anexar a saída. |

## 10. Impacto

- **Pastas:** cria `frontend/`. Não toca em `backend/`.
- **Documentos do Maestro:** registrar os comandos executados no `AMBIENTE.md` §6.1; incluir `PESAGEM_GERAL_URL_BACKEND` no `AMBIENTE.md` §8 e no `.env.exemplo` (trilha E); `specs/README.md` §2.
- **Integração (INT-001):** em desenvolvimento, a origem do frontend entra em `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS`.
- **Segurança operacional:** o frontend não decide nada. A placa de modo e o bloqueio reduzem o risco de o operador agir achando que está em simulação, ou olhando dados velhos.
- **Reversibilidade:** alta. São só arquivos novos.

## 11. Perguntas em aberto

| ID | Pergunta | Tratamento até a resposta |
|---|---|---|
| Q-F1 | Qual o tamanho e a resolução da tela do totem? | Casca responsiva, testada em 1080×1920 retrato e 1920×1080 paisagem. |
| Q-F2 | O totem deve mostrar o modo `REAL`/`SIMULADO`? O contrato 013 não dá esse dado sem sessão. | Não mostra. Se precisar, pedir uma CT-9xx. |
