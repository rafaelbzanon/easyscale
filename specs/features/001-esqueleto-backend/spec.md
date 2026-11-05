# Spec 001 — Esqueleto do backend

- **Trilha:** Backend
- **Status:** Implementada (BE-102, 2026-10-29; aguarda aceite do autor)
- **Data:** 2026-10-29
- **Tarefa:** BE-101 (spec e plano), BE-102 (implementação) — `specs/tarefas-iniciais.md`
- **Decisões base:** ADR-0002 (monólito modular, Aceita), ADR-0003 (ferramentas do backend, Aceita)
- **Plano:** [`plano.md`](plano.md)

---

## 1. Contexto e origem

- As specs de domínio (BE-201 a BE-203) e suas implementações (BE-211 a BE-213) precisam de um lugar para o código e de um comando de testes já funcionando (`AGENTS.md` §8, §13).
- O ADR-0003 definiu as ferramentas: pytest, pytest-cov, ruff e mypy em modo estrito, instaladas com `venv` + `pip`. A versão mínima de Python (P-2) ficou para esta spec.
- O ADR-0002 definiu um único pacote `pesagem`, com módulos separados pelas regras de dependência P-4 a P-6 do `CONVENCOES.md`.
- Requisitos ligados: **RNF-001** (organização em módulos) e **RNF-008** (Python no backend). As regras de qualidade vêm do `AGENTS.md` §8 e §10.

## 2. Objetivo

Criar o **mínimo** necessário para escrever e rodar testes do domínio, com lint, formatação, tipagem e cobertura verificados por comando, e com as regras de dependência entre camadas checadas automaticamente.

## 3. Fora de escopo

- FastAPI, rotas, `main.py`, `config.py` e variáveis de ambiente (ficam para BE-501, BE-701 e posteriores).
- Banco, ORM, migrações, Docker e `Dockerfile` (ficam para BE-501, BE-502 e BE-801).
- OpenCV, EasyOCR, PySerial e qualquer dependência de execução. **O esqueleto não tem nenhuma.**
- Os subpacotes `dominio/operacao/`, `dominio/pesagem/` e `dominio/placa/`, que são criados nas tarefas BE-211 a BE-213. Nenhuma pasta vazia "para o futuro" (`CONVENCOES.md` §2).
- Integração contínua (CI).

## 4. Atores

Quem desenvolve: o autor, o agente ou uma pessoa que clonou o repositório.

## 5. Pré-condições

- Python **3.12** ou mais novo (P-2, §11).
- `venv` disponível. O `pip` usado é o que vem dentro do venv; ele precisa ter a versão 25.1 ou mais nova para instalar os grupos de dependência (`pip install --group`).

## 6. Comportamento normal

1. A partir de `backend/`, quem desenvolve cria o venv e instala as ferramentas com um comando documentado (ver §8). Nenhum outro programa além do Python é necessário.
2. Os comandos oficiais funcionam sem argumentos extras, todos a partir de `backend/`:
   - `pytest`
   - `ruff check`
   - `ruff format --check`
   - `mypy`
   - e a variante de cobertura, `pytest --cov`.
3. Os testes encontram o pacote `pesagem` sem que ele seja instalado. Isso é feito pela opção `pythonpath` do pytest e pela `mypy_path` do mypy (ver Q-B1).
4. Um teste de arquitetura verifica as regras P-4 a P-6 em todo arquivo `.py` dentro de `src/pesagem/`. Ele lê os `import` com o módulo `ast` da biblioteca padrão, sem executar o código analisado.

## 7. Comportamento em falha

| Situação | Comportamento esperado |
|---|---|
| Um módulo em `dominio/` importa `api`, `orquestracao`, `lpr`, `dispositivos`, `persistencia`, `fastapi`, `serial`, `cv2` ou `easyocr` | O teste de arquitetura falha e a mensagem nomeia o arquivo e o import proibido. |
| `serial` é importado fora de `dispositivos/`, ou `cv2`/`easyocr` fora de `lpr/` | O teste de arquitetura falha e a mensagem nomeia o arquivo e o import proibido. |
| Um arquivo `.py` de `src/` não pode ser analisado (erro de sintaxe) | O teste falha e nomeia o arquivo. O arquivo **não** é ignorado em silêncio. |
| Código sem anotação de tipo ou com `Any` implícito | O `mypy --strict` falha. |
| Versão de Python abaixo da mínima | O `pip` recusa a instalação por causa do `requires-python`. Não verificado em versão antiga; ver CA-006. |
| A pasta `src/pesagem/` não existe ou está vazia de `.py` | O teste de arquitetura falha, em vez de passar sem ter verificado nada. |

## 8. Regras e dados

- **Arquivos criados:**
  - `backend/pyproject.toml`
  - `backend/src/pesagem/__init__.py`
  - `backend/src/pesagem/dominio/__init__.py`
  - `backend/tests/unitarios/test_dependencias_camadas.py`
- **`pyproject.toml`:**
  - `[project]` com `name`, `version`, `requires-python` (P-2) e `dependencies = []`;
  - `[dependency-groups]`, padrão da PEP 735, com o grupo `dev` contendo pytest, pytest-cov, ruff e mypy, todos com a **versão fixada** (`==`) que foi efetivamente instalada e verificada na BE-102;
  - configuração de `[tool.pytest.ini_options]`, `[tool.ruff]`, `[tool.mypy]` e `[tool.coverage]` no mesmo arquivo.
