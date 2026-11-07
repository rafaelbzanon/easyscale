# Spec 029 — Dispositivos serial (transporte da balança)

- **Trilha:** Backend
- **Status:** Aprovada pelo autor em 2026-11-07
- **Data:** 2026-11-07
- **Tarefa:** BE-303/304 (Rivet) — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-013, RF-030, RNF-003, RN-005; `AGENTS.md` §7.3
- **Decisões:** spec 004 (interfaces, P-1 a P-9), ADR-0002 (um único dono da porta), spec 001 §8 (critério de versão)
- **Código:** `backend/src/pesagem/dispositivos/balanca/serial.py`, `dispositivos/balanca/protocolos/__init__.py`, `dispositivos/modo.py`, `config.py` (parte da balança), `main.py` (uma chamada, autorizada pelo Maestro em 2026-11-07)

---

## 1. Contexto e origem

- A spec 004 deixou `BalancaSerial`, `CancelaSerial` e os protocolos bloqueados pela Q-01 (modelo, quadros e comandos desconhecidos).
- **Decisão do autor em 2026-11-07:** liberar da Q-01 **só o transporte serial da balança e o encaixe do protocolo**, com a dependência PySerial. O resto da Q-01 continua aberto: modelo, protocolo concreto, valores seriais e tudo da cancela.
- Consequência: o modo `REAL` da balança passa a ter implementação, mas **continua sem subir** enquanto nenhum protocolo de modelo existir (o registro de protocolos está vazio).

## 2. Objetivo

1. `BalancaSerial`: implementa `Balanca` (spec 004 §5.1) sobre PySerial, com qualquer `ProtocoloBalanca`.
2. Acrescentar a `ProtocoloBalanca` o mínimo que o transporte precisa para saber onde termina um quadro.
3. Registro de protocolos (nome → classe), **vazio**, consultado por `PESAGEM_BALANCA_PROTOCOLO`.
4. Parâmetros seriais por configuração, sem valor padrão, lidos só em `REAL`.
5. Roteiro para integrar um modelo real (`docs/equipamentos/README.md`).

## 3. Fora de escopo

- Qualquer protocolo concreto, quadro de exemplo ou valor serial de equipamento (Q-01). Nada disso é inventado.
- `CancelaSerial` e `ProtocoloCancela` (P-1).
- Aceitação do peso (estabilidade, faixa): continua na spec 002. O transporte não descarta nem ajusta peso.
- Várias balanças ao mesmo tempo (spec 004, P-8).

## 4. Dependência

- **PySerial 3.5** (licença BSD), `dependencies` do `backend/pyproject.toml`. Aprovada pelo autor em 2026-11-07. Critério da spec 001 §8: é a estável mais recente, publicada em 2020-11-23 (bem mais de 14 dias antes); não há versão posterior no PyPI em 2026-11-07. Importada sem stubs (`# type: ignore[import-untyped]`, como o EasyOCR).
- Só `dispositivos/balanca/serial.py` importa `serial` (`CONVENCOES.md` P-6); protocolos não fazem I/O.

## 5. Interfaces

### 5.1 `ProtocoloBalanca` (spec 004 §5.1, acrescida)

| Método | Conteúdo |
|---|---|
| `montar_pedido() -> bytes \| None` | Já existia. Pedido de leitura, ou `None` se o modelo transmite sem pedido. |
| `extrair_quadro(recebido: bytes) -> bytes \| None` | **Novo.** Dado tudo o que chegou desde o início da tentativa, devolve o **primeiro quadro completo**, ignorando o que vier antes dele; `None` se ainda não há quadro completo. Quem sabe onde o quadro começa e termina é o protocolo; o transporte não supõe formato. |
| `interpretar_quadro(quadro: bytes) -> Decimal \| None` | Já existia. Peso em kg, ou `None` se o quadro está corrompido. |

### 5.2 `ParametrosSerial`

`porta`, `baud_rate`, `paridade`, `data_bits`, `stop_bits`, `timeout_ms`, `intervalo_tentativa_ms`. Valores no formato do próprio PySerial (§6.3).

### 5.3 Registro

`dispositivos/balanca/protocolos/__init__.py`: `PROTOCOLOS: dict[str, type[ProtocoloBalanca]] = {}`. Cada modelo futuro é um arquivo `protocolos/<modelo>.py` e uma linha no registro.

## 6. Comportamento normal

### 6.1 Uma tentativa (`BalancaSerial`)

1. Se a porta não está aberta, abre (uma vez; `exclusive=True`, para nenhum outro processo usar a mesma porta, ADR-0002).
2. **Descarta o que estiver no buffer de entrada**, para nunca usar um peso recebido antes do pedido.
3. Se `montar_pedido()` devolve bytes, envia (com `write_timeout` = `timeout_ms`).
4. Lê o que chegar, acumulando, e chama `extrair_quadro` a cada leitura, até o prazo de `timeout_ms` desde o início da leitura.
5. Quadro completo → `interpretar_quadro`: peso → `PesoRecebido(peso, relógio())`; `None` → `QUADRO_CORROMPIDO`.
6. O que sobra depois do quadro é descartado com o buffer da próxima tentativa (passo 2).

O PySerial (síncrono) roda em `asyncio.to_thread` (spec 004 §6.1). O relógio é injetado.

### 6.2 Tentativas

A política é a da spec 004 §6.2 (`tentativas.py`, sem mudança): só `SEM_RESPOSTA` tem segunda tentativa, depois de esperar `intervalo_tentativa_ms`.

### 6.3 Configuração (só com `PESAGEM_BALANCA_MODO=REAL`)

