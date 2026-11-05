# ADR-0003 — Ferramentas do backend: teste, lint, formatação e tipagem

- **Trilha:** Backend
- **Status:** Aceita
- **Data:** 2026-10-29
- **Decisão relacionada:** D-11 (parte backend) — `AMBIENTE.md` §15
- **Tarefa:** BE-001 (`specs/tarefas-iniciais.md`)
- **Aprovação:** autor, 2026-10-29 (ferramentas aprovadas; P-1 = `venv` + `pip`; P-2 adiada para a BE-101; P-3 = adotar cobertura)

---

## 1. Contexto

- Sem ferramenta de teste definida não é possível cumprir o `AGENTS.md` §8 ("cada funcionalidade nasce com testes") nem a definição de pronto (§13). Esta decisão precede qualquer código do backend.
- `AGENTS.md` §10 exige Python tipado em código novo e evita `Any` sem justificativa; §10.1 exige justificar cada dependência (problema, por que a biblioteca padrão não basta, manutenção, licença compatível com open-source).
- `CONVENCOES.md` §9 já usa nomes `test_<modulo>.py` e funções `test_<comportamento>_<condicao>`, compatíveis com os principais runners; rastreabilidade por docstring citando `CA-`/`RF-`.
- Escopo **somente backend (Python)**. O frontend tem ADR próprio (FE-002, regra S-7).
- Estas ferramentas são **de desenvolvimento**: não entram na imagem de execução nem são importadas por `backend/src/`.

### 1.1 Fatos observados no ambiente do autor (2026-10-29, verificado nesta sessão)

| Item | Resultado |
|---|---|
| `python3 --version` | Python 3.14.7 |
| `uv --version` | uv 0.12.22 |
| `pip`, `pip3`, `poetry`, `pipx` | não encontrados no PATH |
| `pytest`, `ruff`, `black`, `flake8`, `isort`, `mypy`, `pyright` | não instalados |
| módulo `venv` | disponível |

Isso descreve **a máquina do autor**, não a versão de Python do projeto (ver §6, pergunta P-2).

---

## 2. Critérios

1. Atende ao requisito (testes de domínio, falhas, casos-limite; tipagem estrita; estilo consistente).
2. Menor número de dependências para cobrir a necessidade (`AGENTS.md` §10.1).
3. Licença permissiva compatível com projeto open-source.
4. Manutenção ativa e adoção ampla no ecossistema Python/FastAPI.
5. Configuração centralizada em `backend/pyproject.toml` (S-7), sem arquivos extras.
6. Funciona igual localmente, em Docker e em CI futura.

---

## 3. Opções consideradas

### 3.1 Testes

| Opção | Prós | Contras | Licença |
|---|---|---|---|
| **A. `unittest` (biblioteca padrão)** | Zero dependência. | Mais verboso (classes, `self.assert*`); parametrização limitada (`subTest`); fixtures menos práticas para simuladores com cenários. | PSF (parte do Python) |
| **B. `pytest`** | Padrão de fato no ecossistema; `assert` simples; `@pytest.mark.parametrize` ideal para tabelas de casos (placas, quadros, transições); fixtures para injetar simuladores; marcadores para rastrear `CA-`; descobre `test_*.py` (já previsto no `CONVENCOES.md` §9); é o runner usado na documentação de testes do FastAPI. | Uma dependência de desenvolvimento. | MIT |

### 3.2 Lint e formatação

| Opção | Prós | Contras | Licença |
|---|---|---|---|
| **A. `black` + `flake8` + `isort`** | Ferramentas maduras e conhecidas. | Três dependências e três configurações; sobreposição de regras. | MIT / MIT / MIT |
| **B. `ruff` (lint + formatação)** | Uma ferramenta cobre lint, ordenação de imports e formatação (compatível com o estilo do black); configuração única no `pyproject.toml`; rápido. | Projeto mais novo; conjunto de regras precisa ser escolhido explicitamente. | MIT |
| **C. Nenhuma** | Zero dependência. | Sem verificação automática de estilo e de erros comuns; contraria a meta de código legível e consistente. | — |

### 3.3 Tipagem estática

| Opção | Prós | Contras | Licença |
|---|---|---|---|
| **A. `mypy`** | Verificador de referência do Python; instalável como pacote Python (sem Node); modo `--strict`; bom suporte a Pydantic/FastAPI via plugin quando necessário. | Mais lento que pyright em bases grandes (irrelevante neste porte). | MIT |
| **B. `pyright`** | Rápido; inferência forte. | Distribuído via Node (ou wrapper que baixa Node), o que mistura ferramentas de frontend no backend (contra S-7). | MIT |
| **C. Nenhum** | Zero dependência. | Anotações de tipo sem verificação; contraria `AGENTS.md` §10. | — |

### 3.4 Cobertura

| Opção | Prós | Contras | Licença |
|---|---|---|---|
| **A. Não adotar agora** | Nenhuma dependência extra; rastreabilidade já é por `CA-`. | Sem métrica de linhas não exercitadas. | — |
| **B. `coverage.py` (via `pytest-cov`)** | Mostra código não testado. | Duas dependências; métrica sem meta definida vira ruído. | Apache-2.0 / MIT |

