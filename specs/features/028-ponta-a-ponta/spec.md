# Spec 028 — Teste ponta a ponta

- **Trilha:** Integração
- **Status:** Implementada (INT-002, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** INT-002 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-001 a RF-011, RF-013 a RF-019, RF-021, RF-024, RF-027, RN-002 a RN-012, RN-016, RN-018 a RN-020, RNF-003, RNF-007, RNF-009, RNF-010 e os 7 cenários de `specs/requisitos.md` §4 **[ARTIGO §2]**
- **Decisões:** AGENTS.md §7.2 e §8; specs 007 a 012 e 015 (contratos e orquestração); spec 011 §6.4 (controle dos simuladores)
- **Código:** `backend/tests/ponta_a_ponta/`

---

## 1. Contexto e origem

- O artigo valida o protótipo em ambiente controlado, com imagens de placas e simulação serial da balança e das cancelas **[ARTIGO §2]**. O AMBIENTE §14.1 prevê o nível "ponta a ponta com simuladores".
- Os testes de integração (Keel) cobrem cada contrato isolado. Falta provar que as partes andam juntas, do login à operação finalizada.

## 2. Objetivo

Percorrer o sistema só pela API HTTP, com a aplicação real, o PostgreSQL real e os simuladores dirigidos pelas rotas da spec 011 §6.4, e conferir o resultado pelo histórico (spec 010) e pelos eventos.

## 3. Fora de escopo

- Hardware real, câmeras reais e OCR real: nada disso foi exercitado.
- Navegador e frontend. Quem testa as telas é o próprio frontend (Vitest, spec 016 em diante).
- Contêineres do Compose (spec 027). Aqui o backend roda no processo do teste.
- Passagem do tempo real: o relógio é controlado pelo teste e os ciclos da orquestração são chamados um a um, como na integração do Keel. Isso deixa o resultado igual a cada execução, sem `sleep`.
- Carga, desempenho e concorrência de verdade (já cobertos nos testes de persistência).

## 4. Como roda

- Os fixtures do PostgreSQL em contêiner (`postgres:18.6-alpine`), do relógio e do cliente HTTPS são os de `backend/tests/integracao/conftest.py`, carregados pelo caminho. Não há cópia.
- O primeiro administrador nasce pelo repositório de usuários (o comando de instalação é `pesagem.api.criar_administrador`, spec 012 §6.10, testado na integração). Daí em diante, login, cadastros, faixa, agendamento, chegada e ações usam só rotas.
- A chegada da placa é a `POST /api/simuladores/chegadas`; posição, balança e cancelas, as rotas `POST /api/simuladores/...`.
- Os ciclos de identificação, fila, posição e balança são chamados pelo teste no laço da aplicação.
- Sem Docker, os testes falham com mensagem clara. Não são pulados.

## 5. Cenários

### 5.1 Do artigo (`specs/requisitos.md` §4)

| # | Cenário | CA |
|---|---|---|
| 1 | Veículo com agendamento válido | CA-001 |
| 2 | Veículo sem agendamento | CA-006 |
| 3 | Falha no reconhecimento da placa | CA-007 |
| 4 | Leitura de peso | CA-001, CA-002 |
| 5 | Falha de comunicação com a balança | CA-008 |
| 6 | Acionamento de cancela | CA-001, CA-009, CA-010 |
| 7 | Finalização com o peso líquido | CA-001 a CA-003, CA-013 |

### 5.2 Falhas do AGENTS.md §7.2 que a API mostra

Placa inconclusiva, sem agendamento, balança sem resposta ou instável, cancela sem confirmação, posição inconclusiva, concorrência (versão velha), transição inválida e líquido negativo. Câmera indisponível e reinício do backend não têm rota nos simuladores (spec 011 §3) e ficam nos testes unitários e de integração.

## 6. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | **Carga completa.** Login, cadastros, faixa e agendamento manual (`origem = USUARIO`); chegada `ABC1D23` autorizada; balança livre; entrada aberta e fechada; peso inicial; saída aberta e fechada; volta com a placa (`RETORNO_ACEITO`); peso final; saída; `FINALIZADA`. Os 8 comandos saem na ordem da spec 006. O líquido é final − inicial. O agendamento fica `CONCLUIDO`. O histórico mostra a pesagem, os eventos em ordem, sem placa nem CPF, e todos automáticos. |
| CA-002 | **Descarga.** O líquido é inicial − final (RN-006). |
| CA-003 | **Sem movimentação.** Diferença de 12 kg: `SEM_MOVIMENTACAO` e líquido `"12.000"`, nunca zero (RN-004, RN-006). |
| CA-004 | `AUDITOR` e `OPERADOR` consultam a pesagem e os eventos e recebem `403` ao cancelar. |
| CA-005 | O canal de eventos traz um `pesagem` por transição e também `leitura_placa`, `cancela`, `posicao` e `balanca`, sem CPF. |
| CA-006 | Placa cadastrada sem agendamento e placa desconhecida: `NAO_AUTORIZADA` com `SEM_AGENDAMENTO` e `VEICULO_NAO_CADASTRADO`, com imagem guardada, sem pesagem e sem comando de cancela. |
| CA-007 | Sem texto, texto sem formato de placa, duas placas e confiança baixa: `NAO_AUTORIZADA` com o motivo certo, sem pesagem e sem comando. Sem imagem nova, nada é registrado. O `OPERADOR` não libera a entrada; o administrador libera `CONFIANCA_BAIXA` e a pesagem nasce com `liberacao_manual`, sem abrir a cancela na hora. |
| CA-008 | Com a pesagem em posição: balança `SEM_RESPOSTA`, `QUADRO_CORROMPIDO`, `DESCONECTADA`, `INSTAVEL` e peso fora da faixa não gravam peso, e cada motivo aparece nos eventos. Passado o limite, a pesagem vai a `AGUARDANDO_INTERVENCAO` (`TEMPO_ESGOTADO`). `TENTAR_NOVAMENTE` pelo operador e uma leitura estável gravam o peso. |
| CA-009 | Cancela de entrada em `FALHA` (1 tentativa) ou `NAO_MOVE` (`SEM_CONFIRMACAO`, 2 tentativas): `AGUARDANDO_INTERVENCAO` com o motivo certo, um único comando registrado, nada anda sozinho; `TENTAR_NOVAMENTE` envia um comando novo. |
| CA-010 | Sensor da cancela sem resposta ao fechar: estado `DESCONHECIDO`, resultado `SEM_CONFIRMACAO` e `AGUARDANDO_INTERVENCAO`. Com o sensor ainda mudo, `TENTAR_NOVAMENTE` volta à intervenção. |
| CA-011 | Posição `INCONCLUSIVA` não avança nem fecha a entrada. Passado o limite, `TEMPO_ESGOTADO`. `OPERADOR` não confirma a posição (`403`); o administrador confirma, com responsável e motivo nos eventos, e a pesagem segue com `liberacao_manual`. |
| CA-012 | Ação com `versao` velha dá `409 VERSAO_DESATUALIZADA`; ação que a máquina não aceita dá `409 TRANSICAO_REJEITADA`, registrada nos eventos. Nada muda. |
| CA-013 | Líquido abaixo de −20 kg: `AGUARDANDO_INTERVENCAO` (`LIQUIDO_NEGATIVO`) com os pesos, `NEGATIVO_FORA_TOLERANCIA`, saída fechada. `OPERADOR` não aceita o peso (`403`). `TENTAR_NOVAMENTE` apaga o peso final da pesagem e o valor descartado fica nos eventos. O administrador pode aceitar o peso e a pesagem finaliza com `liberacao_manual`. |
| CA-014 | Dois caminhões autorizados: a fila segue a ordem de chegada e o segundo só recebe a balança depois de o primeiro sair dela (RN-019). |
| CA-015 | Cancelar na balança deixa a liberação `PENDENTE` e o agendamento volta a `AGENDADO`. `OPERADOR` pede `liberar-caminhao`; a saída abre, fecha com a balança vazia e a pendência some. A pesagem cancelada fica no histórico (RN-009, RN-020). |
| CA-016 | Na volta, placa com confiança baixa ou de outro veículo não move a pesagem (RN-018). O `OPERADOR` não libera o retorno; o administrador libera, e a pesagem termina com `liberacao_manual`. |
| CA-017 | Depois do cancelamento, a mesma placa autorizada de novo gera leitura nova e pesagem nova para o mesmo agendamento (RN-009). |

## 7. Defeitos achados e corrigidos (INT-002)

| Defeito | Dono | Situação |
|---|---|---|
| Volta da placa não gravava: `ErroLeituraJaUsada` (leitura de retorno já nascia ligada à pesagem). Fail-safe, mas a volta só passava por `liberar-retorno`. | Gyro | Corrigido em `orquestracao/operacao.py` (2026-11-07). |
| Mesma placa autorizada de novo depois de cancelar era ignorada como "decisão repetida" (spec 015 §6.1 item 4). | Gyro | Corrigido; spec 015 §6.1 ajustada. |

## 8. Impacto

- **Código novo:** só `backend/tests/ponta_a_ponta/`. Nenhuma alteração em `backend/src/` nem em `frontend/`.
- **Execução:** `pytest tests/ponta_a_ponta` ou o `pytest` inteiro (AMBIENTE §6.1). Rodando tudo junto, a integração e o ponta a ponta carregam o conftest em módulos separados e cada um sobe o seu contêiner de PostgreSQL por sessão (não medido o custo).
- **Segurança operacional:** os testes provam, com simuladores, que cada falha termina sem autorizar, sem registrar peso e sem comando cego. **Nada foi validado com hardware real.**

## 9. Perguntas em aberto

| ID | Pergunta | Até a resposta |
|---|---|---|
| P-1 | O canal de eventos monta o objeto `pesagem` com o estado do banco na hora do envio, e não o da transição. Um leitor lento recebe a mesma versão várias vezes. A spec 009 §6.1 manda ignorar versão repetida, então a tela não erra. É o comportamento desejado? | O teste confere só a contagem, o `id` e a última versão. |
