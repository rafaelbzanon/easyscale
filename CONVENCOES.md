# CONVENCOES.md — Nomenclatura e organização de pastas

Sistema open-source de automação de pesagem rodoviária com LPR e visão computacional (TCC — IFRS, Veranópolis).

Este arquivo define **como nomear** e **onde colocar** cada coisa no repositório. Complementa:

- `AGENTS.md` — como trabalhar (SDD, segurança, testes, relato);
- `AMBIENTE.md` — o quê e com quê (arquitetura, tecnologias, decisões).

> Leia este arquivo junto com o `AGENTS.md` e o `AMBIENTE.md` no início de toda sessão.
> Usa a mesma legenda de status: **[ARTIGO]**, **[DEFINIDO]**, **[PROPOSTA]**, **[PENDENTE]**.

**Status deste documento:** Aprovado pelo autor em 2026-10-29 (C-003). Resolve a decisão **D-10** (idioma/convenção de nomes). O agente deve segui-lo e **não** inventar convenções paralelas. Mudanças neste arquivo exigem aprovação do autor. Sincronizado com as specs 002 a 005 em 2026-11-02 (C-104, aprovado pelo autor) e com as specs 006 a 008 e os ADRs 0004 e 0005 em 2026-11-04, a pedido do autor.

---

## 1. Regras gerais (valem para tudo)

| # | Regra |
|---|---|
| G-1 | **Domínio em português, sem acentos e sem cedilha** em qualquer identificador: código, arquivos, pastas, variáveis de ambiente, banco, rotas. Ex.: `pesagem`, `agendamento`, `balanca`, `cancela`, `operacao`. |
| G-2 | **Inglês só para termos técnicos** sem tradução natural ou impostos por bibliotecas: `router`, `parser`, `timeout`, `frame`, `cache`, `payload`, `hash`, `id`, `roi`, `ocr`, `lpr`. Não traduzir nomes de APIs de terceiros (`APIRouter`, `serial.Serial`). |
| G-3 | **Nunca misturar idiomas para o mesmo conceito.** Se é `pesagem` em um lugar, é `pesagem` em todos (nada de `weighing` em outro). Use o glossário da seção 10. |
| G-4 | **Acentos são permitidos apenas em texto livre**: documentação, comentários, mensagens exibidas ao usuário, strings de log. |
| G-5 | **Unidades no nome** de toda grandeza física ou de tempo: `_kg`, `_ms`, `_s`. Ex.: `peso_bruto_kg`, `timeout_leitura_ms`. Nunca `peso` ou `timeout` sozinhos quando o valor tem unidade. |
| G-6 | **Instantes terminam em `_em`** (como no `docs/modelo-dados/schema.sql`): `criado_em`, `lida_em`, `peso_inicial_em`. Datas sem hora terminam em `data_`: `data_prevista`. |
| G-7 | **Sem abreviações** fora das consagradas (`id`, `cnpj`, `cpf`, `cnh`, `rg`, `ocr`, `lpr`, `roi`, `api`, `url`). `qtd`, `vlr`, `cfg`, `msg` são proibidas. |
| G-8 | **Singular para entidades** (`pesagem`, `veiculo`); **plural para coleções** (rotas REST, listas, pastas que agrupam itens homogêneos como `rotas/`, `repositorios/`). |
| G-9 | Nomes descrevem **o que é**, não como foi implementado: `leitor_placa`, não `easyocr_wrapper` (exceto na implementação concreta, ver §4.4). |

---

## 2. Árvore de diretórios **[PROPOSTA]**

> Nada abaixo existe até ser criado em uma tarefa ligada a spec aprovada (`AGENTS.md` §5). **Não crie pastas vazias "para o futuro"**: crie cada pasta na tarefa que precisar dela.
>
> **Já existem (2026-11-04):** os documentos da raiz, `specs/`, `docs/decisoes/`, `docs/artigo/`, `docs/modelo-dados/` e, em `backend/`, `pyproject.toml`, `src/pesagem/dominio/` (sem `autorizacao/`), `src/pesagem/lpr/`, `src/pesagem/dispositivos/` (sem `serial.py` e `protocolos/`), `tests/unitarios/` e `tests/avaliacao/`. Desde 2026-11-07: `src/pesagem/config.py`, `src/pesagem/persistencia/` e `tests/integracao/` (spec 014).

