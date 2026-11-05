# Spec 004 — Camada de dispositivos

- **Trilha:** Backend
- **Status:** Implementada (BE-302, 2026-10-29; aceita pelo autor em 2026-10-29). Aprovada pelo autor em 2026-10-29 ("aprovado, pode prosseguir", com o RF-030 e a não repetição após `FALHA` da cancela)
- **Data:** 2026-10-29
- **Tarefa:** BE-301 (spec); implementação na BE-302 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-011, RF-013, RF-019 (parcial), RF-030, RNF-003, RN-005, RN-007, RNF-009
- **Código:** `backend/src/pesagem/dispositivos/` (`CONVENCOES.md` §2, §4.4)

---

## 1. Contexto e origem

- Pelo artigo, o sistema lê o peso da balança e comanda as cancelas por RS232 com PySerial. A porta, a taxa de transmissão e o timeout são configuráveis, e sem equipamento físico o comportamento é **simulado** **[ARTIGO §1, §2, §3.4, §4]** (RF-011, RF-013, RNF-003).
- O protocolo, os quadros e os comandos **não são conhecidos** (Q-01, `AMBIENTE.md` §11.2). Por isso, esta spec define só as **interfaces**, as **regras comuns** (retentativa, estado) e os **simuladores**. `BalancaSerial`, `CancelaSerial` e `parser_quadro.py` ficam **bloqueados** até a Q-01 ter resposta e existirem quadros reais em `docs/equipamentos/` (BE-301).
- Decisões que já valem:
  - modo e parâmetros de comunicação vêm de variáveis de ambiente, não do banco (C-002 item 7, `AMBIENTE.md` §8);
  - o resultado de um comando de cancela é `CONFIRMADO`, `FALHA` ou `SEM_CONFIRMACAO`, e não um booleano (C-002 item 5);
  - as portas seriais pertencem a um único componente, em um único processo (ADR-0002);
  - há cancela de entrada e cancela de saída (Q-15).
- **Decisões do autor em 2026-10-29 (revisão desta spec):**
  - falhas do equipamento são **resultados**, não exceções (P-2);
  - quando o equipamento não responde, a pesagem **não avança** (P-4; confirma a RN-005);
  - quando não há resposta, **uma segunda tentativa** é permitida, nas cancelas e na balança (P-5);
  - **as cancelas têm um sensor de status, com cabo dedicado** (informação parcial da Q-01);
  - o sistema deve permitir **adicionar balanças diferentes, com protocolos diferentes** (P-6; detalhes em aberto, P-8);
  - a pesagem **só avança em caso de sucesso** (P-7).
- **Decisões do autor em 2026-10-29 (segunda rodada):**
  - as interfaces dos dispositivos são **assíncronas** (P-1). Isso decide em parte a D-05: os dispositivos não bloqueiam o laço de eventos da API;
  - os nomes das falhas da balança são `SEM_RESPOSTA`, `QUADRO_CORROMPIDO` e `DESCONECTADA` (P-4);
  - "diferentes balanças" quer dizer **diferentes modelos**, cada um com seu protocolo, escrito como código a partir do manual e de quadros reais e escolhido por configuração. Por enquanto há **uma balança e uma fila**; várias filas ao mesmo tempo ficam para depois (P-8);
  - sem segunda tentativa em `QUADRO_CORROMPIDO` e `DESCONECTADA`. Em `SEM_RESPOSTA`, o pedido é reenviado, porque às vezes a balança demora para estabilizar e é preciso pedir o valor de novo (P-9).
- **Decisões do autor em 2026-10-29 (terceira rodada):**
  - o desenvolvimento segue **no modo simulado**, que continua sendo o padrão. O modo real será adicionado **quando tudo estiver testado** (P-3, opção a);
  - a cancela recebe o comando de novo **quando o sensor está funcionando e mostra que ela não se moveu**. Com o sensor sem resposta, não há reenvio (P-10).

## 2. Objetivo

