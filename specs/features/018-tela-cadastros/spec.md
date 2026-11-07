# Spec 018 — Tela de cadastros

- **Trilha:** Frontend
- **Status:** Implementada (FE-301, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-301 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-001, RF-002, RF-003, RF-025, RF-026, RNF-013, RNF-014, RN-002
- **Decisões:** ADR-0004 (permissões; o frontend só esconde, o backend decide)
- **Contratos usados:** spec 007 inteira (rotas, campos, erros, CPF mascarado); spec 012 §5.2 (permissões da sessão)

---

## 1. Contexto e origem

- O contrato 007 define cinco cadastros: transportadoras, motoristas, tipos de veículo, veículos e produtos. Não há `DELETE`; o cadastro é só desativado (P-1).
- `ADMINISTRADOR` consulta e altera. `OPERADOR` só consulta. `AUDITOR` não tem acesso (spec 007 §4.2).
- A casca (spec 016) já fornece sessão, menu, erro e botões.

## 2. Objetivo

Uma tela para listar, criar, editar e desativar os cinco cadastros, usando só o contrato 007.

## 3. Fora de escopo

- Faixas de horário (spec 019) e usuários (spec 017).
- Importação, exclusão e consulta externa de CPF, CNPJ ou placa (spec 007 §7).
- Validar dígitos de CPF, CNPJ ou placa no navegador. Quem valida é o backend.

## 4. Atores

`ADMINISTRADOR` (lista e altera) e `OPERADOR` (só lista). O menu mostra "Cadastros" com `CONSULTAR_CADASTROS`.

## 5. Pré-condições

Sessão ativa. Rota `/cadastros`.

## 6. Comportamento normal

### 6.1 Navegação e lista

1. A tela mostra uma linha de cinco abas (um link por cadastro). A aba ativa fica no endereço (`?recurso=`); o padrão é veículos.
2. Cada cadastro mostra uma tabela com os campos principais, o filtro de situação (padrão: ativos) e, quando o contrato prevê, a busca (`busca` ou `placa`). A lista é paginada (spec 007 §3.3), com "Anterior", "Próxima" e o total.
3. A coluna "Situação" mostra palavra e forma: "Ativo" (quadrado cheio) ou "Inativo" (triângulo).
4. Veículos e motoristas mostram o nome da transportadora, do tipo e do motorista padrão, não o número. A tela busca esses cadastros para isso.
5. Motorista mostra sempre `cpf_mascarado`. A lista nunca traz o CPF completo (spec 007 §4.2).
6. Placa aparece em fonte monoespaçada.

### 6.2 Criar e editar (só com `GERENCIAR_CADASTROS`)

1. "Novo …" e "Editar" só aparecem com a permissão. Sem ela, a tela é só de consulta.
2. O formulário abre acima da tabela. Campos obrigatórios têm o aviso "obrigatório". Os campos de escolha (transportadora, tipo de veículo, motorista padrão) listam só cadastros ativos; o valor atual de um item editado continua à vista, mesmo inativo.
3. Antes de enviar, a tela só confere o que o HTML confere (obrigatório e tamanho máximo). Validade de CPF, CNPJ e placa é do backend.
4. A tela tira máscara de CPF, CNPJ e telefone antes de enviar (o contrato pede texto sem máscara), troca a vírgula por ponto em `tara_kg` e `capacidade_kg`, e manda campo opcional vazio como ausente na criação e como `null` na edição. A placa vai como digitada: o backend normaliza (spec 007 §6.1).
5. Ao editar, a tela busca o item (`GET /{recurso}/{id}`) e preenche o formulário. Só o administrador recebe o CPF completo.
6. A edição envia só os campos alterados (`PATCH`). Sem alteração, não envia nada.
7. Só depois da resposta de sucesso, a tela fecha o formulário, recarrega a lista e mostra "Salvo.".

### 6.3 Desativar

- Na edição, a caixa "Cadastro ativo" desmarcada troca o botão para "Salvar e desativar" e mostra o aviso: "Cadastro inativo não entra em novos agendamentos e não é autorizado na entrada." (spec 007 §6.2).
- Reativar usa a mesma caixa.

## 7. Comportamento em falha

| Situação | Comportamento |
|---|---|
| Carregando lista ou item | "Carregando…". Nada de lista velha com dado novo. |
| Falha ao listar | Mensagem de erro com "Tentar de novo". |
| `401 NAO_AUTENTICADO` | Casca vai ao login (spec 016). |
| `403 SEM_PERMISSAO` | "Você não tem permissão para esta ação." Nada é gravado. |
| `409` (duplicidade, operação aberta) ou `422` | O formulário continua aberto com os dados digitados. A mensagem do backend aparece no topo e os campos de `campos[]` ficam marcados. |
| `500`, rede caída, corpo inválido | Erro no formulário. A tela não supõe que salvou e não fecha o formulário. |
| Falha ao buscar os cadastros de apoio (transportadoras etc.) | Erro com "Tentar de novo"; o formulário não abre sem as opções. |
| Lista vazia | "Nenhum cadastro encontrado." |

## 8. Regras e dados

- Tipos e chamadas: `tipos/cadastros.ts` e `api/cadastros.ts` (S-6). Nenhum campo novo.
- A tela não grava nada em `localStorage`, `sessionStorage` nem cookie.
- Dados pessoais: a tela mostra só o que o contrato entrega ao perfil. O CPF completo só existe no formulário do administrador.
- Textos em português, frases curtas. Sem caixa alta em rótulo.

## 9. Critérios de aceitação

| CA | Critério | Como verificar |
|---|---|---|
| CA-001 | A tela lista o cadastro escolhido, com filtro de situação ativos por padrão, e troca de cadastro pelas abas. | Teste com `fetch` simulado. |
| CA-002 | Motorista mostra `cpf_mascarado`; o CPF completo não aparece na lista. | Teste. |
| CA-003 | Sem `GERENCIAR_CADASTROS`, não há "Novo" nem "Editar". | Teste com sessão de operador. |
| CA-004 | Criar veículo envia `POST /api/veiculos` com a placa digitada, sem os campos opcionais vazios, e só depois do sucesso mostra "Salvo." e recarrega a lista. | Teste. |
| CA-005 | Editar envia `PATCH` só com os campos alterados; sem alteração, nada é enviado. Motorista editado pelo administrador vem com o CPF completo. | Teste. |
| CA-006 | Desmarcar "Cadastro ativo" mostra o aviso e envia `ativo: false`. | Teste. |
| CA-007 | `409 CONFLITO` e `422` mantêm o formulário aberto com os dados, a mensagem do backend e o campo marcado. | Teste. |
| CA-008 | `403`, `500` e falha de rede no envio mostram erro e não fecham o formulário. | Teste. |
| CA-009 | Falha ao listar mostra erro e "Tentar de novo". | Teste. |
| CA-010 | CPF, CNPJ e telefone saem sem máscara; `tara_kg` com vírgula sai com ponto. | Teste. |
| CA-011 | Paginação: "Próxima" pede a página seguinte. | Teste. |
| CA-012 | Nenhum código grava em `localStorage`, `sessionStorage` ou `document.cookie`. | `grep`. |

## 10. Impacto

- **Pastas:** `frontend/src/paginas/cadastros/` e `frontend/src/componentes/Campo.tsx` (novos); uma linha em `rotas.tsx`. Não toca em `backend/`.
- **Segurança operacional:** nenhuma ação física. O cadastro define quem pode ser autorizado; por isso a tela avisa o efeito da desativação antes do envio.
- **Reversibilidade:** alta (arquivos novos).

## 11. Perguntas em aberto

| ID | Pergunta | Tratamento |
|---|---|---|
| Q-F3 | O contrato 007 não lista os códigos de `campos[].codigo` além de `PLACA_INVALIDA`. | A tela mostra a `mensagem` do backend, marca o campo e escreve um texto curto só para os três códigos vistos no backend real (`CAMPO_INVALIDO`, `CONFLITO`, `PLACA_INVALIDA`). Outro código: "Corrija este campo.". Pedir a lista à Quill. |