```
/
├── AGENTS.md
├── AMBIENTE.md
├── CONVENCOES.md
├── README.md                      # instalação, configuração, execução [ARTIGO]
├── LICENSE                        # [PENDENTE] D-12 — arquivo MIT já existe, sem decisão registrada
├── compose.yaml                   # orquestração Docker (quando aprovado)
├── .env.exemplo                   # variáveis de ambiente sem segredos
│
├── specs/                         # especificações (AGENTS.md §5.1)
│   ├── README.md
│   ├── tarefas-iniciais.md        # lista de tarefas por trilha
│   ├── requisitos.md
│   ├── glossario.md
│   └── features/
│       └── 001-maquina-estados-operacao/
│           ├── spec.md
│           ├── plano.md
│           └── tarefas.md
│
├── docs/
│   ├── decisoes/                  # ADRs
│   │   └── ADR-0001-banco-de-dados.md
│   ├── artigo/                    # artigo do TCC (artigo-tcc.pdf)
│   ├── modelo-dados/              # referência do modelo enquanto não há migrations
│   │   └── schema.sql
│   └── equipamentos/              # manuais, quadros de exemplo reais da balança/cancela
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml             # ferramentas: ADR-0003; grupos `dev` e `lpr`
│   ├── src/
│   │   └── pesagem/               # pacote Python raiz (ver §4.1)
│   │       ├── __init__.py
│   │       ├── main.py            # cria a aplicação FastAPI
│   │       ├── config.py          # leitura/validação das variáveis de ambiente
│   │       ├── api/               # borda HTTP (sem regra de negócio)
│   │       │   ├── rotas/         # um arquivo por recurso: agendamentos.py, pesagens.py
│   │       │   ├── esquemas/      # modelos de entrada/saída da API (Pydantic)
│   │       │   ├── dependencias.py
│   │       │   ├── erros.py           # corpo de erro da spec 007 §3.2
│   │       │   ├── cadastros.py       # construtor comum das rotas de cadastro (spec 007)
│   │       │   ├── validacao.py       # CPF, CNPJ e placa digitada (spec 007 §6.1)
│   │       │   ├── senha.py           # scrypt (ADR-0004)
│   │       │   ├── criar_administrador.py  # comando do primeiro administrador
│   │       │   └── esquemas/, rotas/      # um arquivo por recurso (comum, usuarios, pesagens, ...)
│   │       ├── dominio/           # regras de negócio puras (sem I/O)
│   │       │   ├── operacao/      # máquina de estados, transições
│   │       │   ├── pesagem/       # cálculo de peso líquido, aceitação de peso
│   │       │   ├── placa/         # normalizacao.py, selecao.py (specs 003 e 005)
│   │       │   ├── autorizacao/   # decisao.py: decisão de autorizar a entrada e a volta (spec 015)
│   │       │   └── erros.py
│   │       ├── orquestracao/      # coordena domínio + LPR + dispositivos + persistência (spec 015)
│   │       │   ├── configuracao.py
│   │       │   ├── erros.py
│   │       │   ├── repositorios.py
│   │       │   ├── eventos.py         # distribuidor de eventos em memória (ADR-0005)
│   │       │   ├── operacao.py
│   │       │   └── simuladores.py     # controle dos simuladores, só em SIMULADO
│   │       ├── lpr/               # visão computacional (OpenCV + EasyOCR)
│   │       │   ├── fontes/        # interface.py, pasta_imagens.py; futuras: camera_rede.py, camera_local.py, arquivo_video.py (Q-06)
│   │       │   ├── erros.py
│   │       │   ├── preprocessamento.py
│   │       │   ├── localizacao.py
│   │       │   ├── pipeline.py          # imagem → ROIs → OCR (spec 005)
│   │       │   ├── leitor_placa.py      # fronteira do OCR (interface)
│   │       │   ├── leitor_easyocr.py    # implementação concreta
│   │       │   ├── leitor_simulado.py   # para testar o pipeline sem o EasyOCR
│   │       │   ├── reconhecedor_simulado.py  # chegada de placa simulada (spec 015)
│   │       │   ├── codificacao.py       # JPEG das imagens das decisões (OpenCV, P-6)
│   │       │   ├── posicao/             # interface.py, simulada.py; real bloqueada (Q-06, Q-17)
│   │       │   ├── baixar_modelos.py    # download explícito dos modelos (D-08)
│   │       │   └── resultado.py
│   │       ├── dispositivos/      # balança e cancelas (PySerial + simuladores)
│   │       │   ├── erros.py
│   │       │   ├── modo.py              # SIMULADO (padrão) ou REAL (spec 004 §5.3)
│   │       │   ├── balanca/
│   │       │   │   ├── interface.py
│   │       │   │   ├── tentativas.py    # política de segunda tentativa (spec 004 §6.2)
│   │       │   │   ├── simulada.py
│   │       │   │   ├── serial.py        # bloqueado até a Q-01
│   │       │   │   └── protocolos/      # um arquivo por modelo, parsing puro, sem I/O (RF-030; Q-01)
│   │       │   └── cancela/
│   │       │       ├── interface.py
│   │       │       ├── tentativas.py
│   │       │       ├── simulada.py
│   │       │       └── serial.py        # bloqueado até a Q-01
│   │       └── persistencia/      # SQLAlchemy Core + psycopg 3 (ADR-0006)
│   │           ├── migracoes/     # Alembic: env.py e versions/NNNN_descricao.py (ADR-0006)
│   │           └── repositorios/  # um arquivo por agregado: agendamento, pesagem, cadastro, faixa_horario, usuario, acesso, ...
│   └── tests/
│       ├── unitarios/             # espelha src/pesagem/
│       ├── integracao/        # persistencia/: PostgreSQL real em contêiner (spec 014)
│       ├── ponta_a_ponta/
│       ├── avaliacao/             # avaliação do LPR com o acervo (marcador `avaliacao`, spec 005 §6.4)
│       └── conftest.py            # só se houver fixture compartilhada (pytest, ADR-0003)
│
├── frontend/                      # React + Vite + Tailwind (ADR-0007)
│   ├── Dockerfile
│   └── src/
│       ├── paginas/               # cadastros, agendamentos, operacao, historico, diagnostico
│       ├── componentes/
│       ├── api/                   # cliente HTTP e tipos espelhando a API
│       ├── tipos/
│       └── estilos/
│
├── simuladores/                   # simuladores executáveis à parte (opcional)
│   ├── balanca/
│   └── cancela/
│
└── dados-teste/                   # só documentação: o acervo real fica fora do repositório (spec 005 §12.1)
    └── placas/
        └── README.md              # onde fica o acervo, formato do gabarito.csv, licença e privacidade (Q-09)
```

