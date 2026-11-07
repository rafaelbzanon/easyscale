# Equipamentos

Manuais e quadros reais da balança e das cancelas. **Hoje não há nenhum** (Q-01): modelo, protocolo e parâmetros
seriais continuam desconhecidos, e o modo `REAL` da balança não sobe porque o registro de protocolos está vazio
(spec 029). Nada aqui pode ser inventado (`AGENTS.md` §4.3).

## Roteiro para integrar um modelo de balança (spec 029)

1. **Pedir ao fabricante ou ao dono do equipamento:**
   - marca e modelo do indicador de pesagem;
   - o manual do protocolo serial: parâmetros (taxa, paridade, bits de dados, bits de parada), se o indicador
     transmite sozinho ou só responde a um pedido (e qual pedido), como começa e termina um quadro, onde está o peso,
     a unidade, o sinal e as marcas de erro ou sobrecarga;
   - quadros reais capturados do equipamento, de preferência com o peso conhecido em cada um.
2. **Salvar aqui**, com os nomes do `CONVENCOES.md` §9: o manual (ou a referência dele, se a licença não permitir
   copiar) e os quadros, um por arquivo, sem alterar os bytes: `balanca-estavel-01.txt`, `balanca-instavel-01.txt`,
   `balanca-corrompido-01.txt` e assim por diante. Anotar ao lado o peso esperado de cada um e de onde veio.
3. **Criar o protocolo** em `backend/src/pesagem/dispositivos/balanca/protocolos/<modelo>.py`, sem I/O, com os três
   métodos de `ProtocoloBalanca` (spec 004 §5.1): `montar_pedido`, `extrair_quadro` e `interpretar_quadro`. Tudo o que
   o código assumir precisa estar no manual ou nos quadros. Registrar uma linha em `protocolos/__init__.py`
   (`PROTOCOLOS["<NOME>"] = Classe`).
4. **Escrever o teste** `backend/tests/unitarios/dispositivos/balanca/test_protocolo_<modelo>.py`, lendo os quadros
   desta pasta: cada quadro estável vira o peso anotado, cada quadro corrompido vira `None`, e `extrair_quadro`
   acha o quadro com lixo antes e em pedaços. Ver como exemplo de transporte o
   `test_balanca_serial.py` (o protocolo de lá é fictício).
5. **Atualizar a spec** do modelo (ou a 029) e registrar a resposta na Q-01, com aprovação do autor.
6. **Configurar** (sem valor padrão, `AMBIENTE.md` §8): `PESAGEM_BALANCA_MODO=REAL`, `PESAGEM_BALANCA_PROTOCOLO`,
   `_PORTA`, `_BAUD_RATE`, `_PARIDADE` (`N`, `E`, `O`, `M`, `S`), `_DATA_BITS`, `_STOP_BITS`, `_TIMEOUT_MS` e
   `_INTERVALO_TENTATIVA_MS`, com os valores do manual.
7. **Testar com o equipamento** e registrar o teste à parte (`AMBIENTE.md` §14.1, nível 4). Só esse teste valida o
   comportamento real; os automáticos validam a lógica.

As cancelas ainda não têm roteiro: falta saber como o sensor de status, de cabo dedicado, é lido (spec 029, P-1).
