# Spec 012 — Contrato da API de autenticação e usuários

- **Trilha:** Contrato
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** CT-106; implementação no backend (`api/`), uso no login e na tela de usuários do frontend — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-024, RF-031, RF-032, RN-011, RN-013, RN-016, RNF-010, RNF-013, RNF-014
- **Decisões:** ADR-0004 (sessão, senha, permissões); ADR-0005 §4 item 6 (sessão no canal de eventos); spec 007 §3 (regras comuns da API)

---

## 1. Contexto e origem

- O ADR-0004 escolheu sessão guardada no banco, com cookie `HttpOnly`, senha com `hashlib.scrypt` e permissões por rota, com perfis nos dados.
- O RF-032 pede que o administrador crie e desative usuários e redefina senhas. Não há recuperação de senha por e-mail nem MFA (ADR-0004 §5).
- O `docs/modelo-dados/schema.sql` tem `usuario` com `login`, `senha_hash`, `perfil` e `ativo`. É referência **[PROPOSTA]**, e a BE-502 o ajusta a este contrato e ao ADR-0004 §5.
- Os contratos 007 a 011 dependem deste: toda rota protegida responde `401` sem sessão válida e `403` sem a permissão.

## 2. Objetivo

Definir login, logout, usuário atual com permissões, gestão de usuários, a proteção contra CSRF e a configuração de segurança, com critérios verificáveis pelos dois lados.

## 3. Fora de escopo

- Troca da própria senha pelo usuário: nenhum requisito pede (P-4).
- Recuperação de senha por e-mail e MFA (ADR-0004 §5).
- Tela e rotas para criar ou alterar perfis: os perfis são criados por migração (ADR-0004, P-A).
- Consulta da auditoria de acesso pela interface.
- Autoatendimento do motorista, sem login: CT-107 (spec 013).
- Forma de fornecer o HTTPS: INT-001.

## 4. Rotas e permissões

A forma das respostas, os erros e a paginação seguem a spec 007 §3.

### 4.1 Sessão

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `POST /api/sessoes` | Login: cria a sessão e grava o cookie (§6.1) | 201, com o usuário atual (§5.2) | Nenhuma |
| `GET /api/sessoes/atual` | Usuário da sessão e suas permissões | 200 (§5.2) | Sessão válida |
| `DELETE /api/sessoes/atual` | Logout: encerra a sessão e apaga o cookie | 204, sem corpo | Nenhuma (§6.4) |

`atual` é um segmento fixo, e não um id: o navegador não conhece o identificador da sessão, que fica só no cookie.