| Variável | Valores aceitos |
|---|---|
| `PESAGEM_BALANCA_PROTOCOLO` | nome registrado em `PROTOCOLOS` (hoje nenhum) |
| `PESAGEM_BALANCA_PORTA` | caminho ou URL do PySerial (ex. de formato: `/dev/ttyUSB0`) |
| `PESAGEM_BALANCA_BAUD_RATE` | uma de `serial.Serial.BAUDRATES` |
| `PESAGEM_BALANCA_PARIDADE` | `N`, `E`, `O`, `M`, `S` (letras do PySerial) |
| `PESAGEM_BALANCA_DATA_BITS` | `5`, `6`, `7`, `8` |
| `PESAGEM_BALANCA_STOP_BITS` | `1`, `1.5`, `2` |
| `PESAGEM_BALANCA_TIMEOUT_MS` | inteiro de 1 a 86.400.000 |
| `PESAGEM_BALANCA_INTERVALO_TENTATIVA_MS` | idem; é o intervalo sem valor padrão da spec 004 §6.2 |

Nenhuma tem valor padrão. Em `SIMULADO` nenhuma é lida.

## 7. Comportamento em falha

| Situação | Resultado | Depois |
|---|---|---|
| Porta não abre (inexistente, sem permissão, em uso) | `DESCONECTADA` | Próxima chamada tenta abrir de novo, uma vez. |
| Erro de E/S com a porta aberta | `DESCONECTADA` | Fecha a porta; próxima chamada reabre, uma vez. |
| Pedido não enviado dentro do `write_timeout` | `SEM_RESPOSTA` | Segunda tentativa pela política. |
| Nenhum quadro completo no prazo (inclusive só lixo ou quadro pela metade) | `SEM_RESPOSTA` | Idem. |
| Quadro completo que o protocolo não interpreta | `QUADRO_CORROMPIDO` | Sem segunda tentativa. |
| `PESAGEM_BALANCA_PROTOCOLO` ausente ou fora do registro (hoje: qualquer nome) | `ErroConfiguracaoDispositivo` na partida | O backend não sobe; nunca cai para o simulado. |
| Parâmetro serial ausente ou fora dos valores aceitos | `ErroConfiguracao` na partida (cita o nome, nunca o valor) | Idem. |

Nunca há peso inventado, ajustado ou reaproveitado de um buffer antigo (RN-005, `AGENTS.md` §7.2).

## 8. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | Com `loop://` e o protocolo de teste, um quadro completo vira `LeituraBalanca` com o peso, `lida_em` do relógio injetado e `tentativas=1`. |
| CA-002 | Quadro que chega em pedaços é montado e lido. |
| CA-003 | Lixo antes do quadro é ignorado pelo protocolo; dados velhos no buffer antes da tentativa não são usados. |
| CA-004 | Sem quadro no prazo: `FalhaBalanca(SEM_RESPOSTA, tentativas=2)`, com o pedido enviado duas vezes. |
| CA-005 | Quadro que o protocolo não interpreta: `FalhaBalanca(QUADRO_CORROMPIDO, tentativas=1)`. |
| CA-006 | Porta inexistente: `FalhaBalanca(DESCONECTADA, tentativas=1)`. |
| CA-007 | Depois de `DESCONECTADA`, a chamada seguinte reabre a porta e lê; com a porta aberta, ela não é reaberta. |
| CA-008 | O pedido do protocolo é enviado antes de cada tentativa; sem pedido, nada é escrito. |
| CA-009 | Com o registro vazio, `REAL` recusa a partida com `ErroConfiguracaoDispositivo`, mesmo com todos os parâmetros seriais válidos. |
| CA-010 | Em `REAL`, cada parâmetro serial ausente ou inválido gera `ErroConfiguracao` com o nome da variável; em `SIMULADO` nenhum é exigido. |
| CA-011 | Teste de camadas: só `dispositivos/balanca/serial.py` importa `serial`. |

O protocolo de teste existe **só em `tests/`**; nenhum protocolo é criado em `src/`.

## 9. Impacto

- **Código:** novo `serial.py` e `protocolos/__init__.py`; `interface.py` ganha `extrair_quadro`; `modo.py` cria a `BalancaSerial` (assinatura de `criar_balanca` muda); `config.py` lê os parâmetros; `main.py` passa a configuração.
- **Spec 004:** §5.1 atualizada (`extrair_quadro`) e §6.4 (a balança real existe; a cancela real não).
- **Documentos do Maestro:** `AMBIENTE.md` §8, §11.3; `CONVENCOES.md` §2; `specs/README.md` (texto enviado no relato).
- **Segurança operacional:** o modo real continua sem subir até existir um protocolo revisado com quadros reais; descarte do buffer antes de cada tentativa evita peso antigo; nenhuma escrita além do pedido do protocolo.
- **Não verificado:** nada foi testado com porta física ou balança real (`AGENTS.md` §4.9).
- **Reversibilidade:** alta.

## 10. Perguntas

| ID | Pergunta | Situação |
|---|---|---|
| P-1 | Como o sistema lê o sensor de status da cancela (cabo dedicado): pela mesma porta do comando, por outra porta serial, por linhas de controle (CTS/DSR) ou por outro meio? Sem isso não há como escrever `CancelaSerial` nem `ProtocoloCancela`. | **Aberta.** A cancela real continua indisponível (`ErroModoIndisponivel`). |
| P-2 | Modelo da balança, manual do protocolo e quadros reais (Q-01). | **Aberta.** Roteiro em `docs/equipamentos/README.md`. |