1. Definir as interfaces assíncronas `Balanca` e `Cancela`, que a orquestração usa sem saber se o equipamento é real ou simulado, nem qual é o modelo ou protocolo.
2. Definir a interface `ProtocoloBalanca`, que isola o que muda de um modelo de balança para outro.
3. Definir a política de retentativa (no máximo 2 tentativas, só quando não há resposta) e a regra do estado da cancela pelo sensor.
4. Definir `BalancaSimulada` e `CancelaSimulada`, com cenários determinísticos para os testes automatizados e para a demonstração.
5. Definir como o modo (`SIMULADO`/`REAL`) é escolhido, com `SIMULADO` como padrão e o hardware real só com configuração explícita.

## 3. Fora de escopo

- Várias balanças e várias filas ao mesmo tempo (P-8; futuro).
- `BalancaSerial`, `CancelaSerial`, os protocolos concretos de cada modelo, `parser_quadro.py`, os parâmetros seriais e os valores de timeout e de intervalo. Ficam bloqueados pela Q-01.
- Decidir **quando** ler o peso ou abrir uma cancela, e se é permitido. Isso é da máquina de estados (BE-201) e da orquestração (BE-601). Elas aplicam a regra "só avança com sucesso" (§8).
- Aceitar o peso: estabilidade e faixa já estão na spec 002, que recebe as leituras.
- Registro de eventos (`evento_cancela`, RF-019) e tela de estado dos dispositivos (RF-023). Ficam com a orquestração, a persistência e o contrato CT-105. Esta camada devolve o número de tentativas para que esses registros sejam possíveis.
- Ler as variáveis de ambiente e o cadastro de equipamentos. Esta spec define a regra de escolha do modo a partir do valor já lido.
- O restante da D-05: onde roda o OCR e a captura de vídeo. Esta spec só decide que os dispositivos são assíncronos (P-1).
- Sensores de presença e perímetro da balança (RF-027, Q-17).

## 4. Atores

Nenhum ator humano. Quem chama é a orquestração (BE-601). Os testes e a demonstração usam os simuladores.

## 5. Dados e interfaces **[PROPOSTA]**

Os nomes seguem o `CONVENCOES.md` §4.4 e §4.5.

### 5.1 Balança

| Nome | Conteúdo |
|---|---|
| `Balanca` (interface) | `async def ler_peso() -> LeituraBalanca \| FalhaBalanca`. Uma chamada = **uma leitura**, com no máximo 2 tentativas (§6.2). A interface não depende do modelo (P-6, P-8). |
| `ProtocoloBalanca` (interface) | O que muda de um modelo para outro, **sem I/O**: se é preciso enviar um pedido e qual é ele, e como interpretar um quadro recebido (peso ou quadro corrompido). Cada modelo é uma implementação em `dispositivos/balanca/protocolos/<modelo>.py`, testada com quadros reais em `docs/equipamentos/`. **Nenhum protocolo concreto existe ainda (Q-01).** |
| `LeituraBalanca` | `peso_kg: Decimal`, `lida_em: datetime` (com fuso) e `tentativas: int` (1 ou 2). Tipo próprio da camada, convertido para `LeituraPeso` pela orquestração (P-6: `dispositivos` não importa `dominio`). |
| `FalhaBalanca` | `motivo: MotivoFalhaBalanca` e `tentativas: int`. |
| `MotivoFalhaBalanca` | `SEM_RESPOSTA` (nenhum quadro completo dentro do timeout), `QUADRO_CORROMPIDO` (dados recebidos, mas fora do formato) ou `DESCONECTADA` (a porta não está disponível). Ver P-4. |

### 5.2 Cancela

| Nome | Conteúdo |
|---|---|
| `Cancela` (interface) | `async def abrir() -> ResultadoComandoCancela`, `async def fechar() -> ResultadoComandoCancela` e `async def consultar_estado() -> EstadoCancela`. |
| `ResultadoComandoCancela` | `resultado: ResultadoComando` e `tentativas: int` (0, 1 ou 2; 0 quando nenhum comando foi enviado). |
| `ResultadoComando` | `CONFIRMADO` (o sensor mostra a posição pedida), `FALHA` (o equipamento respondeu que não executou) ou `SEM_CONFIRMACAO` (o sensor não mostrou a posição pedida dentro do timeout, ou não respondeu). |
| `EstadoCancela` | `ABERTA`, `FECHADA` ou `DESCONHECIDO`. |