---

## 4. Decisão

| Necessidade | Ferramenta proposta | Justificativa resumida |
|---|---|---|
| Testes | **pytest** | Parametrização e fixtures reduzem muito o código de teste dos casos de falha (§7.2) e dos simuladores; `unittest` não oferece isso com a mesma clareza. |
| Lint + formatação | **ruff** | Uma dependência no lugar de três. |
| Tipagem | **mypy em modo estrito** | Mantém o backend só com ferramentas Python (S-7); cumpre `AGENTS.md` §10. |
| Cobertura | **coverage.py via `pytest-cov`** | Decisão do autor (P-3): mostrar linhas não exercitadas pelos testes. **Sem meta mínima** de cobertura; a rastreabilidade continua pelos `CA-`. |
| Ambiente e dependências | **`venv` + `pip`** | Decisão do autor (P-1): só ferramentas padrão do Python para quem clonar o repositório; sem lockfile. |

Total: **4 dependências de desenvolvimento declaradas** (pytest, pytest-cov, ruff, mypy; `pytest-cov` traz coverage.py), nenhuma de execução.

### 4.1 Regras de uso propostas

- Todas declaradas como dependências **de desenvolvimento** em `backend/pyproject.toml`; configuração das três também no `pyproject.toml` (sem `setup.cfg`, `.flake8`, `mypy.ini`, `pytest.ini`).
- **Versões**: não fixadas neste ADR. Na BE-101/BE-102 serão fixadas as versões efetivamente instaladas e verificadas, com o motivo registrado (`AGENTS.md` §10.1).
- `mypy --strict` sobre `src/` e `tests/`; `Any` explícito só com comentário justificando.
- Conjunto de regras do `ruff`: definido na spec `esqueleto-backend` (BE-101), começando pelo conjunto padrão mais um grupo pequeno justificado; não ativar "todas as regras".
- Testes citam `CA-`/`RF-` na docstring (`CONVENCOES.md` §9). Uso de marcador customizado do pytest para rastreabilidade: **não** adotado agora (docstring basta).
- Único plugin de pytest aprovado: `pytest-cov`. Nenhum outro (ex.: async, mock) sem nova justificativa. Testes de domínio são síncronos e usam a biblioteca padrão (`unittest.mock`, se preciso).
- Comandos oficiais (a registrar no `AMBIENTE.md` §6.1 **somente depois de executados** na BE-102), na forma:
  - testes: `pytest`
  - lint: `ruff check`
  - formatação: `ruff format --check`
  - tipagem: `mypy`
  - cobertura: `pytest --cov` (forma exata definida na BE-101)

---

## 5. Consequências

- **Positivas**: testes de domínio podem começar logo após o esqueleto; estilo e tipos verificados automaticamente; configuração única.
- **Negativas**: quatro dependências a manter atualizadas; sem lockfile (P-1), a reprodutibilidade depende das versões fixadas no `pyproject.toml`; mypy estrito exige anotações completas (custo pequeno em código novo).
- **Reversibilidade**: alta. Trocar `ruff` por `black`+`flake8` ou `mypy` por `pyright` afeta só o `pyproject.toml`. Trocar `pytest` por `unittest` exigiria reescrever testes (custo cresce com o tempo).
- **Docker**: ferramentas não entram na imagem de execução; se houver perfil `teste` (`CONVENCOES.md` §7.2), ele as instala separadamente (definido em BE-801/INT-001).

---

## 6. Perguntas (respondidas em 2026-10-29)

| ID | Pergunta | Opções | Recomendação |
|---|---|---|---|
| P-1 ✅ `venv` + `pip` | Como criar o ambiente virtual e instalar dependências do backend? | (a) `venv` + `pip` (padrão, `pip` dentro do venv); (b) `uv` (já instalado na máquina do autor; gera lockfile); (c) `poetry` (não instalado). | **(a) `venv` + `pip`**: zero ferramenta extra exigida de quem clonar o repositório. (b) é aceitável se o autor quiser lockfile reproduzível. |
| P-2 ✅ 3.12 (decidida na BE-101, spec 001 §11) | Qual versão mínima de Python o projeto suporta? | A máquina do autor tem 3.14.7; a imagem Docker ainda não existe. A compatibilidade de EasyOCR/OpenCV com a versão escolhida **não foi verificada**. | Decidir na BE-101, após verificar a compatibilidade das dependências [DEFINIDO] (EasyOCR, OpenCV) com a versão candidata. Não presumir. |
| P-3 ✅ Sim | Adotar cobertura agora? | Sim / Não. | Não (§3.4); o autor escolheu **Sim**. |

---

## 7. Aprovação

- [x] Autor aprovou pytest, ruff e mypy estrito (2026-10-29).
- [x] Autor respondeu P-1 (`venv` + `pip`) e P-3 (Sim); P-2 respondida na BE-101: Python ≥ 3.12 (evidência na spec 001 §11).

Atualizados na mesma mudança: `AMBIENTE.md` §15 (D-11, parte backend) e `specs/README.md`.
