# Plano 016 — Esqueleto do frontend

- **Trilha:** Frontend
- **Spec:** [`spec.md`](spec.md)
- **Tarefa:** FE-102

## Tarefas

| # | Tarefa | CA |
|---|---|---|
| 1 | `package.json` com as versões exatas dos ADR-0007 e ADR-0008; `npm install` gera o `package-lock.json`. | CA-001 |
| 2 | Configuração: `tsconfig.json` (estrito, §4.1 do ADR-0008), `vite.config.ts` (plugins React e Tailwind, proxy, Vitest com jsdom), `eslint.config.js`, `.prettierrc.json`, `.prettierignore`, `index.html`. | CA-001, CA-010 |
| 3 | Tipos: `tipos/comum.ts`, `tipos/sessao.ts`, `tipos/operacao.ts` (só o necessário, spec §8.2). | CA-006 |
| 4 | `api/cliente-api.ts` com o tratamento de erro e o aviso de `401`; `api/sessao.ts` e `api/operacao.ts`. Testes. | CA-002 a CA-005 |
| 5 | Tokens em `estilos/global.css`; componentes `PlacaModo`, `AreaAcoes`, `MensagemErro`, `LayoutBase`, `LayoutTotem`. Testes. | CA-006 a CA-008 |
| 6 | Páginas de casca e rotas em `main.tsx`. | CA-008 |
| 7 | Rodar os cinco comandos e o `npm run dev` sem a variável; anexar as saídas. Busca de `localStorage`. | CA-001, CA-009, CA-010 |
| 8 | Fechamento do impeccable: detector, revisão de acabamento e `DESIGN.md`. | — |

## Estratégia de teste

- Vitest com jsdom e Testing Library (ADR-0008). `fetch` trocado por função simulada em cada teste, com respostas tipadas pelos contratos (S-6).
- Os testes verificam o que o usuário vê: texto, papel e estado desabilitado. Sem teste de detalhe de implementação.
- Sem navegador real. A verificação visual da casca usa capturas de tela, se houver navegador disponível; se não houver, o relato diz isso.