### 2.1 Regras de organização

| # | Regra |
|---|---|
| P-1 | **Pastas de primeiro nível e de documentação**: `kebab-case` (`dados-teste`, `modelo-dados`). |
| P-2 | **Pastas dentro de pacotes Python**: `snake_case` (obrigatório para import). Ex.: `ponta_a_ponta`. |
| P-3 | **Pastas do frontend**: `kebab-case`. |
| P-4 | **Regra de dependência no backend** (direção permitida das importações):<br>`api` → `orquestracao` → `dominio`<br>`orquestracao` → `lpr`, `dispositivos`, `persistencia`<br>`dominio` **não importa** `api`, `lpr`, `dispositivos`, `persistencia`, `fastapi`, `serial`, `cv2` nem `easyocr`.<br>`persistencia` → `dominio` (só tipos: `Operacao` e eventos; spec 014).<br>`dispositivos` e `lpr` **não importam** `dominio`: têm tipos próprios, e a `orquestracao` converte (specs 004 P-6 e 005 §5.3). |
| P-5 | **`dominio/` não faz I/O** (nem HTTP, serial, câmera, banco, relógio direto). Recebe dados e dependências injetadas. |
| P-6 | **Só `dispositivos/` importa `serial`**; só `lpr/` importa `cv2` e `easyocr`; só `persistencia/` importa `sqlalchemy`, `psycopg` e `alembic` (spec 014 CA-017). Qualquer outro lugar que precise disso está na camada errada. |
| P-7 | **`tests/unitarios/` espelha `src/pesagem/`**: o teste de `dominio/placa/normalizacao.py` fica em `tests/unitarios/dominio/placa/test_normalizacao.py`. |
| P-8 | **Simulador usado em testes automatizados** vive em `dispositivos/<equipamento>/simulada.py`. A pasta `simuladores/` raiz é só para simuladores executados como processo/serviço separado, se aprovados. |
| P-9 | **Arquivos grandes** (imagens, vídeos, modelos do EasyOCR) **não** entram em `src/` nem na imagem Docker. Modelos ficam numa pasta configurada, baixados só pelo comando explícito (D-08). O acervo de imagens reais e o seu `gabarito.csv` contêm placas e **nunca** entram no Git (spec 005 §12.1, Q-09). |
| P-10 | O esquema vigente são as migrações em `persistencia/migracoes/` (ADR-0006); o `docs/modelo-dados/schema.sql` é histórico e não é mais atualizado. Não duplicar o esquema em outro lugar. |

