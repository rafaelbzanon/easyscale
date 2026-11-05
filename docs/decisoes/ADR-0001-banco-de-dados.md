# ADR-0001 — Banco de dados

- **Trilha:** Comum
- **Status:** Aceita
- **Data:** 2026-10-29
- **Decisão relacionada:** D-01 — `AMBIENTE.md` §13, §15
- **Tarefa:** C-201 (`specs/tarefas-iniciais.md`)
- **Aprovação:** decisão do autor em 2026-10-29 (resposta ao item 1 da C-002, registrada em `AMBIENTE.md` §0.4)

---

## 1. Contexto

- O artigo exige apenas um **banco de dados relacional** para cadastros, agendamentos, pesagens, eventos de cancela e registros do sistema **[ARTIGO §2, §4]** (RNF-004).
- O sistema tem consequências físicas e de integridade (`AGENTS.md` §7): pesagens sem duplicidade, histórico auditável, estados consistentes, escritas concorrentes (API + reconhecimento contínuo + eventos de dispositivos).
- Já existe um esquema de **referência** escrito para PostgreSQL (`docs/modelo-dados/schema.sql`, cabeçalho "PostgreSQL 12+"), derivado do banco legado. Ele usa recursos específicos do PostgreSQL: coluna gerada (`GENERATED ALWAYS AS ... STORED`), identidade (`GENERATED ALWAYS AS IDENTITY`) e índices únicos parciais (`... WHERE situacao IN (...)`). Seu status é **[PROPOSTA]**: as specs de domínio podem revisá-lo (C-002).

## 2. Critérios

Integridade e restrições; concorrência de escrita; consistência transacional; auditoria; reprodutibilidade com Docker; simplicidade de operação para protótipo; suporte no ecossistema Python; licença compatível com open-source (`AMBIENTE.md` §13.1).

## 3. Opções consideradas

| Aspecto | PostgreSQL | MySQL / MariaDB | SQLite |
|---|---|---|---|
| Integridade/restrições | Ricas; índices únicos parciais permitem regras como "uma pesagem aberta por veículo" (RN-008) e "nova pesagem só após `CANCELADA`" (RN-009) | Adequadas; sem índices parciais nativos | Básicas; tipagem flexível exige disciplina |
| Escritas concorrentes | Boas (vários escritores) | Boas | Um escritor por vez |
| Compatível com o esquema de referência | Sim (escrito para ele) | Exigiria reescrever coluna gerada, identidade e índices parciais | Exigiria reescrita e perderia garantias |
| Docker | Imagem oficial; serviço separado | Idem | Sem serviço (arquivo) |
| Complexidade operacional | Moderada | Moderada | Mínima |
| Licença | PostgreSQL License (permissiva) | MySQL: GPL + comercial (Oracle); MariaDB: GPL | Domínio público |

Análise completa: `AMBIENTE.md` §13.2–§13.3.

## 4. Decisão

**PostgreSQL** é o banco de dados do projeto.

Justificativa: atende integridade e restrições necessárias às regras de segurança (RN-008, RN-009), suporta escritas concorrentes, é compatível com o esquema de referência sem reescrita e tem reprodutibilidade simples via Docker. Coincide com a inclinação inicial do autor e com a recomendação preliminar do `AMBIENTE.md` §13.4.

## 5. Consequências

- **Testes de persistência** rodam contra PostgreSQL, o mesmo motor da execução (`AGENTS.md` §8). SQLite **não** é usado como substituto em testes de persistência.
- **Versão**: não fixada neste ADR. A versão mínima exigida pelo esquema de referência é 12 (colunas geradas). A versão da imagem Docker é definida e justificada em BE-801/INT-001. Registro de verificação: o esquema de referência foi carregado sem erro em PostgreSQL 18.6 local em 2026-10-29 (teste descartável, sem instalação no projeto); outras versões **não** foram verificadas.
- **Docker**: serviço `db` e volume `pesagem-dados-db` (`CONVENCOES.md` §7.2), criados na INT-001.
- **Configuração**: parâmetros de conexão por variáveis `PESAGEM_BANCO_*`, sem segredos no repositório (`CONVENCOES.md` §7.1).
- **Próxima decisão dependente**: ORM e ferramenta de migração (D-02, BE-501).
- **Recursos**: PostgreSQL disputa CPU/memória com o OCR se rodar na mesma máquina; avaliar quando Q-07 for respondida.
- **Esquema**: continua referência; ajustes vêm das specs (BE-201, BE-202, BE-301, BE-401) e se consolidam na spec `persistencia` (BE-502).
- **Reversibilidade**: média-baixa depois que existirem migrações e dados; alta enquanto só houver o esquema de referência.
