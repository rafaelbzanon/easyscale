# ADR-0008 — Ferramentas do frontend: teste, lint, formatação e tipagem

- **Trilha:** Frontend
- **Status:** Aceita (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Decisão relacionada:** D-11 (parte frontend) — `AMBIENTE.md` §15
- **Tarefa:** FE-002 (`specs/tarefas-iniciais.md`)
- **Decisão do autor:** Vitest + Testing Library, ESLint com typescript-eslint, Prettier, `tsc` estrito (`.maestri/coordenacao.md`, D-11)
- **Depende de:** ADR-0007 (React + Vite + TypeScript)

---

## 1. Contexto

- Sem ferramenta de teste não há como cumprir o `AGENTS.md` §8 nem a definição de pronto (§13).
- O backend usa pytest, ruff e mypy (ADR-0003). As ferramentas não se misturam (S-7): tudo do frontend fica em `frontend/package.json`.
- As ferramentas são **de desenvolvimento**. Nenhuma entra no build estático.
- A tela de operação tem estados de falha e bloqueio de ações (ADR-0005 §4). Os testes precisam verificar o que o usuário vê e o que fica desabilitado, sem navegador real.

## 2. Critérios

1. Atende ao requisito: testes de componentes e de lógica, lint de erros comuns, formatação uniforme, tipos estritos.
2. Menor número de dependências que cubra a necessidade (`AGENTS.md` §10.1).
3. Licença permissiva.
4. Integração direta com o Vite (ADR-0007), sem segunda configuração de build.
5. Funciona igual na máquina local, em Docker e numa CI futura.

## 3. Opções consideradas

### 3.1 Testes

| Opção | Prós | Contras | Licença |
|---|---|---|---|
| **A. Vitest + Testing Library + jsdom** | Usa a configuração do Vite; mesma sintaxe do Jest; a Testing Library testa pelo que aparece na tela (papel, nome acessível, texto). | jsdom não é um navegador completo (não tem `EventSource`, por exemplo); o teste troca essas peças por versões simuladas. | MIT |
| **B. Jest + Testing Library** | Muito conhecido. | Precisa de transformação própria para TypeScript e ESM, separada do Vite. | MIT |
| **C. Playwright (navegador real)** | Testa no navegador de verdade. | Baixa navegadores (centenas de MB); lento para testes de componente. Faz sentido para ponta a ponta (INT-002), não aqui. | Apache-2.0 |

Ambiente de DOM: jsdom e não happy-dom, porque o jsdom segue a especificação mais de perto e é o padrão da Testing Library.

### 3.2 Lint

| Opção | Prós | Contras | Licença |
|---|---|---|---|
| **A. ESLint + typescript-eslint + regras de hooks do React** | Padrão de fato; o `typescript-eslint` entende tipos; o plugin de hooks pega erros que o TypeScript não vê (hook dentro de `if`, dependência faltando). | Quatro pacotes. | MIT |
| **B. Biome (lint + formatação)** | Uma ferramenta só. | Fora da decisão do autor; regras de hooks menos completas. | MIT |
| **C. Só o `tsc`** | Nenhuma dependência a mais. | Não pega erros de uso do React. | — |

### 3.3 Formatação

**Prettier**, decisão do autor. É o formatador mais usado para TypeScript e CSS. Lint e formatação ficam separados: o ESLint não verifica estilo, então os dois não brigam.

### 3.4 Tipagem

**`tsc` em modo estrito**, sem emitir arquivos (`noEmit`). O Vite transforma o TypeScript sem verificar tipos, então o `tsc` é o único verificador.

### 3.5 Cobertura

Não adotada agora. A decisão do autor não a inclui, e a rastreabilidade é pelos `CA-` (como no ADR-0003). Se for pedida, entra `@vitest/coverage-v8`, na mesma versão do Vitest.

## 4. Decisão

Versões: a estável mais recente publicada há pelo menos 14 dias, como na spec 001 §8. Data de corte: 2026-10-24. Registro do npm consultado em 2026-11-07.

| Pacote | Papel | Versão | Publicada em | Licença |
|---|---|---|---|---|
| `vitest` | Executor de testes | 5.0.5 | 2026-10-15 | MIT |
| `jsdom` | DOM para os testes | 30.1.3 | 2026-10-15 | MIT |
| `@testing-library/react` | Renderiza componentes nos testes | 16.3.3 | 2026-08-27 | MIT |
| `@testing-library/dom` | Consultas por papel e texto (exigido pelo pacote acima) | 10.4.2 | 2026-09-13 | MIT |
| `@testing-library/jest-dom` | Verificações como `toBeDisabled` e `toHaveAccessibleName`, usadas no bloqueio de ações | 7.0.1 | 2026-08-09 | MIT |
| `@testing-library/user-event` | Simula clique e digitação como o usuário faz | 14.6.8 | 2026-10-13 | MIT |
| `eslint` | Lint | 10.13.0 | 2026-10-16 | MIT |
| `@eslint/js` | Regras recomendadas do ESLint | 10.0.1 | 2026-02-06 | MIT |
| `typescript-eslint` | Lint com informação de tipos | 8.72.0 | 2026-10-19 | MIT |
| `eslint-plugin-react-hooks` | Regras dos hooks do React | 7.1.1 | 2026-04-17 | MIT |
| `prettier` | Formatação | 3.9.10 | 2026-10-10 | MIT |
| `@types/react`, `@types/react-dom` | Tipos do React para o `tsc` | 19.3.0 | 2026-09-09 | MIT |

O `typescript` (6.0.3) já está no ADR-0007. Ele fica abaixo do 7.0.2 porque o `typescript-eslint` 8.72.0 aceita só `<6.1.0`.

Total: **13 pacotes de desenvolvimento**. As versões só valem depois de instaladas e com os comandos rodando na FE-102.

### 4.1 Regras de uso

- **Gerenciador:** npm, que vem com o Node. O `package-lock.json` é versionado e o Docker instala com `npm ci`. Isso difere do backend, que não tem lockfile (ADR-0003 P-1): no npm, as dependências indiretas são muitas e mudam sem aviso, e o lockfile é o comportamento padrão da ferramenta.
- **Versões exatas** no `package.json`, sem `^` nem `~`.
- **`legacy-peer-deps=true`** no `frontend/.npmrc` (FE-102, 2026-11-07). O npm 10.9.7 falha ao resolver os peers opcionais do Vitest e do jsdom (`Cannot read properties of null (reading 'edgesOut')`, em `#loadPeerSet`). Com a opção, o npm não instala peers sozinho; todos os peers obrigatórios estão listados no `package.json` e foram conferidos contra os `peerDependencies` de cada pacote.
- **`npm audit` (FE-102):** 10 alertas moderados, todos do mesmo `minimatch` (GHSA-g3hv-75wg-m249, negação de serviço por padrão de glob) dentro do ESLint e do typescript-eslint. Só afetam o lint, que lê padrões do próprio projeto, e não entram no build. A correção sugerida rebaixa o ESLint para a versão 9. Fica aceito até sair uma versão corrigida.
- **Configuração:** cada ferramenta no arquivo que ela exige, na raiz de `frontend/`: `vite.config.ts` (também configura o Vitest), `tsconfig.json`, `eslint.config.js` e `.prettierrc.json`.
- **TypeScript:** `strict`, mais `noUncheckedIndexedAccess`, `noImplicitOverride` e `exactOptionalPropertyTypes`. O lint recusa `any` explícito; uma exceção exige `// eslint-disable-next-line` com o motivo na mesma linha.
- **ESLint:** `@eslint/js` recomendado, `typescript-eslint` com `strictTypeChecked`, e as regras recomendadas de hooks. Nada de "todas as regras".
- **Prettier:** padrão da ferramenta, só com `printWidth: 100`. Sem plugins.
- **Testes:** ao lado do arquivo testado, com o nome `<arquivo>.test.ts` ou `<arquivo>.test.tsx`. Cada teste cita os `CA-` no nome do `describe` ou num comentário (`CONVENCOES.md` §9). O Vitest roda sem `globals`: os testes importam `describe`, `it` e `expect`.
- **Requisições nos testes:** `fetch` e `EventSource` são trocados por versões simuladas no próprio teste, com respostas tipadas pelo contrato (S-6). Nenhuma biblioteca de simulação de rede.

### 4.2 Comandos oficiais

A partir de `frontend/`. Os nomes de script são termos técnicos em inglês (`CONVENCOES.md` G-2); `test` é o nome que o npm reconhece.

| Comando | Faz |
|---|---|
| `npm ci` | Instala exatamente o que está no `package-lock.json` |
| `npm run dev` | Servidor de desenvolvimento com proxy de `/api` |
| `npm run build` | Build estático em `dist/` |
| `npm test` | Testes (`vitest run`) |
| `npm run lint` | ESLint |
| `npm run format` | Prettier em modo verificação (`prettier --check .`) |
| `npm run typecheck` | `tsc --noEmit` |

Eles só vão para o `AMBIENTE.md` §6.1 depois de executados na FE-102.

## 5. Consequências

- **Positivas:** uma única configuração (Vite) serve para build e testes; os testes verificam o que o operador vê, inclusive botões desabilitados quando a tela está desatualizada.
- **Negativas:** 13 pacotes de desenvolvimento e um lockfile grande; o TypeScript fica preso à linha 6 até o `typescript-eslint` aceitar o 7.
- **Docker (FE-401):** o estágio de build instala tudo com `npm ci` e roda os comandos; a imagem final leva só `dist/`.
- **Reversibilidade:** alta para lint e formatação (só configuração). Trocar o Vitest pelo Jest exige pouca mudança nos testes, porque a sintaxe é a mesma.

Afeta documentos do Maestro: `AGENTS.md` §8 e §10 (ferramentas do frontend deixam de ser pendentes), `AMBIENTE.md` §14 e §15 (D-11 completa) e `specs/README.md` §3.