### 4.2 Usuários e perfis

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/usuarios` | Lista, com filtros | 200 | `GERENCIAR_USUARIOS` |
| `GET /api/usuarios/{usuario_id}` | Um item | 200 | `GERENCIAR_USUARIOS` |
| `POST /api/usuarios` | Cria | 201, com o item | `GERENCIAR_USUARIOS` |
| `PATCH /api/usuarios/{usuario_id}` | Altera só `ativo` (§6.5) | 200, com o item | `GERENCIAR_USUARIOS` |
| `POST /api/usuarios/{usuario_id}/redefinir-senha` | Troca a senha (§6.6) | 204, sem corpo | `GERENCIAR_USUARIOS` |
| `GET /api/perfis` | Perfis existentes, para escolher na criação | 200 (§5.4) | `GERENCIAR_USUARIOS` |

**Não há `DELETE` de usuário:** os registros de auditoria apontam para o responsável (RN-011).

### 4.3 Acesso por perfil

Só o `ADMINISTRADOR` tem `GERENCIAR_USUARIOS` (ADR-0004 §4.3). `OPERADOR` e `AUDITOR` usam só as rotas da §4.1.

## 5. Recursos e campos

### 5.1 Login

Corpo do `POST /api/sessoes`:

| Campo | Tipo | Obr. | Validação |
|---|---|---|---|
| `login` | texto até 50 | Sim | Não vazio. |
| `senha` | texto | Sim | Não vazio. Nunca volta em resposta nem vai para log. |

### 5.2 Usuário atual

Resposta do login e do `GET /api/sessoes/atual`:

```json
{
  "usuario": { "id": 3, "nome": "Maria Souza", "login": "maria", "perfil": "OPERADOR" },
  "permissoes": ["CONSULTAR_OPERACAO", "CRIAR_AGENDAMENTO"]
}
```

- `permissoes` traz os códigos do catálogo do ADR-0004 §4.3, em ordem alfabética, e o exemplo acima está incompleto de propósito. Serve **só** para o frontend esconder o que o usuário não pode usar. Quem decide é o backend, em toda requisição (RNF-014).
- O frontend não guarda a lista como verdade: ao receber `403`, mostra que falta permissão (ADR-0004 §5).

### 5.3 `usuarios`

| Campo | Tipo | Na criação | Validação |
|---|---|---|---|
| `id` | inteiro | Só leitura | — |
| `nome` | texto até 100 | Obrigatório | Não vazio. |
| `login` | texto até 50 | Obrigatório | Não vazio, sem espaço. Único sem diferenciar maiúsculas (P-6): `Maria` e `maria` são o mesmo login. Guardado como enviado. |
| `perfil` | texto | Obrigatório | Código de um perfil existente (§5.4). |
| `senha` | texto | Obrigatório | Só entrada; regra da §6.7. Nunca aparece na resposta. |
| `ativo` | booleano | `true` ao criar | — |
| `criado_em` | data e hora | Só leitura | — |

Nenhuma resposta traz `senha`, `senha_hash` ou dados da sessão.

Filtros: `ativo`, `perfil`, `busca` (nome ou login). Ordem: `nome`, `id`.

### 5.4 `perfis`

Não paginada, porque são poucos perfis:

```json
{ "itens": [{ "codigo": "AUDITOR", "permissoes": ["CONSULTAR_AGENDAMENTOS", "CONSULTAR_OPERACAO"] }] }
```

Ordem: `codigo`. Os perfis iniciais são `ADMINISTRADOR`, `OPERADOR` e `AUDITOR`, com as permissões do ADR-0004 §4.3.

## 6. Regras

### 6.1 Sessão e cookie (ADR-0004 §4.1)

- O login bem-sucedido sempre cria uma sessão **nova**, mesmo que o navegador já tenha uma.
- Identificador: 32 bytes de `secrets.token_urlsafe`. O banco guarda só o hash SHA-256 dele, nunca o valor.
- Cookie `pesagem_sessao`, com `HttpOnly`, `Secure`, `SameSite=Strict` e `Path=/api`. Sem `Max-Age` nem `Expires`: quem decide o fim é o servidor (§6.3). Não existe configuração para desligar o `Secure` (P-D do ADR-0004: há HTTPS).
- Um usuário pode ter várias sessões, por exemplo em dois computadores.
- O JavaScript nunca recebe o identificador: ele não aparece em nenhum corpo de resposta.

### 6.2 Verificação em cada requisição

Toda rota protegida, nesta ordem:
1. cookie ausente, sessão inexistente, encerrada ou vencida pelo tempo sem uso: `401 NAO_AUTENTICADO`;
2. usuário da sessão inativo: `401 NAO_AUTENTICADO`;
3. perfil do usuário sem a permissão da rota: `403 SEM_PERMISSAO`.

As permissões são lidas do perfil **atual** a cada requisição, e não guardadas na sessão. Uma mudança de perfil feita por migração vale na requisição seguinte.

### 6.3 Tempo sem uso

- A sessão termina quando passa `PESAGEM_SEGURANCA_SESSAO_TEMPO_SEM_USO_S` segundos sem requisição autenticada.
- Toda requisição autenticada renova o prazo, **exceto** a conexão do canal de eventos (ADR-0005): uma tela aberta só recebendo eventos não mantém a sessão viva. Se a sessão acabar, o servidor encerra a conexão de eventos (ADR-0005 §4 item 6).
- Pedidos automáticos da tela, como a imagem periódica do diagnóstico, renovam o prazo (P-5).

### 6.4 Logout

- `DELETE /api/sessoes/atual` encerra a sessão do cookie, se existir, e responde com o cookie apagado (`Max-Age=0`).
- Sem sessão válida, responde `204` do mesmo jeito: o resultado é o mesmo, e o frontend não precisa tratar erro.
- As outras sessões do mesmo usuário continuam.

### 6.5 Desativar e reativar (RF-032)

- `PATCH` aceita só `{ "ativo": false }` ou `{ "ativo": true }`. Qualquer outro campo dá `422 CAMPO_INVALIDO` (P-1).
- Desativar encerra **na hora** todas as sessões do usuário (ADR-0004 §2 critério 1). A próxima requisição dele dá `401`.
- O administrador não pode desativar a si mesmo: `409 CONFLITO` com `campos[].codigo` `PROPRIO_USUARIO`. Assim sempre resta um usuário ativo capaz de gerenciar os outros (P-2).
- Reativar não recria sessões: o usuário faz login de novo.

### 6.6 Redefinir senha (RF-032)

- Corpo: `{ "nova_senha": "..." }`, com a regra da §6.7.
- Grava o novo hash e encerra **todas** as sessões do usuário, inclusive a do próprio administrador, se ele redefinir a própria senha.
- Zera o contador de tentativas de login daquele login (§6.8).
- Vale para usuário ativo ou inativo.

### 6.7 Senha

- Não vazia. Tamanho mínimo, máximo e composição: P-3. Até a resposta, só "não vazia" é verificado.
- Hash com `hashlib.scrypt`, com estes parâmetros, gravados junto com o hash (ADR-0004 §4.1 item 5):

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `n` | 2^14 (16384) | Uma das cinco combinações equivalentes da OWASP (Password Storage Cheat Sheet, consultada em 2026-11-07): N=2^14, r=8, p=5 usa 16 MiB por cálculo. A mínima com p=1 usa 128 MiB, o que competiria com o OCR na mesma máquina (RNF-011, R-04). |
| `r` | 8 | Mesma combinação da OWASP. |
| `p` | 5 | Mesma combinação da OWASP. |
| sal | 16 bytes de `secrets`, um por usuário | A documentação do `hashlib` pede "16 ou mais bytes" de fonte adequada. |
| `dklen` | 64 | Valor padrão do `hashlib.scrypt`. |
| `maxmem` | Padrão | 16 MiB cabe no limite padrão do OpenSSL (32 MiB, pela documentação do `hashlib`); não verificado na máquina de execução (Q-07). |

- O hash guarda o algoritmo e os quatro parâmetros. Um hash com parâmetros antigos continua válido, e subir os valores no futuro não invalida as senhas existentes.
- A comparação usa `hmac.compare_digest`.
- O tempo do cálculo não foi medido. A BE mede e relata.

### 6.8 Falha de login e limite de tentativas (ADR-0004 §4.1 item 6)

- Login inexistente, senha errada e usuário inativo dão **a mesma resposta**: `401 CREDENCIAIS_INVALIDAS`, com a mesma `mensagem` e `campos` vazio.
- Para não revelar pelo tempo de resposta se o login existe, um login inexistente também passa por um cálculo scrypt com os parâmetros da §6.7.
- O contador é por texto de login, sem diferenciar maiúsculas, **exista o login ou não**. Assim o bloqueio também não revela nada.
- Depois de `PESAGEM_SEGURANCA_LOGIN_TENTATIVAS_MAXIMAS` falhas seguidas, o login fica bloqueado por `PESAGEM_SEGURANCA_LOGIN_BLOQUEIO_S` segundos.
- Durante o bloqueio, toda tentativa dá `429 LOGIN_BLOQUEADO`, **sem conferir a senha**, mesmo que esteja certa. Essas tentativas não prolongam o bloqueio.
- Um login bem-sucedido zera o contador, e o fim do bloqueio também.
- O contador sobrevive a um reinício do backend; a forma de guardar fica com a BE-502.

### 6.9 CSRF e origem (ADR-0004 §4.1 item 3)

Vale para **todas** as rotas da API, inclusive as das specs 007 a 013:

- `POST`, `PATCH` e `DELETE` precisam do cabeçalho `Origin` igual a uma das origens de `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS`. Ausente ou diferente: `403 ORIGEM_NAO_PERMITIDA`, sem efeito. Os navegadores enviam `Origin` nesses métodos, inclusive na mesma origem.
- Os mesmos métodos precisam de `Content-Type: application/json`, mesmo sem corpo útil (`{}`). Outro tipo: `415 TIPO_CONTEUDO_INVALIDO`, sem efeito. Um formulário HTML de outro site não consegue enviar JSON.
- A conferência vem **antes** da sessão e da permissão, então vale também para o login e o logout.
- `GET` não muda estado e não passa por essa conferência.

### 6.10 Primeiro administrador (ADR-0004 §4.1 item 7)

- Um comando de linha de comando do backend, executado na instalação. O nome do comando fica com a BE.
- Pede nome, login e senha, esta duas vezes e sem eco na tela. Não aceita a senha por argumento nem por variável de ambiente, para ela não ficar no histórico do terminal.
- Cria um usuário com o perfil `ADMINISTRADOR`. Só funciona se **não houver** usuário ativo com esse perfil; caso contrário, termina com erro e não cria nada (P-7).
- Login repetido, senha vazia ou as duas senhas diferentes: termina com erro, sem criar nada.
- Nenhuma senha padrão existe no código, no repositório ou nas migrações.

### 6.11 Auditoria (RN-011, RNF-010)

Ficam registrados, com instante: login aceito, login recusado, login bloqueado, logout, criação de usuário, desativação, reativação e redefinição de senha, com o responsável e o usuário afetado.

- Nunca registrar a senha, o identificador da sessão nem o cookie.
- Em login recusado de login **inexistente**, não registrar o texto digitado: muitas vezes é uma senha digitada no campo errado. Registra-se só que o login não existe.
- Login recusado de login existente registra o `usuario_id`.

### 6.12 Configuração

Todas obrigatórias, **sem valor padrão** no código. Se faltar uma ou o valor for inválido, o backend não inicia, com mensagem clara (`AMBIENTE.md` §8).

| Variável | Conteúdo | Validação |
|---|---|---|
| `PESAGEM_SEGURANCA_ORIGENS_PERMITIDAS` | Origens aceitas, separadas por vírgula, no formato `https://host[:porta]` | Ao menos uma; cada uma com esquema e host, sem caminho. |
| `PESAGEM_SEGURANCA_SESSAO_TEMPO_SEM_USO_S` | Tempo sem uso que encerra a sessão, em segundos | Inteiro > 0. |
| `PESAGEM_SEGURANCA_LOGIN_TENTATIVAS_MAXIMAS` | Falhas seguidas que bloqueiam o login | Inteiro > 0. |
| `PESAGEM_SEGURANCA_LOGIN_BLOQUEIO_S` | Duração do bloqueio, em segundos | Inteiro > 0. |