Regras do estado (P-7, revisada com o sensor):
- O estado vem **sempre do sensor de status**. Ele nunca é deduzido do comando enviado.
- Se o sensor não responder, o estado é `DESCONHECIDO`. O sistema nunca supõe que a cancela está fechada.
- Um comando só é `CONFIRMADO` quando o sensor mostra a posição pedida.

### 5.3 Modo

| Nome | Conteúdo |
|---|---|
| `ModoDispositivo` | `SIMULADO` ou `REAL`, escolhido separadamente para a balança e para as cancelas (variáveis no formato `PESAGEM_BALANCA_MODO` e `PESAGEM_CANCELA_MODO`, `CONVENCOES.md` §7; nomes finais na spec de configuração; ver P-8 para várias balanças). |
| Protocolo da balança | Variável no formato `PESAGEM_BALANCA_PROTOCOLO`, com o nome de um protocolo implementado. Obrigatória no modo `REAL`; um nome desconhecido → `ErroConfiguracaoDispositivo`. |
| `selecionar_modo(valor: str \| None) -> ModoDispositivo` | Ausente ou vazio → `SIMULADO`. `"SIMULADO"` → `SIMULADO`. `"REAL"` → `REAL`. Qualquer outro valor (incluindo minúsculas e espaços) → `ErroConfiguracaoDispositivo`. |

## 6. Comportamento normal

### 6.1 Leitura e comando

- Todas as operações são `async`. A implementação real usa o PySerial (síncrono) dentro de `asyncio.to_thread`, **sem dependência nova** (P-1). Toda operação tem timeout (`AGENTS.md` §7.3).
- Os testes chamam as funções assíncronas com `asyncio.run` dentro de testes comuns do pytest, **sem plugin novo** (o ADR-0003 só permite o pytest-cov).

- **Balança:** `ler_peso()` pede uma leitura. Se ela chega, devolve `LeituraBalanca`.
- **Cancela:** `abrir()`/`fechar()` enviam o comando e esperam o sensor mostrar a posição pedida, até o timeout.
  - Se o sensor **já** mostra a posição pedida antes do envio, nenhum comando é enviado: o resultado é `CONFIRMADO` com `tentativas = 0`.
  - Se o sensor mostra a posição pedida dentro do timeout: `CONFIRMADO`.

### 6.2 Segunda tentativa (P-5)

| Situação na 1ª tentativa | Segunda tentativa? | Motivo |
|---|---|---|
| Balança: `SEM_RESPOSTA` | **Sim**, uma vez | Decisão do autor: às vezes a balança demora para estabilizar e é preciso pedir o valor de novo (P-9). |
| Balança: `QUADRO_CORROMPIDO` ou `DESCONECTADA` | Não | Decisão do autor (P-9). |
| Cancela: sem confirmação, e o sensor responde mostrando a **outra** posição | **Sim**, reenvia o comando uma vez | Decisão do autor (P-10). O sensor prova que a cancela não se moveu: o reenvio **não é cego** (`AGENTS.md` §7.1.4). |
| Cancela: sem confirmação, e o **sensor não responde** | **Não** | Sem o sensor, não há como saber a posição; reenviar seria cego. Resultado `SEM_CONFIRMACAO`, estado `DESCONHECIDO`. Decisão do autor (P-10). |
| Cancela: `FALHA` (o equipamento respondeu que não executou) | Não | O equipamento respondeu; a decisão passa ao operador. |

- Nunca há mais de **2 tentativas** por chamada. Se a balança continuar sem estabilizar, quem chama de novo é a orquestração, que junta as leituras e aplica a spec 002; quanto tempo ela espera no total é da BE-601.
- Entre as tentativas há um intervalo vindo de configuração, **sem valor padrão** (depende do equipamento, Q-01). Os simuladores não esperam esse intervalo.
- O resultado devolve `tentativas`, para o registro de auditoria (RF-019).

### 6.3 Simuladores

