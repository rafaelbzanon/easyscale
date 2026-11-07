# ADR-0006 — Acesso ao banco e migrações

- **Trilha:** Backend
- **Status:** Aceita (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Decisão relacionada:** D-02 — `AMBIENTE.md` §15
- **Tarefa:** BE-501 (`specs/tarefas-iniciais.md`)
- **Aprovação:** o autor escolheu SQLAlchemy 2 (psycopg 3) + Alembic em 2026-11-07 (`.maestri/coordenacao.md` §1, D-02). Este ADR registra a escolha e os detalhes.

---

## 1. Contexto

- O banco é PostgreSQL (ADR-0001). Os testes de persistência rodam contra ele, nunca contra SQLite (`AGENTS.md` §8).
- As regras de concorrência precisam de transação e de restrições no banco: `versao` da operação, reserva da balança, uma operação aberta por placa, um agendamento aberto por veículo e vaga da faixa (spec 006 §7.3, spec 008 §6.2 e §6.4).
- Os dispositivos são assíncronos, e o LPR roda em `asyncio.to_thread` (D-05). A API é FastAPI.
- O domínio já tem tipos próprios, imutáveis e sem I/O (`dominio/`, P-4 e P-5).
- Falta ferramenta de migração. Até ela existir, o `docs/modelo-dados/schema.sql` é a referência (P-10).

## 2. Opções

### 2.1 Acesso ao banco

| Opção | Prós | Contras |
|---|---|---|
| **SQLAlchemy 2 + psycopg 3** (escolha do autor) | Padrão no ecossistema Python; transações, pool e SQL explícito; usado pelo Alembic. | Uma biblioteca grande. |
| psycopg 3 sozinho | Menos uma dependência. | Pool, transações e migrações ficam por nossa conta; o Alembic exige SQLAlchemy de qualquer forma. |
| SQLModel, Django ORM, Tortoise | Modelos prontos. | Acoplam a validação ou o framework; mais peças. |

### 2.2 Migrações

| Opção | Prós | Contras |
|---|---|---|
| **Alembic** (escolha do autor) | Feito para o SQLAlchemy; versões em arquivos Python revisáveis; configuração no `pyproject.toml`. | — |
| SQL solto aplicado à mão | Nada a instalar. | Sem controle de versão aplicada; erro humano na execução. |

### 2.3 Síncrono ou assíncrono

| Opção | Prós | Contras |
|---|---|---|
| **A. Síncrono, chamado em `asyncio.to_thread`** | Mesmo padrão do LPR (D-05); sem `greenlet`; testes sem plugin assíncrono; a transação é curta e nunca atravessa um comando físico, porque a situação é gravada **antes** do comando (spec 006 §7.2). | Uma thread por chamada ao banco; irrelevante na escala de uma balança (Q-12). |
| B. Assíncrono (`sqlalchemy.ext.asyncio`) | Sem troca de thread. | Exige `greenlet` (dependência nova, com extensão em C); erros de "I/O implícito" difíceis de achar; ganho nulo nesta escala. |

## 3. Decisão

1. **SQLAlchemy 2 Core, síncrono, com psycopg 3.** Os repositórios usam `Connection` e SQL explícito. Não há mapeamento ORM: o domínio já tem os seus tipos, e o SQL explícito deixa visíveis os bloqueios (`FOR UPDATE`) e as condições de concorrência. A orquestração e a API chamam os repositórios com `asyncio.to_thread` (opção A).
2. **Alembic** para as migrações, configurado em `[tool.alembic]` do `backend/pyproject.toml`, sem `alembic.ini`.
3. **As migrações são a única fonte do esquema.** Cada uma é escrita à mão em SQL (`op.execute`), revisável como o `schema.sql`. Não há `autogenerate` nem um segundo modelo das tabelas no código, para não duplicar o esquema (P-10). O `docs/modelo-dados/schema.sql` passa a ser histórico (spec 014).
4. **Local das migrações:** `backend/src/pesagem/persistencia/migracoes/`, com arquivos `NNNN_descricao_snake.py` (`CONVENCOES.md` §6). Ficam dentro do pacote para irem junto com o código na imagem do backend.

### 3.1 Versões

Critério da spec 001 §8: a estável mais recente publicada há pelo menos 14 dias. Hoje é 2026-11-07, então o limite é 2026-10-24. Consultadas no PyPI e no `postgresql.org` nesta data.

| Item | Versão | Publicada em | Licença | Motivo |
|---|---|---|---|---|
| SQLAlchemy | 2.1.6 | 2026-10-21 | MIT | A 2.1.7 e a 2.1.8 têm menos de 14 dias. A série 2.1 é estável desde 2026-09-24. Tem pacote para Python 3.14. |
| psycopg (`psycopg[binary]`) | 3.3.6 | 2026-09-18 | LGPL-3.0 | A 3.3.7 e a 3.3.8 têm menos de 14 dias. O pacote `binary` traz a `libpq`, sem compilar nada; tem pacote para Python 3.14. |
| Alembic | 1.20.1 | 2026-10-22 | MIT | Mais recente dentro do limite; lê a configuração do `pyproject.toml`. |
| Imagem PostgreSQL | `postgres:18.6-alpine` | 18.6 lançada em 2026-08-13 | PostgreSQL License | A 18 é a versão principal mais recente (a 19 ainda não saiu). A 18.6 é a correção mais recente, e o esquema de referência já carregou nela (ADR-0001). `alpine` por ser menor. |

As três bibliotecas vão para `[project] dependencies` (execução), não para um grupo, porque a aplicação precisa delas para rodar. A LGPL do psycopg é compatível com o projeto: ele é usado como biblioteca, sem alteração.

A mesma imagem vale para os testes e para a execução. A INT-001 usa a mesma tag no `compose.yaml`; trocar a versão exige rodar de novo os testes de persistência.

## 4. Consequências

- **Código:** `persistencia/` (conexão, transação, repositórios e migrações) e `config.py` com `PESAGEM_BANCO_*` (BE-503). Só `persistencia/` importa `sqlalchemy` e `psycopg`; o teste de camadas passa a verificar isso.
- **Testes:** integração em `backend/tests/integracao/`, contra um contêiner `postgres:18.6-alpine` criado pelo próprio teste. Sem Docker, esses testes falham com mensagem clara; não são pulados em silêncio.
- **Erros:** violações de unicidade e conflitos de `versao` viram erros próprios (`ErroPersistencia` e filhos, `CONVENCOES.md` §4.5); a exceção do driver não sai de `persistencia/`.
- **`CONVENCOES.md`:** a pasta `persistencia/migracoes/` entra na §2, e a linha "Migrations" da §6 deixa de ser pendente.
- **Reversibilidade:** alta agora. Trocar para assíncrono depois muda só a forma de chamar os repositórios, não o esquema.