Os valores vão no `.env.exemplo` como espaço a preencher, sem número sugerido.

### 6.13 Falhas

| Situação | Resposta |
|---|---|
| Banco indisponível no login ou na verificação da sessão | `500 ERRO_INTERNO`. Nenhuma sessão é criada nem considerada válida: na dúvida, sem acesso. |
| Dois `POST /api/usuarios` com o mesmo login | Um recebe `201`, o outro `409 CONFLITO` com `campos` `[{ "campo": "login", "codigo": "CONFLITO" }]`, garantido pela unicidade no banco. |
| `perfil` inexistente na criação | `422 CAMPO_INVALIDO`, com o campo indicado. |
| Corpo com campo desconhecido ou somente leitura | `422 CAMPO_INVALIDO`. |
| Sessão encerrada durante uma operação física | A operação continua; só as ações manuais ficam indisponíveis até novo login (ADR-0004 §4.1). |
| Tempo de resposta | Sem número definido; não há dado para isso. |

### 6.14 Códigos novos

| Status | `codigo` | Quando |
|---|---|---|
| 401 | `CREDENCIAIS_INVALIDAS` | Login recusado (§6.8). |
| 429 | `LOGIN_BLOQUEADO` | Login bloqueado (§6.8). |
| 403 | `ORIGEM_NAO_PERMITIDA` | `Origin` ausente ou fora da lista (§6.9). |
| 415 | `TIPO_CONTEUDO_INVALIDO` | Método que muda estado sem JSON (§6.9). |