- Os simuladores ficam em `dispositivos/<equipamento>/simulada.py` (P-8 do `CONVENCOES.md`), não fazem I/O real e **não esperam tempo de verdade**: um `SEM_RESPOSTA` simulado é devolvido na hora. Assim os testes ficam rápidos e determinísticos.
- O relógio é **injetado** (uma função que devolve `datetime` com fuso), e o simulador o usa para preencher `lida_em`. Os testes usam um relógio controlado.
- O cenário é definido na criação e pode ser trocado com `definir_cenario(...)`, para testes de ponta a ponta que mudam de situação no meio da operação.

**`CenarioBalanca`:**

| Cenário | O que `ler_peso()` devolve |
|---|---|
| `ESTAVEL` | Sempre o `peso_kg` configurado. |
| `INSTAVEL` | Alterna entre `peso_kg − amplitude_kg` e `peso_kg + amplitude_kg`, começando por `peso_kg − amplitude_kg`. |
| `SEM_RESPOSTA` | `FalhaBalanca(SEM_RESPOSTA, tentativas=2)`. |
| `SEM_RESPOSTA_NA_PRIMEIRA` | A 1ª tentativa não responde e a 2ª devolve o `peso_kg` (`tentativas=2`). Testa a segunda tentativa. |
| `QUADRO_CORROMPIDO` | `FalhaBalanca(QUADRO_CORROMPIDO, tentativas=1)`. |
| `DESCONECTADA` | `FalhaBalanca(DESCONECTADA, tentativas=1)`. |

Peso fora da faixa, negativo ou com muitas casas decimais é só um `peso_kg` configurado no cenário `ESTAVEL`: o simulador **não** valida o peso, porque quem aceita ou rejeita é a regra da spec 002.

**`CenarioCancela`** (a cancela simulada guarda uma posição física simulada; o sensor simulado a informa):

| Cenário | `abrir()` / `fechar()` | Estado depois |
|---|---|---|
| `CONFIRMADO` | Move na 1ª tentativa → `CONFIRMADO`, `tentativas=1` | A posição pedida |
| `CONFIRMADO_NA_SEGUNDA` | Não move na 1ª, move na 2ª → `CONFIRMADO`, `tentativas=2` | A posição pedida |
| `NAO_MOVE` | Nunca move → `SEM_CONFIRMACAO`, `tentativas=2` | A posição anterior, informada pelo sensor |
| `FALHA` | O equipamento responde que falhou → `FALHA`, `tentativas=1` | A posição anterior, informada pelo sensor |
| `SENSOR_SEM_RESPOSTA` | `SEM_CONFIRMACAO`, `tentativas=1` | `DESCONHECIDO` |

- A posição inicial é configurada na criação (`ABERTA` ou `FECHADA`), para os testes cobrirem os dois casos.
- O simulador guarda a lista dos comandos enviados (`ABRIR`/`FECHAR`), na ordem. Assim um teste verifica quantos comandos foram enviados e que **nenhum** foi enviado numa situação proibida.

### 6.4 Escolha das implementações

- `SIMULADO` cria `BalancaSimulada` / `CancelaSimulada`.
- `REAL` levanta `ErroModoIndisponivel` enquanto `BalancaSerial` e `CancelaSerial` não existirem. O modo real será adicionado depois que tudo estiver testado no simulado, numa spec própria (P-3). O sistema não inicia, e **nunca** cai para o simulado em silêncio.

## 7. Comportamento em falha

| Situação | Resultado | Observação |
|---|---|---|
| Balança sem resposta nas 2 tentativas | `FalhaBalanca(SEM_RESPOSTA, tentativas=2)` | Nenhum peso é inventado; a pesagem não avança (RN-005, P-4). |
| Quadro da balança corrompido | `FalhaBalanca(QUADRO_CORROMPIDO)` | — |
| Porta da balança indisponível | `FalhaBalanca(DESCONECTADA)` | — |
| Cancela responde que falhou | `FALHA`; estado pelo sensor | Não repete; a operação não avança (P-7). |
| Cancela não se move nas 2 tentativas | `SEM_CONFIRMACAO`; estado pelo sensor | A operação não avança. |
| Sensor da cancela não responde | `SEM_CONFIRMACAO`; estado `DESCONHECIDO` | Sem segunda tentativa (reenvio seria cego). |
| Modo com valor inválido | `ErroConfiguracaoDispositivo` | Na partida; nunca escolhe um modo "parecido". |
| Modo `REAL` sem implementação real | `ErroModoIndisponivel` | Na partida; nunca usa o simulado no lugar. |
| Chamadas simultâneas ao mesmo dispositivo | Não suportado; a orquestração é a única dona (ADR-0002) | A spec da orquestração garante a serialização. |