---

## 3. Arquivos de documentação e especificação

| Tipo | Padrão | Exemplo |
|---|---|---|
| Documento de raiz | `MAIUSCULAS.md` | `AGENTS.md`, `README.md` |
| Demais `.md` | `kebab-case.md` | `requisitos.md`, `glossario.md` |
| Pasta de feature | `NNN-slug-kebab` (3 dígitos, sequencial, sem reuso) | `003-camada-dispositivos` |
| Arquivos da feature | fixos | `spec.md`, `plano.md`, `tarefas.md` |
| ADR | `ADR-NNNN-titulo-kebab.md` (4 dígitos) | `ADR-0002-framework-frontend.md` |
| IDs de requisito | `RF-NNN`, `RNF-NNN`, `RN-NNN` | `RF-012` |
| Critério de aceitação | `CA-NNN` (escopo da feature) | `CA-004` |
| Decisões / perguntas / riscos | `D-NN`, `Q-NN`, `R-NN` (como no `AMBIENTE.md`) | `D-10`, `Q-02` |

O slug é curto (2 a 5 palavras), descreve o assunto e nunca muda depois de criado.

---

## 4. Backend — Python

### 4.1 Pacote e arquivos

- Pacote raiz: **`pesagem`** (layout `src/`).
- Arquivos e módulos: `snake_case.py`, substantivo que descreve o conteúdo: `maquina_estados.py`, `calculo_peso.py`, `normalizacao.py`.
- Proibidos: `utils.py`, `helpers.py`, `misc.py`, `common.py`, `manager.py`. Se algo não tem lugar, falta uma decisão de design — pergunte.

### 4.2 Identificadores

| Elemento | Padrão | Exemplo |
|---|---|---|
| Variável, função, método, parâmetro | `snake_case` | `placa_normalizada`, `calcular_peso_liquido()` |
| Classe | `PascalCase` | `Agendamento`, `ResultadoLeitura` |
| Constante | `UPPER_SNAKE_CASE` | `TOLERANCIA_ESTABILIDADE_KG` (valor vem de config, não fixo — §7) |
| Membro de `Enum` | `UPPER_SNAKE_CASE`, **mesmo texto do banco** | `SituacaoPesagem.PESO_INICIAL_OK` |
| Privado | prefixo `_` | `_validar_quadro()` |
| Tipo genérico | `PascalCase` curto | `T`, `EntidadeT` |

### 4.3 Verbos e formas

| Situação | Padrão | Exemplo |
|---|---|---|
| Ação | verbo no infinitivo | `ler_peso()`, `abrir_cancela()`, `registrar_pesagem()` |
| Consulta que pode não achar | `buscar_` → retorna valor ou `None` | `buscar_agendamento_ativo(placa)` |
| Consulta que exige existir | `obter_` → lança erro se não achar | `obter_pesagem(pesagem_id)` |
| Listagem | `listar_` | `listar_leituras_placa()` |
| Conversão / validação | `normalizar_`, `validar_`, `converter_` | `validar_formato_placa()` |
| Booleano | `esta_`, `tem_`, `pode_`, `e_` (é) ou adjetivo do banco | `esta_estavel`, `tem_agendamento`, `pode_autorizar`, `ativo`, `simulada` |

### 4.4 Interfaces e implementações de dispositivos/OCR

| Papel | Padrão | Exemplo |
|---|---|---|
| Interface (Protocol/ABC) | nome do conceito | `Balanca`, `Cancela`, `LeitorPlaca`, `FonteImagem` |
| Implementação real | conceito + meio | `BalancaSerial`, `CancelaSerial`, `LeitorEasyOcr`, `FonteCameraRede` |
| Implementação simulada | conceito + `Simulada`/`Simulado` (concordância) | `BalancaSimulada`, `CancelaSimulada`, `LeitorPlacaSimulado` |
| Cenário de simulação | `Cenario<Equipamento>.<SITUACAO>` | `CenarioBalanca`: `ESTAVEL`, `INSTAVEL`, `SEM_RESPOSTA`, `SEM_RESPOSTA_NA_PRIMEIRA`, `QUADRO_CORROMPIDO`, `DESCONECTADA`. `CenarioCancela`: `CONFIRMADO`, `CONFIRMADO_NA_SEGUNDA`, `NAO_MOVE`, `FALHA`, `SENSOR_SEM_RESPOSTA` (spec 004 §6.3) |