Em `campos[].codigo`: `PROPRIO_USUARIO` (§6.5), além dos códigos comuns da spec 007.

## 7. Dados pessoais

- Nome e login dos usuários só aparecem para quem tem `GERENCIAR_USUARIOS` e na própria sessão.
- Os registros de acesso não gravam a query string (spec 007 §3.4), o corpo do login nem o cabeçalho `Cookie`.

## 8. Critérios de aceitação

Verificáveis no backend (testes de API) e no frontend (respostas simuladas com estes tipos, S-6). Os testes do backend usam URL `https`, porque o cookie é `Secure`.

| CA | Critério |
|---|---|
| CA-001 | Login certo dá `201` com o corpo da §5.2 e grava o cookie `pesagem_sessao` com `HttpOnly`, `Secure`, `SameSite=Strict` e `Path=/api`; nenhum corpo de resposta contém o identificador. |
| CA-002 | Login inexistente, senha errada e usuário inativo dão a mesma resposta `401 CREDENCIAIS_INVALIDAS`, com corpo idêntico. |
| CA-003 | Depois do número configurado de falhas seguidas, o login dá `429 LOGIN_BLOQUEADO`, inclusive com a senha certa; um login inexistente é bloqueado do mesmo jeito; depois do tempo configurado, o login volta a funcionar. |
| CA-004 | Um login bem-sucedido zera o contador de falhas. |
| CA-005 | `GET /api/sessoes/atual` sem cookie, com cookie desconhecido ou depois do logout dá `401`. |
| CA-006 | Sem requisição por mais que o tempo sem uso configurado, a próxima dá `401`; uma requisição antes do prazo o renova. |
| CA-007 | Desativar um usuário faz a próxima requisição de qualquer sessão dele dar `401`, sem esperar o tempo sem uso. |
| CA-008 | Redefinir a senha encerra todas as sessões do usuário; a senha antiga passa a dar `401 CREDENCIAIS_INVALIDAS`, e a nova funciona. |
| CA-009 | O administrador que tenta se desativar recebe `409` com `PROPRIO_USUARIO`, e nada muda. |
| CA-010 | `OPERADOR` e `AUDITOR` recebem `403` em todas as rotas da §4.2. |
| CA-011 | A lista de `permissoes` corresponde ao perfil do ADR-0004 §4.3, e uma mudança no perfil vale na requisição seguinte, sem novo login. |
| CA-012 | Nenhuma resposta contém `senha` ou `senha_hash`; o hash gravado não contém a senha e registra o algoritmo e os parâmetros da §6.7. |
| CA-013 | `POST`, `PATCH` e `DELETE` sem `Origin` ou com origem fora da lista dão `403 ORIGEM_NAO_PERMITIDA`, sem efeito, inclusive no login. |
| CA-014 | `POST` com `Content-Type` diferente de JSON dá `415 TIPO_CONTEUDO_INVALIDO`, sem efeito. |
| CA-015 | Criar um usuário com login igual a outro, só mudando maiúsculas, dá `409`; dois pedidos simultâneos resultam em um `201` e um `409`. |
| CA-016 | `PATCH` com campo diferente de `ativo` dá `422`. |
| CA-017 | Logout sem sessão dá `204` e apaga o cookie; logout com sessão encerra só aquela sessão. |
| CA-018 | Sem qualquer variável da §6.12, ou com valor inválido, o backend não inicia. |
| CA-019 | O comando do primeiro administrador cria o usuário quando não há administrador ativo e recusa quando há; não aceita senha por argumento. |
| CA-020 | Logs e auditoria não contêm a senha, o identificador da sessão, o cookie nem o texto de um login inexistente. |
| CA-021 | O frontend volta à tela de login ao receber `401` e mostra falta de permissão ao receber `403`, sem guardar credencial em JavaScript. |