Os erros `ErroConfiguracaoDispositivo` e `ErroModoIndisponivel` derivam de `ErroDispositivo` (`CONVENCOES.md` §4.5). Falhas **de operação** do equipamento são resultados, não exceções (P-2).

## 8. Regras de negócio

- **RN-005 (confirmada pelo autor, P-4):** falha da balança nunca gera peso, e a pesagem não avança.
- **RN-007 (política definida aqui, P-5):** comando sem confirmação não é sucesso; no máximo 2 tentativas, só quando não houve resposta, e só com o sensor provando que a cancela não se moveu.
- **Só avança com sucesso (P-7):** a máquina de estados (BE-201) e a orquestração (BE-601) só avançam a operação com `LeituraBalanca` (depois aceita pela spec 002) ou `CONFIRMADO`. Qualquer outro resultado mantém a etapa atual e sinaliza a falha.
- **RNF-003:** `SIMULADO` é o padrão; o real só com `REAL` explícito.

## 9. Estados afetados

Só o `EstadoCancela` de cada cancela, lido do sensor. O estado da operação é da BE-201.

## 10. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | `BalancaSimulada` em `ESTAVEL` devolve sempre o `peso_kg` configurado, com `lida_em` do relógio injetado e `tentativas=1`. |
| CA-002 | Em `INSTAVEL`, devolve `peso − amplitude`, `peso + amplitude`, `peso − amplitude`, ..., e essa série é rejeitada como `INSTAVEL` pela spec 002 quando a amplitude passa do limite. |
| CA-003 | `SEM_RESPOSTA` devolve `FalhaBalanca(SEM_RESPOSTA, tentativas=2)`; `SEM_RESPOSTA_NA_PRIMEIRA` devolve a leitura com `tentativas=2`. |
| CA-004 | `QUADRO_CORROMPIDO` e `DESCONECTADA` devolvem `FalhaBalanca` com o motivo certo e `tentativas=1`, nunca um peso. |
| CA-005 | Os simuladores não esperam tempo real: 1.000 chamadas em `SEM_RESPOSTA` terminam em menos de 1 s. |
| CA-006 | `definir_cenario` muda o comportamento a partir da chamada seguinte. |
| CA-007 | Em `CONFIRMADO`, `abrir()` → `CONFIRMADO`, `tentativas=1`, estado `ABERTA`; `fechar()` → `FECHADA`; um comando enviado por chamada. |
| CA-008 | Em `CONFIRMADO_NA_SEGUNDA`, o resultado é `CONFIRMADO` com `tentativas=2` e exatamente 2 comandos enviados. |
| CA-009 | Em `NAO_MOVE`, o resultado é `SEM_CONFIRMACAO`, `tentativas=2`, 2 comandos enviados, e o estado é a posição anterior. |
| CA-010 | Em `FALHA`, o resultado é `FALHA`, `tentativas=1`, 1 comando enviado. |
| CA-011 | Em `SENSOR_SEM_RESPOSTA`, o resultado é `SEM_CONFIRMACAO`, `tentativas=1`, 1 comando enviado, e o estado é `DESCONHECIDO`. |
| CA-012 | Se o sensor já mostra a posição pedida, nenhum comando é enviado e o resultado é `CONFIRMADO` com `tentativas=0`. |
| CA-013 | Nenhuma chamada envia mais de 2 comandos, em nenhum cenário. |
| CA-014 | `selecionar_modo(None)` e `selecionar_modo("")` → `SIMULADO`; `"SIMULADO"` → `SIMULADO`; `"REAL"` → `REAL`; `"real"`, `" REAL"`, `"SIMULADA"`, `"X"` → `ErroConfiguracaoDispositivo`. |
| CA-015 | Criar dispositivos em `REAL` levanta `ErroModoIndisponivel`, e nenhum simulador é criado. |
| CA-016 | O teste de arquitetura (spec 001) passa: `dominio` não importa `dispositivos`, e `dispositivos` não importa `dominio` (P-6); nenhum arquivo desta spec importa `serial`. |
| CA-017 | Os simuladores satisfazem as interfaces assíncronas, e o mypy estrito confirma. |
| CA-018 | Com `REAL`, um `PESAGEM_BALANCA_PROTOCOLO` ausente ou desconhecido levanta `ErroConfiguracaoDispositivo`. |