### 4.5 Erros

- Classes de erro terminam em **prefixo `Erro`**: `ErroComunicacaoBalanca`, `ErroTimeoutCancela`, `ErroTransicaoInvalida`, `ErroLeituraInconclusiva`.
- Base por módulo: `ErroDominio`, `ErroDispositivo`, `ErroLpr`, `ErroPersistencia`.
- Nada de `Exception` genérica lançada nem capturada (`AGENTS.md` §10).
- **Única exceção (C-104, decisão do autor em 2026-11-02):** captura genérica na **fronteira com biblioteca de terceiros** cujas exceções não podem ser listadas (ex.: a chamada ao EasyOCR em `lpr/pipeline.py`). Só vale se, ao mesmo tempo:
  - a falha vira um **resultado tipado** (ex.: `FalhaLeitor`), que segue o caminho seguro;
  - o **tipo** do erro vai para o log, sem dado pessoal;
  - nada é engolido nem "corrigido";
  - um comentário no local explica o motivo.

### 4.6 Estados e situações

- Valores de estado/situação/resultado: `UPPER_SNAKE_CASE`, português, **idênticos** aos `CHECK` do banco: `AGENDADO`, `EM_ANDAMENTO`, `AUTORIZADA`, `NAO_RECONHECIDA`.
- Um valor novo de estado entra **primeiro na spec**, depois no `Enum` e no banco, na mesma mudança.

---

## 5. API HTTP

| Elemento | Padrão | Exemplo |
|---|---|---|
| Prefixo | `/api` (versionamento **[PENDENTE]**, não adicionar `/v1` sem decisão) | `/api/agendamentos` |
| Recurso | substantivo **plural**, `kebab-case` | `/api/leituras-placa`, `/api/pesagens` |
| Item | `/{recurso}/{id}` com parâmetro `<entidade>_id` | `/api/pesagens/{pesagem_id}` |
| Ação que não é CRUD | sub-recurso verbal no infinitivo, só se a spec definir | `POST /api/pesagens/{pesagem_id}/cancelar` |
| Campos JSON | `snake_case`, iguais aos do domínio/banco | `peso_liquido_kg`, `data_prevista` |
| Query string | `snake_case` | `?data_inicio=...&situacao=FINALIZADA` |
| Arquivo de rotas | plural do recurso | `api/rotas/agendamentos.py` |
| Esquemas da API | `<Entidade><Papel>` | `AgendamentoCriacao`, `AgendamentoResposta`, `PesagemResumo` |

Nenhum endpoint é criado sem spec aprovada (`AGENTS.md` §12).

---

## 6. Banco de dados

Segue o padrão já usado no `docs/modelo-dados/schema.sql`. Banco: PostgreSQL (D-01, ADR-0001).

| Elemento | Padrão | Exemplo |
|---|---|---|
| Tabela | singular, `snake_case` | `pesagem`, `leitura_placa`, `ponto_controle` |
| Chave primária | `id` | `id` |
| Chave estrangeira (coluna) | `<tabela_referenciada>_id`, ou papel + `_id` quando houver mais de uma | `veiculo_id`, `cancela_entrada_id` |
| Coluna de usuário responsável | verbo no particípio + `_por` | `criado_por`, `liberado_por` |
| Coluna booleana | adjetivo/particípio | `ativo`, `simulada`, `liberacao_manual` |
| Constraint de PK | `pk_<tabela>` | `pk_pesagem` |
| Constraint de FK | `fk_<tabela>_<coluna>` | `fk_pesagem_agendamento_id` |
| Constraint CHECK | `ck_<tabela>_<regra>` | `ck_pesagem_situacao` |
| Índice único | `ux_<tabela>_<descricao>` | `ux_pesagem_veiculo_aberta` |
| Índice comum | `ix_<tabela>_<colunas>` | `ix_pesagem_criado_em` |
| Migrations | Alembic (ADR-0006), SQL escrito à mão: `NNNN_descricao_snake.py` em `persistencia/migracoes/versions/` | `0001_cria_tabelas_iniciais.py` |
| Restrição EXCLUDE | `ex_<tabela>_<descricao>` | `ex_faixa_horario_sobreposta` |