## 9. Impacto

- **Backend (`api/`):** sessão, verificação por rota, conferência de origem e tipo de conteúdo para toda a API, rotas desta spec e o comando do primeiro administrador. Nenhuma dependência nova (`hashlib`, `secrets`, `hmac`).
- **Frontend:** tela de login, guarda das rotas pela lista de permissões, tela de usuários. O cliente HTTP envia sempre `Content-Type: application/json` nos métodos que mudam estado.
- **Esquema (BE-502), sem alterar agora:** tabelas `sessao`, `perfil` e `perfil_permissao` (ADR-0004 §5); unicidade de `usuario.login` sem diferenciar maiúsculas; o contador de tentativas de login guardado no banco; registros de auditoria da §6.11.
- **Specs 007 a 013:** a §6.9 vale para todas, e os códigos `401`, `403`, `415` e `429` desta spec podem aparecer em qualquer rota que muda estado.
- **Glossário:** termos novos `perfil`, `usuario`, `login`. Texto para o Maestro incluir em `CONVENCOES.md` §10: "Perfil de acesso | `perfil` | `role`"; "Usuário do sistema | `usuario` | `user`".
- **Configuração:** quatro variáveis novas no grupo `SEGURANCA` (§6.12).
- **Segurança operacional:** nenhuma ação física. O efeito é indireto: as ações manuais e as liberações dependem de sessão válida, e o corte de acesso é imediato.
- **Reversibilidade:** alta, sem código ainda.

