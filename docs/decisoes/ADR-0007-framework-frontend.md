# ADR-0007 — Framework do frontend

- **Trilha:** Frontend
- **Status:** Aceita (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Decisão relacionada:** D-03 — `AMBIENTE.md` §3.2, §15
- **Tarefa:** FE-001 (`specs/tarefas-iniciais.md`)
- **Requisitos:** RF-020 a RF-024, RF-033, RNF-002, RNF-007, RNF-008, RNF-014
- **Decisão do autor:** React + Vite, com React Router; Tailwind CSS v4; TypeScript estrito (`.maestri/coordenacao.md`, D-03)

---

## 1. Contexto

- TypeScript e Tailwind CSS são **[DEFINIDO]** (`AGENTS.md` §3). O framework estava **[PENDENTE]**.
- O frontend tem dois tipos de tela:
  - telas internas, com login: cadastros, agendamentos, operação em tempo real, histórico, diagnóstico e dispositivos (`AMBIENTE.md` §10.1);
  - a tela do motorista, sem login, num totem ou na rede do pátio (RF-033).
- O tempo real usa SSE com `EventSource` e imagens buscadas por `GET` (ADR-0005). A sessão é um cookie `HttpOnly` (ADR-0004), então o frontend não guarda credencial.
- Todas as decisões de segurança ficam no backend (RNF-014). O frontend apresenta e pede ações.
- O backend é um único serviço FastAPI (ADR-0002). Não há necessidade de renderizar páginas no servidor.

## 2. Critérios

1. Funciona com TypeScript estrito e Tailwind sem adaptação.
2. Gera arquivos estáticos que qualquer servidor HTTP entrega. Nada de Node em execução.
3. Poucas dependências de execução (`AGENTS.md` §10.1).
4. Licença permissiva.
5. Manutenção ativa e documentação ampla, para quem clonar o repositório.
6. Testável sem navegador real (FE-002).

## 3. Opções consideradas

Versões e licenças consultadas no registro do npm em 2026-11-07.

| Opção | Prós | Contras | Licença |
|---|---|---|---|
| **A. React + Vite + React Router** | Ecossistema e documentação mais amplos; JSX tipado pelo próprio TypeScript; Testing Library nasceu para React; build estático com Vite. | Três dependências de execução (`react`, `react-dom`, `react-router`); exige cuidado com as regras de hooks (o lint cobre). | MIT |
| **B. Vue 3 + Vite + Vue Router** | Bom suporte a TypeScript; arquivos `.vue` concentram modelo e estilo. | A verificação de tipos dos modelos precisa de uma ferramenta a mais (`vue-tsc`); menos material em português sobre testes. | MIT |
| **C. Svelte 5 + Vite** | Pouco código por tela; pacote final pequeno. | Verificação de tipos com `svelte-check`; o roteamento costuma vir do SvelteKit, que traz servidor próprio e convenções de arquivos. | MIT |
| **D. Preact + Vite** | API parecida com a do React, em pacote menor. | Parte das bibliotecas do React precisa de camada de compatibilidade; comunidade menor. | MIT |
| **E. TypeScript sem framework + Vite** | Nenhuma dependência de execução. | Estado, roteamento e atualização da tela escritos à mão. Para a tela de operação em tempo real, isso vira um framework caseiro, sem testes de terceiros. | — |
| **F. Next.js** | Recursos prontos (rotas por arquivo, renderização no servidor). | Pede um servidor Node em execução e duplica o papel do FastAPI; desproporcional ao protótipo (ADR-0002). | MIT |

## 4. Decisão

**Opção A: React + Vite + React Router, com Tailwind CSS v4 e TypeScript estrito.**

| Peça | Papel | Versão fixada | Publicada em | Licença |
|---|---|---|---|---|
| `react`, `react-dom` | Componentes e renderização | 19.3.1 | 2026-10-14 | MIT |
| `react-router` | Rotas no navegador (modo declarativo, sem renderização no servidor) | 8.5.0 | 2026-10-19 | MIT |
| `vite` | Servidor de desenvolvimento, proxy de `/api` e build estático | 8.3.5 | 2026-10-21 | MIT |
| `@vitejs/plugin-react` | Suporte a JSX e recarga rápida no Vite | 6.1.2 | 2026-10-05 | MIT |
| `tailwindcss`, `@tailwindcss/vite` | Estilos, integrados ao Vite (v4, configuração no CSS) | 4.3.3 | 2026-07-16 | MIT |
| `typescript` | Linguagem e verificação de tipos | 6.0.3 | 2026-04-16 | Apache-2.0 |

Regra de escolha das versões: a estável mais recente publicada há pelo menos 14 dias, como na spec 001 §8. A data de corte é 2026-10-24. Duas exceções vêm de compatibilidade:

- **TypeScript 6.0.3, e não 7.0.2.** O `typescript-eslint` 8.72.0 (ADR-0008) aceita só `typescript >=4.8.4 <6.1.0`. O 6.0.3 é a última versão dentro dessa faixa.
- Pacotes com versão mais nova publicada depois do corte (`react-router` 8.5.1, `vite` 8.3.6, `tailwindcss` 4.3.5) ficam na versão anterior ao corte.

Todas as versões ficam exatas no `package.json` (`"19.3.1"`, sem `^` nem `~`), e o `package-lock.json` é versionado (ADR-0008 §4). Elas só valem depois de instaladas e com os comandos rodando na FE-102.

Requisito de ambiente: **Node 22.22.2 ou mais novo**. O `react-router` 8.5.0 pede `>=22.22.0`, e o `jsdom` 30.1.3 (ADR-0008) pede `^22.22.2`. A máquina do autor tem Node 22.22.2 e npm 10.9.7.

### 4.1 Regras de uso

- **Sem renderização no servidor.** O React Router fica no modo declarativo (`<BrowserRouter>`, `<Routes>`), sem o modo framework e sem o plugin de rotas do Vite. Assim o produto final é só HTML, CSS e JavaScript.
- **Tailwind v4 sem arquivo de configuração JS.** Os tokens do sistema de design ficam no CSS, com `@theme`, em `src/estilos/`.
- **Nenhuma biblioteca de componentes, de estado ou de requisições** neste ADR. O cliente HTTP usa `fetch`, e o tempo real usa `EventSource`, ambos nativos. Qualquer acréscimo precisa de justificativa e aprovação (`AGENTS.md` §10.1).
- **Credenciais:** nada de token, senha ou identificador de sessão em `localStorage`, `sessionStorage` ou variável global (ADR-0004). As chamadas usam o cookie com `credentials: "same-origin"`.

## 5. Consequências

- **Positivas:** um único conjunto de ferramentas (Vite) cobre desenvolvimento, proxy e build; a Testing Library e o Vitest (ADR-0008) funcionam direto com React; o produto final é estático.
- **Negativas:** três dependências de execução a manter; o TypeScript fica uma versão maior atrás (6 e não 7) até o `typescript-eslint` aceitar o 7.
- **Docker (FE-401, INT-001):**
  - desenvolvimento: imagem com Node 22.22.2 ou mais novo, rodando `vite` com o proxy de `/api` para o backend;
  - execução: o build (`frontend/dist/`) é estático. A imagem final não precisa de Node, só de um servidor de arquivos. Qual servidor, e se ele é o mesmo proxy que faz o HTTPS (ADR-0004 P-D) e desliga o buffer na rota de eventos (ADR-0005), fica para a FE-401 e a INT-001;
  - o servidor precisa devolver o `index.html` para rotas desconhecidas que não começam com `/api`, porque as rotas são do navegador.
- **Reversibilidade:** média. Trocar o React por outro framework obriga a reescrever os componentes. Os tipos da API e o cliente HTTP (`src/tipos/`, `src/api/`) não dependem do React e seriam reaproveitados.

## 6. Atualização proposta do `CONVENCOES.md` §8

O `CONVENCOES.md` é editado só pelo Maestro. Texto proposto para substituir a primeira frase e a tabela da §8:

> Framework: React + Vite + React Router, com Tailwind CSS v4 e TypeScript estrito (D-03, ADR-0007). Ferramentas: ADR-0008. Onde o React ou as ferramentas impõem um nome, ele prevalece (G-2).
>
> | Elemento | Padrão | Exemplo |
> |---|---|---|
> | Arquivo comum | `kebab-case.ts` | `cliente-api.ts`, `formatar-peso.ts` |
> | Arquivo de componente | `PascalCase.tsx` | `PainelOperacao.tsx`, `VisorRoi.tsx` |
> | Arquivo de página | `PascalCase.tsx` em `src/paginas/`, com prefixo `Pagina` | `PaginaLogin.tsx` |
> | Hook | `use` + nome em português, `camelCase` (o prefixo `use` é exigido pelo React e pelo lint) | `useSessao`, `useConexaoEventos` |
> | Variável, função | `camelCase` | `pesoLiquido`, `carregarAgendamentos()` |
> | Tipo, interface, componente | `PascalCase` | `Pesagem`, `ResultadoLeitura` |
> | Constante de módulo | `UPPER_SNAKE_CASE` | `INTERVALO_ATUALIZACAO_MS` |
> | Tipos que espelham a API | campos em `snake_case` **iguais ao JSON** (não converter) | `pesagem.peso_liquido_kg` |
> | Textos de interface | português com acentos | "Aguardando identificação" |
> | Arquivos de configuração | nome exigido pela ferramenta, na raiz de `frontend/` | `vite.config.ts`, `eslint.config.js`, `tsconfig.json` |
> | Ponto de entrada | `src/main.tsx` (convenção do Vite) | — |
>
> Converter `snake_case` ↔ `camelCase` na borda é proibido sem decisão: gera divergência entre API, banco e tela.

Na §2, a linha `frontend/  # TypeScript + Tailwind; framework [PENDENTE] D-03` passa a `frontend/  # React + Vite + Tailwind (ADR-0007)`. Na §9, a linha "Arquivo (frontend)" passa a `<arquivo>.test.ts` ou `<arquivo>.test.tsx`, ao lado do arquivo testado (ADR-0008).

Outros documentos do Maestro afetados: `AGENTS.md` §3 (tirar o framework da lista de pendentes), `AMBIENTE.md` §3.2 e §15 (D-03 decidida) e `specs/README.md` §3.
