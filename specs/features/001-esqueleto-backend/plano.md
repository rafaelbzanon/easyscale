# Plano 001 — Esqueleto do backend

- **Trilha:** Backend
- **Status:** Aprovado (autor, 2026-10-29)
- **Spec:** [`spec.md`](spec.md)
- **Tarefa de implementação:** BE-102

Este plano só é executado depois que a spec estiver **Aprovada** e P-2 e Q-B1 tiverem resposta.

## Tarefas (em ordem)

| # | Tarefa | CA |
|---|---|---|
| 1 | Criar `backend/pyproject.toml` com `[project]`, onde `requires-python` vem da P-2 e `dependencies = []`; `[dependency-groups].dev` com as versões candidatas; e a configuração de pytest, ruff, mypy e coverage. | CA-006, CA-007 |
| 2 | Criar `backend/src/pesagem/__init__.py` e `backend/src/pesagem/dominio/__init__.py`, cada um só com uma docstring que diga o que o módulo é e quais regras de camada valem para ele. | CA-007 |
| 3 | Criar `backend/tests/unitarios/test_dependencias_camadas.py`, usando só `ast`, `pathlib` e o pytest. Uma função lista os imports de cada `.py` e outra aplica as regras P-4 a P-6. Haverá um teste sobre o `src/pesagem/` real e testes parametrizados com casos de violação, escritos em `tmp_path`. | CA-001, CA-005 |
| 4 | Criar o venv em `backend/.venv`, já coberto pelo `.gitignore`, e instalar com `pip install --group dev`. Se uma versão candidata falhar na instalação, **parar e relatar**, sem trocar de versão por conta própria. | CA-001 |
| 5 | Executar `pytest`, `ruff check`, `ruff format --check`, `mypy` e `pytest --cov`, e anexar a saída real ao relato. | CA-001 a CA-004 |
| 6 | Registrar no `AMBIENTE.md` §6.1 apenas os comandos que de fato rodaram. Atualizar a spec para `Implementada` e o `specs/README.md`. | — |

## Estratégia de teste

- **Unitário:** o próprio teste de arquitetura, com caminho normal (o `src/` real passa) e casos de falha da spec §7, via `@pytest.mark.parametrize`.
- **Integração e ponta a ponta:** não se aplicam ao esqueleto.
- **Ainda não verificado:** a rejeição do `pip` com um Python abaixo do mínimo (CA-006), se essa versão não estiver disponível na máquina.

## Riscos

- O `pip` dentro de um venv de Python antigo pode ser anterior à 25.1 e não ter `--group`. A documentação dirá para atualizá-lo com `python -m pip install --upgrade pip` dentro do venv. Na máquina do autor, o `ensurepip` traz o pip 26.2.1 (verificado).
- O ruff 0.17.0 foi publicado há 20 dias, perto do limite de 14 dias usado na escolha. Se a instalação ou a execução mostrar problemas, relatar.