## 10. Riscos conhecidos

- **Bloqueio por terceiros:** quem conhece um login pode bloqueá-lo errando a senha de propósito. É o custo de limitar por login (ADR-0004). O bloqueio dura só o tempo configurado.
- **Senha conhecida pelo administrador:** sem troca da própria senha (P-4), o administrador sabe a senha de todos os usuários que criou ou redefiniu.
- **Tela de diagnóstico aberta:** pela §6.3, os pedidos automáticos de imagem mantêm a sessão viva enquanto a tela estiver aberta (P-5).

## 11. Perguntas em aberto

| ID | Pergunta | Situação até a resposta |
|---|---|---|
| P-1 | O administrador pode alterar o nome e o perfil de um usuário? O RF-032 só fala em criar, desativar e redefinir a senha. | Fora: `PATCH` aceita só `ativo`. A reativação foi incluída por ser o desfazer da desativação. |
| P-2 | O administrador pode desativar a si mesmo? | Recusado (`409`), para nunca ficar sem administrador ativo. |
| P-3 | Há regra de tamanho mínimo, máximo ou composição da senha? | Só "não vazia". Nenhum número foi inventado. |
| P-4 | O usuário pode trocar a própria senha? Nenhum requisito pede. | Fora de escopo. Só o administrador redefine. |
| P-5 | Pedidos automáticos da tela, como a imagem periódica do diagnóstico, devem contar como uso? | Contam (§6.3). Distinguir exigiria marcar cada pedido no frontend. |
| P-6 | O login diferencia maiúsculas? | Não: único e comparado sem diferenciar maiúsculas, para o mesmo nome não virar dois usuários nem dois contadores de tentativa. |
| P-7 | O comando do primeiro administrador serve também para recuperar o acesso quando há administrador ativo mas ninguém sabe a senha? | Não: só funciona sem administrador ativo. A recuperação nesse caso fica sem caminho até a resposta. |
