# Spec 017 — Telas de login e de usuários

- **Trilha:** Frontend
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-308 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-031, RF-032, RN-011, RNF-013, RNF-014
- **Contrato:** spec 012 (sessão, usuários, perfis). Casca e cliente: spec 016.
- **Decisões:** ADR-0004 (sessão por cookie, nada de credencial em JavaScript)

## 1. Objetivo

Entrar no sistema e, para o administrador, criar, desativar, reativar usuários e redefinir senhas (RF-032). As outras telas dependem do login.

## 2. Fora de escopo

- Alterar nome ou perfil de um usuário, e trocar a própria senha (spec 012 P-1, P-4).
- Regra de tamanho ou composição de senha: o contrato só exige "não vazia" (012 P-3).
- Filtros na lista de usuários. Nenhum requisito pede, e são poucos usuários.
- Voltar à rota que o usuário tentava abrir antes do login: depois de entrar, vai sempre para o início.

## 3. Comportamento

### 3.1 Login (`/login`)

- Campos "Login" e "Senha", os dois obrigatórios. Botão "Entrar".
- Envia `POST /api/sessoes` com `{ login, senha }`. Em `201`, vai para `/`.
- A senha só vive no estado do formulário. Depois de qualquer resposta, o campo de senha é limpo.
- Enquanto espera a resposta, o botão fica desabilitado com o texto "Entrando…".

### 3.2 Navegação

O cabeçalho da casca ganha o menu. Cada item aparece só se a sessão tiver a permissão dele (spec 012 §5.2). Nesta tarefa, o único item é "Usuários" (`GERENCIAR_USUARIOS`). Quem decide é o backend: abrir a rota sem a permissão dá `403`, e a tela mostra a falta de permissão.

### 3.3 Usuários (`/usuarios`)

- **Lista:** `GET /api/usuarios`, paginada (spec 007 §3.3), na ordem do contrato. Colunas: nome, login, perfil, situação ("Ativo" ou "Inativo"). Com mais de uma página, botões "Anterior" e "Próxima" e o total.
- **Criar:** formulário com nome, login, perfil e senha, todos obrigatórios. Os perfis vêm de `GET /api/perfis`. Em `201`, limpa o formulário e recarrega a lista.
- **Desativar e reativar:** botão por linha. Desativar pede confirmação na própria linha, porque corta as sessões do usuário na hora (012 §6.5). Envia `PATCH` com `{ "ativo": false }` ou `{ "ativo": true }`.
- **Redefinir senha:** botão por linha, que abre na linha um campo "Nova senha" e "Confirmar". Envia `POST .../redefinir-senha` com `{ nova_senha }`. Em `204`, mostra "Senha redefinida. As sessões desse usuário foram encerradas."

Os nomes de perfil aparecem legíveis ("Administrador", "Operador", "Auditor"); um perfil novo aparece com o código (RF-031).

## 4. Comportamento em falha

| Situação | Tela |
|---|---|
| `401 CREDENCIAIS_INVALIDAS` no login | "Login ou senha incorretos." Fica na tela. Não diz qual dos dois errou (012 §6.8). |
| `429 LOGIN_BLOQUEADO` | "Login bloqueado por excesso de tentativas. Tente de novo mais tarde." |
| Outro erro no login (rede, `500`, `403 ORIGEM_NAO_PERMITIDA`) | A mensagem de erro comum da spec 016 §7. |
| `403 SEM_PERMISSAO` em `/usuarios` | "Você não tem permissão para esta ação." e nada da lista. |
| `409` com `campos[].campo` `login` na criação | Junto do campo: "Já existe um usuário com esse login." Nada é criado. |
| `422 CAMPO_INVALIDO` na criação | A mensagem do backend, e cada campo indicado em `campos` fica marcado. |
| `409 PROPRIO_USUARIO` ao desativar | "Você não pode desativar o próprio usuário." Nada muda. |
| Falha ao carregar perfis | O formulário de criação não aparece; mostra o erro com "Tentar de novo". |
| Qualquer falha numa ação | A tela não supõe que deu certo: a lista só muda depois de recarregada do backend. |
| Sessão encerrada no meio (ex.: o administrador redefiniu a própria senha) | O `401` seguinte leva ao login (spec 016). |

## 5. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | Login certo envia `{ login, senha }` e vai para o início. |
| CA-002 | `401 CREDENCIAIS_INVALIDAS` mostra "Login ou senha incorretos.", limpa a senha e não sai da tela. |
| CA-003 | `429 LOGIN_BLOQUEADO` mostra a mensagem de bloqueio. |
| CA-004 | O item "Usuários" aparece só com `GERENCIAR_USUARIOS`. |
| CA-005 | A lista mostra nome, login, perfil legível e situação de cada usuário. |
| CA-006 | Criar envia os quatro campos; `409` de login mostra a mensagem junto do campo. |
| CA-007 | Desativar só envia `PATCH { ativo: false }` depois da confirmação; `409 PROPRIO_USUARIO` mostra a mensagem. |
| CA-008 | Redefinir envia `{ nova_senha }` e, em `204`, mostra a confirmação. |
| CA-009 | `403 SEM_PERMISSAO` em `/usuarios` mostra a falta de permissão e nenhuma linha. |
| CA-010 | Nenhum código grava senha ou sessão em `localStorage`, `sessionStorage` ou `document.cookie`. |

## 6. Perguntas em aberto

Nenhuma nova. Valem as da spec 012 §11.