- **Escolha de versões:** a mais recente estável publicada há pelo menos 14 dias, para evitar lançamentos que ainda não foram testados pela comunidade. Candidatas consultadas no PyPI em 2026-10-29:

  | Pacote | Versão | Publicada em | Licença |
  |---|---|---|---|
  | pytest | 9.1.1 | 2026-06-19 | MIT |
  | pytest-cov | 7.1.0 | 2026-03-21 | MIT |
  | ruff | 0.17.0 | 2026-10-09 | MIT |
  | mypy | 2.4.0 | 2026-10-01 | MIT |

  O `coverage` 7.16.2 (Apache-2.0) vem como dependência do pytest-cov. Essas versões só valem depois de instaladas e com os comandos rodando na BE-102.
- **Regras do ruff:** o conjunto padrão (`E4`, `E7`, `E9`, `F`) mais `I` (ordenação de imports), `B` (bugbear, que pega erros comuns como argumento padrão mutável) e `UP` (sintaxe compatível com a versão mínima). Não ativar "todas as regras" (ADR-0003 §4.1).
- **Cobertura:** mede `src/pesagem` e mostra as linhas não cobertas. **Sem meta mínima**, então `fail_under` não é configurado (ADR-0003, P-3).
- **Rastreabilidade:** cada teste cita na docstring os `CA-` desta spec.
- **Nomes:** seguem o `CONVENCOES.md` §4 e §9.

## 9. Critérios de aceitação

| CA | Critério | Como verificar |
|---|---|---|
| CA-001 | Com o venv criado e o grupo `dev` instalado, `pytest` termina com sucesso e roda os testes de arquitetura. | Executar e anexar a saída. |
| CA-002 | `ruff check` e `ruff format --check` terminam sem apontamentos. | Executar e anexar a saída. |
| CA-003 | `mypy` (modo estrito, sobre `src/` e `tests/`) termina sem erros. | Executar e anexar a saída. |
| CA-004 | `pytest --cov` gera o relatório de cobertura de `src/pesagem` no terminal. | Executar e anexar a saída. |
| CA-005 | O teste de arquitetura **detecta** cada violação: import proibido em `dominio/`, `serial` fora de `dispositivos/`, `cv2`/`easyocr` fora de `lpr/`, arquivo com erro de sintaxe e pasta sem `.py`. | Testes parametrizados que analisam código de exemplo em diretório temporário, sem tocar em `src/`. |
| CA-006 | O `requires-python` do `pyproject.toml` corresponde à resposta da P-2. | Leitura. A rejeição real com Python antigo **não** é verificada se a máquina não tiver essa versão; o relato da BE-102 dirá isso. |
| CA-007 | Não existe dependência de execução nem pasta vazia. | Leitura de `dependencies = []` e listagem das pastas. |

## 10. Impacto

- **Módulos:** cria `backend/`. Os arquivos antigos `backend/app/*` já estão apagados na sua pasta, mas o Git ainda os rastreia, e esta spec não mexe neles: apagá-los do Git depende de pedido seu. Também não há conflito de caminho, porque o esqueleto usa `backend/src/`.
- **Documentação:** depois da BE-102, registrar os comandos **executados** no `AMBIENTE.md` §6.1 (ADR-0003). O `AMBIENTE.md` é arquivo da trilha A, então só o §6.1 é tocado, como o ADR-0003 já previa.
- **Segurança operacional:** nenhum impacto direto. O teste de arquitetura reforça o `AGENTS.md` §7.3 ("acesso a dispositivos somente pela camada de dispositivos").
- **Reversibilidade:** alta. São só arquivos novos.

## 11. Perguntas (respondidas em 2026-10-29: P-2 = **3.12**; Q-B1 = **(a) sem build backend**)

| ID | Pergunta | Opções | Recomendação |
|---|---|---|---|
| **P-2** (ADR-0003) | Qual a versão mínima de Python? | **(a) 3.12**; (b) 3.13; (c) 3.14. | **(a) 3.12.** Veja a evidência abaixo. |
| **Q-B1** | Como os testes e o mypy encontram o pacote? | **(a) Sem build backend:** `pythonpath = ["src"]` no pytest, `mypy_path = "src"` no mypy, ferramentas por `pip install --group dev`. Nenhuma dependência extra. (b) Declarar um build backend (setuptools ou hatchling) e usar `pip install -e .`. Isso acrescenta uma ferramenta de empacotamento. | **(a).** Hoje o pacote não precisa ser instalado nem distribuído. A opção (b) entra quando o Dockerfile (BE-801) precisar instalar o pacote. |

**Evidência para P-2**, verificada só por consulta aos metadados do PyPI em 2026-10-29. **Nada foi instalado.**
- As versões recentes de numpy (2.5.4) e scipy (1.18.1), que são dependências do EasyOCR, exigem Python **≥ 3.12**.
- As versões recentes de torch (2.14.1), torchvision (0.29.1), scikit-image, shapely, pyclipper, python-bidi e pillow têm pacotes compilados (wheels) para **3.12, 3.13 e 3.14**. O opencv-python-headless (4.14.0.94) usa wheel `abi3`, que serve para qualquer versão a partir da 3.7.
- O torchvision exclui só a 3.14.1 (`!=3.14.1`).
- O **EasyOCR 1.7.2** é a última versão, publicada em 2024-09. Não declara `requires_python` nem as versões de Python suportadas, então **não há evidência de que funcione em 3.13 ou 3.14**. Só um teste real resolve, e isso fica para a BE-401/BE-801.
- Por isso a 3.12 é o piso que as dependências recentes já impõem. Ela também é a versão com mais chance de o EasyOCR funcionar sem ajustes. A sua máquina tem 3.14.7, que está acima do piso, então serve para desenvolver o esqueleto. A versão da imagem Docker é decidida na BE-801.