---

## 7. Configuração e Docker

### 7.1 Variáveis de ambiente

- Formato: **`PESAGEM_<GRUPO>_<NOME>`**, `UPPER_SNAKE_CASE`, com unidade quando houver.
- Grupos: `GERAL`, `PATIO`, `BANCO`, `CAMERA`, `LPR`, `BALANCA`, `CANCELA`, `SEGURANCA`, `TEMPO_REAL`, `OPERACAO` (tempos-limite das etapas, spec 015), `PESAGEM` (regras de peso, spec 002), `RETENCAO` (seguem a tabela do `AMBIENTE.md` §8).
- Exemplos de **formato** (não são contrato; nomes reais são definidos na spec): `PESAGEM_BALANCA_MODO`, `PESAGEM_BALANCA_TIMEOUT_MS`, `PESAGEM_LPR_LIMIAR_CONFIANCA`.
- Modo de equipamento: valores `SIMULADO` | `REAL`, com `SIMULADO` como padrão seguro.
- Todas listadas em `.env.exemplo` sem valores secretos. `.env` nunca é versionado.

### 7.2 Docker

| Elemento | Padrão | Exemplo |
|---|---|---|
| Arquivo de orquestração | `compose.yaml` na raiz | — |
| Serviço | minúsculo, `kebab-case` | `backend`, `frontend`, `db`, `simulador-balanca` |
| Volume | `<projeto>-<conteudo>` | `pesagem-dados-db`, `pesagem-modelos-ocr` |
| Dockerfile | um por serviço, dentro da pasta do serviço | `backend/Dockerfile` |
| Perfis | `dev`, `teste`, `hardware-real` | — |

Nenhum arquivo Docker é criado antes de spec/plano aprovados (`AMBIENTE.md` §7.2).

---

## 8. Frontend — TypeScript

Framework: React + Vite + React Router, com Tailwind CSS v4 e TypeScript estrito (D-03, ADR-0007). Ferramentas: ADR-0008. Onde o React ou as ferramentas impõem um nome, ele prevalece (G-2).

| Elemento | Padrão | Exemplo |
|---|---|---|
| Arquivo comum | `kebab-case.ts` | `cliente-api.ts`, `formatar-peso.ts` |
| Arquivo de componente | `PascalCase.tsx` | `PainelOperacao.tsx`, `VisorRoi.tsx` |
| Arquivo de página | `PascalCase.tsx` em `src/paginas/`, com prefixo `Pagina` | `PaginaLogin.tsx` |
| Hook | `use` + nome em português, `camelCase` (o prefixo `use` é exigido pelo React e pelo lint) | `useSessao`, `useConexaoEventos` |
| Variável, função | `camelCase` | `pesoLiquido`, `carregarAgendamentos()` |
| Tipo, interface, componente | `PascalCase` | `Pesagem`, `ResultadoLeitura` |
| Constante de módulo | `UPPER_SNAKE_CASE` | `INTERVALO_ATUALIZACAO_MS` |
| Tipos que espelham a API | campos em `snake_case` **iguais ao JSON** (não converter) | `pesagem.peso_liquido_kg` |
| Textos de interface | português com acentos | "Aguardando identificação" |
| Arquivos de configuração | nome exigido pela ferramenta, na raiz de `frontend/` | `vite.config.ts`, `eslint.config.js`, `tsconfig.json` |
| Ponto de entrada | `src/main.tsx` (convenção do Vite) | — |

Converter `snake_case` ↔ `camelCase` na borda é proibido sem decisão: gera divergência entre API, banco e tela.

---

## 9. Testes

Ferramenta: **pytest** (ADR-0003, D-11 do backend). Padrão de nomes:

| Elemento | Padrão | Exemplo |
|---|---|---|
| Arquivo (Python) | `test_<modulo>.py`, com nome **único em todo `tests/`** (o `mypy` recusa dois módulos com o mesmo nome); se repetir, acrescente o equipamento ou a camada | `test_normalizacao.py`, `test_balanca_simulada.py` |
| Marcador `avaliacao` | teste que usa o EasyOCR real e o acervo; fora da execução padrão, roda com `pytest -m avaliacao` | `test_avalia_conjunto_de_referencia` |
| Função de teste | `test_<comportamento>_<condicao>` | `test_nao_autoriza_quando_confianca_abaixo_do_limiar` |
| Rastreabilidade | docstring ou marcador citando os IDs | `"""CA-003, RF-007"""` |
| Arquivo (frontend) | `<arquivo>.test.ts` ou `<arquivo>.test.tsx`, ao lado do arquivo testado (ADR-0008) | `formatar-peso.test.ts` |
| Dados de teste de imagem | sequencial, sem placa no nome; resultado esperado só no gabarito (fora do repositório); imagens dos testes automáticos são sintéticas, geradas pelo próprio teste | `img-0001.jpg` → linha no `gabarito.csv` |
| Quadros seriais de exemplo | `<equipamento>-<situacao>-NN.<ext>` em `docs/equipamentos/` ou fixtures | `balanca-estavel-01.txt` |

Nomes de teste descrevem **comportamento esperado**, não implementação (`test_rejeita_quadro_malformado`, e não `test_parser_2`).

---

## 10. Glossário de nomes (fonte única)

Use **exatamente** estes termos em identificadores. Novos termos entram aqui e em `specs/glossario.md` antes de aparecer no código.

| Conceito | Identificador | Não usar |
|---|---|---|
| Agendamento | `agendamento` | `schedule`, `reserva` |
| Pesagem (a operação inteira registrada) | `pesagem` | `weighing`, `pesagem_operacao` |
| Operação logística (fluxo/máquina de estados) | `operacao` | `processo`, `fluxo` |
| Tipo de operação | `tipo_operacao` (`CARGA`/`DESCARGA`) | `tipo` |
| Peso inicial / final | `peso_inicial_kg` / `peso_final_kg` | `peso1`, `peso_entrada` |
| Peso líquido | `peso_liquido_kg` | `net_weight` |
| Tolerância de movimentação | `tolerancia_movimentacao_kg` | `margem`, `folga` |
| Classificação do peso líquido | `COM_MOVIMENTACAO` / `SEM_MOVIMENTACAO` / `NEGATIVO_FORA_TOLERANCIA` | `VAZIO`, `ZERADO` |
| Tara / peso bruto | `tara_kg` / `peso_bruto_kg` | `peso_vazio` |
| Situação (estado persistido) | `situacao` | `state`, `estado_atual` |
| Situação de onde a operação parou para intervenção | `situacao_anterior` | `estado_previo` |
| Motivo da parada para intervenção | `motivo_intervencao` | `erro`, `causa` |
| Versão da operação (concorrência) | `versao` | `revision` |
| Ação pedida pela máquina de estados | `acao_pedida` | `side_effect` |
| Sessão de usuário | `sessao` | `session` |
| Usuário do sistema | `usuario` | `user` |
| Perfil de acesso | `perfil` | `role` |
| Permissão de acesso | `permissao` | `role`, `grant` |
| Agendamento pelo motorista, sem login | `autoatendimento` | `self_service`, `kiosk` |
| Código da nota informado na descarga | `codigo_nota` | `chave`, `nf` |
| CPF com parte oculta | `cpf_mascarado` | `cpf_parcial` |
| Status do agendamento | `status` (já no banco) | — |
| Faixa de horário (janela do dia com capacidade) | `faixa_horario` | `slot`, `janela`, `turno` |
| Agendamento ainda não encerrado (`AGENDADO`, `EM_ANDAMENTO`) | agendamento aberto | `ativo` |
| Quem originou o agendamento (`USUARIO`, `AUTOATENDIMENTO`) | `origem` | `canal`, `fonte` |
| Fuso que define o "hoje" e os horários das faixas | `PESAGEM_PATIO_FUSO` | — |
| Motivo do cancelamento do agendamento | `motivo_cancelamento` | `justificativa` |
| Placa lida pelo OCR (bruta) | `placa_lida` | `texto_ocr` |
| Placa após normalização | `placa_normalizada` | `placa_limpa` |
| Chave de comparação de placa (antiga ↔ Mercosul) | `chave_comparacao` | `placa_canonica`, `placa_convertida` |
| Confiança do OCR (de 0 a 1, 3 casas, truncada para baixo) | `confianca` | `score` |
| Texto lido pelo OCR, já com a confiança validada | `texto_lido` | `texto_ocr` |
| Candidato a placa (texto + confiança, entrada da seleção) | `candidato_placa` | `palpite` |
| Placa escolhida pela seleção | `placa_selecionada` | `placa_vencedora` |
| Número de tentativas de leitura ou de comando | `tentativas` | `retries` |
| Conjunto real de imagens de avaliação (fora do repositório) | `acervo` | `dataset` |
| Arquivo com o resultado esperado de cada imagem | `gabarito` | `ground_truth` |
| Região de interesse | `roi` | `regiao` |
| Resultado da decisão de entrada | `decisao` (`AUTORIZADA`, `RETORNO_ACEITO`, `NAO_AUTORIZADA`) | `resultado_autorizacao` |
| Motivo de não autorizar | `MotivoNaoAutorizacao` / `motivo` | `causa` |
| Fonte e leitura de posição na balança | `FontePosicao`, `LeituraPosicao`, `CenarioPosicao` | `sensor_posicao` |
| Pesagem cancelada com caminhão ainda na balança | `aguarda_liberacao_balanca` | `pendente_saida` |
| Instante em que a operação entrou na situação atual | `situacao_desde` | `entrou_em` |
| Liberação de caminhão de operação cancelada na balança | `liberacao_caminhao` | `saida_forcada` |
| Ações manuais que a situação atual permite (para a tela) | `acoes_disponiveis` | `allowed_actions` |
| Estado consolidado dos dispositivos (para a tela) | `EstadoDispositivos` | `status_hardware` |
| Imagem atual de uma câmera (diagnóstico, sem gravar) | `imagem_atual` | `frame_ao_vivo` |
| Registro de histórico da operação (transições, comandos, intervenções) | `evento_operacao` | `log_operacao` |
| Tentativa de login ou de autoatendimento (limite) | `tentativa_acesso` | `rate_limit` |
| Imagem salva de uma decisão (RN-022) | `imagem_decisao` | `foto`, `snapshot` |
| Balança / cancela / câmera | `balanca` / `cancela` / `camera` | `scale`, `gate` |
| Ponto de controle | `ponto_controle` | `estacao` |
| Liberação manual | `liberacao_manual` | `override` |
| Leitura de placa | `leitura_placa` | `reconhecimento` |
| Evento de cancela | `evento_cancela` | `log_cancela` |
| Produto | `produto` | `mercadoria`, `item` |
| Tipo de veículo | `tipo_veiculo` | `categoria_veiculo` |