## 11. Impacto

- **Código:** cria `dispositivos/balanca/` (`interface.py`, `tentativas.py`, `simulada.py`), `dispositivos/cancela/` (`interface.py`, `tentativas.py`, `simulada.py`), `dispositivos/modo.py` e `dispositivos/erros.py`. Os arquivos `tentativas.py` (acrescentados na BE-302) guardam a política da §6.2, para a implementação real futura usar a mesma regra testada com os simuladores. Sem dependência nova: PySerial só entra com a implementação real. A organização dos protocolos de balança depende da P-8.
- **Teste de arquitetura:** precisa reconhecer a camada `dispositivos` e a regra `dispositivos` ↛ `dominio`.
- **Esquema (BE-502):** `evento_cancela.resultado` com `CONFIRMADO`/`FALHA`/`SEM_CONFIRMACAO` (C-002 item 5) e um campo para `tentativas`. Várias balanças com protocolos diferentes (P-8) pedem o protocolo no cadastro da balança. O `endereco_ip` continua dependendo da Q-01 (C-002 item 8).
- **Requisitos:** a P-8 traz um requisito novo, o RF-030 (aprovado em 2026-10-29): suportar diferentes modelos de balança, cada um com seu protocolo escolhido por configuração, com uma balança e uma fila por vez. Registrado em `requisitos.md`. A Q-01 tem uma resposta parcial (sensor de status da cancela), a registrar no `AMBIENTE.md` §17.
- **Glossário e `CONVENCOES.md` §10:** termos `EstadoCancela`, `ResultadoComandoCancela`, `ModoDispositivo`, `DESCONECTADA`, `tentativas` entram com a aprovação.
- **`CONVENCOES.md` §4.4:** o exemplo de `CenarioBalanca` cita `TIMEOUT`; aqui ele se chama `SEM_RESPOSTA` (P-4). Sincronizar numa sessão da trilha A.
- **Segurança operacional:** estado pela leitura do sensor; reenvio só com o sensor provando que a cancela não se moveu; no máximo 2 tentativas; o modo real não é ativado por acidente nem trocado pelo simulado em silêncio.
- **Reversibilidade:** alta. Nada aciona hardware.

## 12. Perguntas

| ID | Pergunta | Situação |
|---|---|---|
| P-1 | Interfaces síncronas ou assíncronas? | **Respondida:** assíncronas. |
| P-2 | Falhas como resultados ou exceções? | **Respondida:** resultados. |
| P-3 | Modo padrão e implementação real. | **Respondida:** (a) simulado como padrão; o modo real entra depois que tudo estiver testado. O modelo do equipamento continua em aberto (Q-01). |
| P-4 | Nomes das falhas da balança. | **Respondida:** `SEM_RESPOSTA`, `QUADRO_CORROMPIDO`, `DESCONECTADA`. |
| P-5 | Retentativa. | **Respondida:** segunda tentativa quando não há resposta. As cancelas têm sensor de status com cabo dedicado. |
| P-6 | Tipo devolvido pela balança. | **Respondida:** tipo próprio da camada, independente do modelo. |
| P-7 | Estado da cancela. | **Respondida:** só avança com sucesso; o estado vem sempre do sensor. |
| P-8 | Várias balanças. | **Respondida:** diferentes modelos, protocolo como código, escolhido por configuração; uma balança e uma fila por vez. |
| P-9 | Quando não repetir na balança. | **Respondida:** não repete em `QUADRO_CORROMPIDO` e `DESCONECTADA`; repete em `SEM_RESPOSTA`. |
| P-10 | Cancela com o sensor sem resposta: reenviar o comando? | **Respondida:** reenvia só quando o sensor funciona e mostra que a cancela não se moveu; com o sensor sem resposta, não reenvia. |