---

## 11. Instruções ao agente

1. **Antes de criar qualquer arquivo ou pasta**, localize o lugar dele na seção 2. Se não houver lugar previsto, **pare e pergunte**; não crie pasta nova nem arquivo "genérico".
2. **Antes de nomear** um conceito do domínio, consulte o glossário (§10). Se o termo não existe, proponha-o ao autor e registre em `specs/glossario.md` e aqui, na mesma mudança.
3. **Respeite as regras de dependência** (P-4 a P-6). Se uma tarefa parecer exigir importar `serial`, `cv2` ou `easyocr` fora da camada certa, a tarefa está mal desenhada: pergunte.
4. **Itens [PENDENTE] não são resolvidos por convenção de nome.** Ex.: não crie `/api/v1` nem arquivos de framework de frontend antes da decisão correspondente.
5. **Não renomeie** arquivos, tabelas, colunas, rotas ou variáveis existentes para "adequar ao padrão" sem pedido explícito; liste as divergências no relato e proponha a correção.
6. **Divergência entre este arquivo e o repositório**: avise o autor e proponha atualizar um dos dois; não ajuste silenciosamente.
7. **Ao concluir uma tarefa**, inclua no relato (`AGENTS.md` §11) uma linha "Convenções": confirmado que os nomes seguem este arquivo, ou quais exceções foram feitas e por quê.

### 11.1 Checklist rápido

- [ ] Identificadores em português, sem acentos; inglês só para termos técnicos.
- [ ] Grandezas com unidade (`_kg`, `_ms`); instantes com `_em`.
- [ ] Arquivo/pasta no local previsto na §2.
- [ ] `dominio/` sem I/O e sem imports de infraestrutura.
- [ ] Estados em `UPPER_SNAKE_CASE`, idênticos aos do banco e da spec.
- [ ] Rotas em plural `kebab-case`; JSON em `snake_case`.
- [ ] Variáveis de ambiente `PESAGEM_<GRUPO>_<NOME>`, modo padrão `SIMULADO`.
- [ ] Testes nomeados pelo comportamento e citando `CA-`/`RF-`.
