# Spec 006 — Máquina de estados da operação

- **Trilha:** Backend
- **Status:** Implementada (BE-213, 2026-11-04; aceita pelo autor em 2026-11-04). Aprovada pelo autor em 2026-11-04 ("aprovado", com os pontos da §14)
- **Data:** 2026-11-04
- **Tarefa:** BE-201 (spec); implementação na BE-213 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-014, RF-015, RF-016, RF-017, RF-024, RF-027, RF-010, RN-006, RN-007, RN-008, RN-009, RN-010, RN-011, RN-012, RN-016, RN-018, RN-019, RN-020, RNF-009, RNF-010
- **Código:** `backend/src/pesagem/dominio/operacao/maquina_estados.py` (`CONVENCOES.md` §2)

---

## 1. Contexto e origem

- O artigo descreve o fluxo: autorização, cancela, pesagem inicial, carga ou descarga, pesagem final, cálculo e saída **[ARTIGO §3.5, §4]**. O `AMBIENTE.md` §2.1 traz só estados candidatos **[PROPOSTA]**.
- Toda operação percorre uma máquina de estados explícita, e transição inválida é rejeitada e registrada, nunca corrigida (`AGENTS.md` §7.1.5, RN-010).
- Percurso físico, definido pelo autor em 2026-11-04 (§13):
  1. Há duas cancelas: a de **entrada**, antes da balança, e a de **saída**, depois dela.
  2. A entrada abre quando a placa bate com um agendamento e a balança está livre, e fecha quando o caminhão está em posição.
  3. Depois de **cada** pesagem, a saída abre e fecha assim que não houver mais caminhão.
  4. A carga e a descarga são feitas fora da balança. Na volta, o caminhão passa de novo pela entrada, com nova leitura da placa.
- Sensores de barreira agem direto na cancela e impedem o fechamento sobre o veículo. O sistema **não os lê**: ele usa as câmeras, e as tentativas de fechamento da spec 004 cobrem esse caso (§13).
- Outras decisões que já valem:
  - a câmera superior identifica a posição, podendo combinar todas as câmeras (Q-17, RF-027);
  - o sistema não orienta o posicionamento (Q-05);
  - só o administrador faz liberação manual (RN-016), sempre com responsável e motivo (RN-011);
  - uma pesagem `CANCELADA` permite uma nova pesagem para o mesmo agendamento (RN-009);
  - o líquido abaixo da tolerância negativa vai para o administrador (RN-006).
- A spec 004 (P-7) determina que só `CONFIRMADO` faz a operação avançar.

## 2. Objetivo

Definir uma regra **pura**: dada a situação atual e um evento, devolver a nova situação e a ação pedida, ou uma rejeição. Sem I/O, sem relógio e sem acesso a banco.

## 3. Fora de escopo

- Decidir se a entrada é autorizada (RN-002, RN-014). A orquestração decide, e a operação só nasce depois disso (P-1).
- Executar comandos, ler a balança, analisar imagens, medir tempo e escolher quem usa a balança (BE-601).
- O critério de análise das imagens da câmera superior. Esta spec recebe só o resultado (§5.2).
- Valores dos tempos-limite. Vêm de configuração, sem padrão inventado (BE-601).
- Esquema, repositórios e rotas (BE-502, CT-103).
- O mecanismo de permissões (CT-001, RF-031). A §9 só diz quem pode pedir cada ação.

## 4. Atores

- **Orquestração (BE-601):** envia os eventos automáticos e executa as ações.
- **Administrador e operador:** pedem as ações manuais, pela API, conforme a §9.

## 5. Dados

Os identificadores seguem o `CONVENCOES.md`. Os tipos são **[PROPOSTA]**.

### 5.1 Situações (`SituacaoOperacao`, gravada em `pesagem.situacao`)

| Situação | Significado | Comando pendente |
|---|---|---|
| `AGUARDANDO_BALANCA_INICIAL` | Placa aceita; aguarda a balança livre. | — |
| `AUTORIZADA` | Balança reservada; entrada ainda não confirmada aberta. | `ABRIR` entrada |
| `ENTRADA_LIBERADA` | Entrada aberta; aguarda o caminhão em posição. | — |
| `FECHANDO_ENTRADA` | Em posição; entrada sendo fechada. | `FECHAR` entrada |
| `POSICIONADA_INICIAL` | Em posição, com a entrada fechada; aguarda o peso inicial. | — |
| `PESO_INICIAL_OK` | Peso inicial registrado; saída ainda não confirmada aberta. | `ABRIR` saída |
| `SAIDA_INICIAL_LIBERADA` | Saída aberta; aguarda a balança vazia. | — |
| `FECHANDO_SAIDA_INICIAL` | Balança vazia; saída sendo fechada. | `FECHAR` saída |
| `EM_CARGA_DESCARGA` | Fora da balança, em carga ou descarga (RF-015). | — |
| `AGUARDANDO_BALANCA_FINAL` | Placa aceita na volta; aguarda a balança livre. | — |
| `RETORNO_AUTORIZADO` | Balança reservada; entrada ainda não confirmada aberta. | `ABRIR` entrada |
| `RETORNO_LIBERADO` | Entrada aberta; aguarda o caminhão em posição. | — |
| `FECHANDO_ENTRADA_RETORNO` | Em posição; entrada sendo fechada. | `FECHAR` entrada |
| `POSICIONADA_FINAL` | Em posição, com a entrada fechada; aguarda o peso final. | — |
| `PESO_FINAL_OK` | Peso final registrado e líquido aceito; saída ainda não confirmada aberta. | `ABRIR` saída |
| `SAIDA_LIBERADA` | Saída aberta; aguarda a balança vazia. | — |
| `FECHANDO_SAIDA` | Balança vazia; saída sendo fechada. | `FECHAR` saída |
| `AGUARDANDO_INTERVENCAO` | Parada segura; nenhum comando é emitido. Guarda `situacao_anterior` e `motivo_intervencao`. | — |
| `FINALIZADA` | Terminal. | — |
| `CANCELADA` | Terminal; permanece no histórico (RN-009). | — |

`pesagem.situacao` já tem `AUTORIZADA`, `PESO_INICIAL_OK`, `FINALIZADA` e `CANCELADA`, com os mesmos nomes (`CONVENCOES.md` §4.6).

### 5.2 Eventos automáticos

| Evento | Origem | Dados |
|---|---|---|
| `BALANCA_DISPONIVEL` | Orquestração: esta operação recebeu a balança (§6.3) | — |
| `PLACA_RETORNO_ACEITA` | Orquestração: a placa lida na volta corresponde a esta operação (RN-018) | — |
| `CANCELA_CONFIRMADA`, `CANCELA_FALHA`, `CANCELA_SEM_CONFIRMACAO` | Resultado do comando pendente (spec 004) | — |
| `POSICAO_CONFIRMADA` | Câmeras: o caminhão **desta operação** está em posição (RF-027) | — |
| `POSICAO_AUSENTE` | Câmeras: não há caminhão na balança | — |
| `POSICAO_INCONCLUSIVA` | Câmeras discordam, imagem ausente ou análise incerta (fail-safe) | — |
| `PESO_ACEITO` | Leitura aceita pela spec 002 | `peso_kg`, `lida_em` |
| `PESO_REJEITADO`, `BALANCA_FALHA` | Rejeição da spec 002 ou falha da balança (spec 004) | `motivo` |
| `TEMPO_ESGOTADO` | Tempo-limite da etapa, medido pela orquestração | — |
| `REINICIO_INCONCLUSIVO` | Retomada sem estado seguro confirmado (§7.2) | — |

### 5.3 Ações manuais (exigem `responsavel` e `motivo` não vazios; RN-011)

`TENTAR_NOVAMENTE`, `CONFIRMAR_POSICAO_MANUAL`, `CONFIRMAR_BALANCA_VAZIA_MANUAL`, `LIBERAR_RETORNO_MANUAL`, `ACEITAR_PESO_FINAL` e `CANCELAR`.

Não existe ação para digitar um peso: todo peso vem de leitura aceita (RN-004, RN-006).

### 5.4 Motivos de intervenção (`motivo_intervencao`)

`CANCELA_FALHA`, `CANCELA_SEM_CONFIRMACAO`, `POSICAO_PERDIDA`, `TEMPO_ESGOTADO`, `LIQUIDO_NEGATIVO` e `REINICIO_INCONCLUSIVO`.

### 5.5 Resultado da regra

- **`TransicaoAplicada`:** a operação nova, com `versao + 1`, e a `AcaoPedida` (`ABRIR`/`FECHAR` e `ENTRADA`/`SAIDA`), se houver.
- **`TransicaoRejeitada`:** situação atual, evento e `motivo_rejeicao`. A operação não muda.
- **`EventoRegistrado`:** a operação não muda; vale para os eventos marcados "registra" na §6.

A operação é imutável e guarda também `tipo_operacao`, `peso_inicial_kg`, `peso_inicial_em`, `peso_final_kg`, `peso_final_em`, `peso_liquido_kg`, `classificacao`, `liberacao_manual` e `versao`.

## 6. Transições válidas

Qualquer par situação/evento que não esteja aqui é **rejeitado** (§7.1).

| Situação | Evento | Vai para | Ação ou efeito |
|---|---|---|---|
| *(criação)* | Entrada aceita pela orquestração (RN-002) | `AGUARDANDO_BALANCA_INICIAL` | — |
| `AGUARDANDO_BALANCA_INICIAL` | `BALANCA_DISPONIVEL` | `AUTORIZADA` | `ABRIR` entrada |
| `AUTORIZADA` | `CANCELA_CONFIRMADA` | `ENTRADA_LIBERADA` | — |
| `ENTRADA_LIBERADA` | `POSICAO_CONFIRMADA` | `FECHANDO_ENTRADA` | `FECHAR` entrada |
| `FECHANDO_ENTRADA` | `CANCELA_CONFIRMADA` | `POSICIONADA_INICIAL` | — |
| `POSICIONADA_INICIAL` | `PESO_ACEITO` | `PESO_INICIAL_OK` | Guarda o peso inicial; `ABRIR` saída |
| `PESO_INICIAL_OK` | `CANCELA_CONFIRMADA` | `SAIDA_INICIAL_LIBERADA` | — |
| `SAIDA_INICIAL_LIBERADA` | `POSICAO_AUSENTE` | `FECHANDO_SAIDA_INICIAL` | `FECHAR` saída |
| `FECHANDO_SAIDA_INICIAL` | `CANCELA_CONFIRMADA` | `EM_CARGA_DESCARGA` | — |
| `EM_CARGA_DESCARGA` | `PLACA_RETORNO_ACEITA` | `AGUARDANDO_BALANCA_FINAL` | — |
| `AGUARDANDO_BALANCA_FINAL` | `BALANCA_DISPONIVEL` | `RETORNO_AUTORIZADO` | `ABRIR` entrada |
| `RETORNO_AUTORIZADO` | `CANCELA_CONFIRMADA` | `RETORNO_LIBERADO` | — |
| `RETORNO_LIBERADO` | `POSICAO_CONFIRMADA` | `FECHANDO_ENTRADA_RETORNO` | `FECHAR` entrada |
| `FECHANDO_ENTRADA_RETORNO` | `CANCELA_CONFIRMADA` | `POSICIONADA_FINAL` | — |
| `POSICIONADA_FINAL` | `PESO_ACEITO` com `COM_MOVIMENTACAO` ou `SEM_MOVIMENTACAO` | `PESO_FINAL_OK` | Guarda peso e líquido (spec 002); `ABRIR` saída |
| `POSICIONADA_FINAL` | `PESO_ACEITO` com `NEGATIVO_FORA_TOLERANCIA` | `AGUARDANDO_INTERVENCAO` | Guarda peso e líquido; motivo `LIQUIDO_NEGATIVO` |
| `PESO_FINAL_OK` | `CANCELA_CONFIRMADA` | `SAIDA_LIBERADA` | — |
| `SAIDA_LIBERADA` | `POSICAO_AUSENTE` | `FECHANDO_SAIDA` | `FECHAR` saída |
| `FECHANDO_SAIDA` | `CANCELA_CONFIRMADA` | `FINALIZADA` | — |

**Regras por grupo:**

| Grupo | Evento | Vai para | Efeito |
|---|---|---|---|
| `ENTRADA_LIBERADA`, `RETORNO_LIBERADO` | `POSICAO_AUSENTE`, `POSICAO_INCONCLUSIVA` | — | Registra |
| `SAIDA_INICIAL_LIBERADA`, `SAIDA_LIBERADA` | `POSICAO_CONFIRMADA`, `POSICAO_INCONCLUSIVA` | — | Registra |
| `POSICIONADA_INICIAL`, `POSICIONADA_FINAL` | `POSICAO_CONFIRMADA`, `POSICAO_INCONCLUSIVA`, `PESO_REJEITADO`, `BALANCA_FALHA` | — | Registra. Nenhum peso é guardado (RN-005). |
| `POSICIONADA_INICIAL`, `POSICIONADA_FINAL` | `POSICAO_AUSENTE` | `AGUARDANDO_INTERVENCAO` | Motivo `POSICAO_PERDIDA` |
| Com comando pendente (§5.1) | `CANCELA_FALHA`, `CANCELA_SEM_CONFIRMACAO` | `AGUARDANDO_INTERVENCAO` | Motivo de mesmo nome; posição da cancela tratada como desconhecida (RN-007) |
| Não terminal, exceto `AGUARDANDO_BALANCA_*`, `EM_CARGA_DESCARGA` e `AGUARDANDO_INTERVENCAO` | `TEMPO_ESGOTADO` | `AGUARDANDO_INTERVENCAO` | Motivo de mesmo nome. Fila e carga não têm limite: não há dado que justifique um. |
| Não terminal, exceto `AGUARDANDO_INTERVENCAO` | `REINICIO_INCONCLUSIVO` | `AGUARDANDO_INTERVENCAO` | Motivo de mesmo nome |
| Não terminal | `CANCELAR` | `CANCELADA` | Nenhum comando |
| `EM_CARGA_DESCARGA` | `LIBERAR_RETORNO_MANUAL` | `AGUARDANDO_BALANCA_FINAL` | `liberacao_manual = verdadeiro`. Cobre uma falha de leitura da placa na volta (RN-016). |

### 6.1 Saindo de `AGUARDANDO_INTERVENCAO`

| Ação | Condição | Vai para | Efeito |
|---|---|---|---|
| `TENTAR_NOVAMENTE` | Qualquer motivo | `situacao_anterior` | Repete o comando pendente da situação, se houver. Com `LIQUIDO_NEGATIVO`, nova pesagem final: o peso final, o líquido e a classificação são limpos, e os valores anteriores ficam no registro de auditoria (§10). |
| `CONFIRMAR_POSICAO_MANUAL` | `situacao_anterior` é `ENTRADA_LIBERADA` ou `RETORNO_LIBERADO` | `FECHANDO_ENTRADA` ou `FECHANDO_ENTRADA_RETORNO` | `liberacao_manual = verdadeiro`; `FECHAR` entrada |
| `CONFIRMAR_BALANCA_VAZIA_MANUAL` | `situacao_anterior` é `SAIDA_INICIAL_LIBERADA` ou `SAIDA_LIBERADA` | `FECHANDO_SAIDA_INICIAL` ou `FECHANDO_SAIDA` | `liberacao_manual = verdadeiro`; `FECHAR` saída. Evita que uma falha da câmera force o cancelamento de uma pesagem já feita. |
| `ACEITAR_PESO_FINAL` | Motivo `LIQUIDO_NEGATIVO` | `PESO_FINAL_OK` | `liberacao_manual = verdadeiro`; os valores não mudam (RN-004); `ABRIR` saída |
| `CANCELAR` | Qualquer motivo | `CANCELADA` | Nenhum comando |

Eventos automáticos que chegam em `AGUARDANDO_INTERVENCAO` são rejeitados e registrados: o sistema só sai dessa parada por ação humana.

### 6.2 Efeito no status do agendamento

Criação → `EM_ANDAMENTO`; `FINALIZADA` → `CONCLUIDO`; `CANCELADA` → `AGENDADO`, para permitir nova pesagem se ainda valer no dia (P-8, RN-009, RN-014). Um agendamento com operação aberta não pode ser editado nem cancelado. A BE-601 aplica esse efeito na mesma transação.

### 6.3 Uso da balança e várias operações abertas (RN-008, RN-019)

- Várias operações podem estar abertas ao mesmo tempo, no máximo uma por placa.
- **A balança é de um caminhão por vez.** Uma operação ocupa a balança de `AUTORIZADA` ou `RETORNO_AUTORIZADO` até o fim de `FECHANDO_SAIDA_INICIAL` ou `FECHANDO_SAIDA`, inclusive quando está em `AGUARDANDO_INTERVENCAO` a partir de uma dessas situações.
- A orquestração envia `BALANCA_DISPONIVEL` a uma única operação, por ordem de chegada, e só se nenhuma outra ocupar a balança, as câmeras informarem `POSICAO_AUSENTE` e as duas cancelas estiverem `FECHADA`. Essa condição cobre o caminhão de uma operação cancelada que ainda está sobre a balança.

### 6.4 Caminhão de operação cancelada na balança (P-7, RN-020)

Cancelar não aciona cancela. Se o caminhão ainda estiver na balança, o **operador ou o administrador** pedem a liberação, com responsável e motivo. A orquestração comanda `ABRIR` saída e, com a balança vazia, `FECHAR` saída, registrando os comandos. Essa liberação fica fora desta máquina, porque a operação já terminou, e só vale quando a operação cancelada ocupava a balança (BE-601).

## 7. Comportamento em falha

### 7.1 Transição inválida

Evento fora da §6, operação terminal, ação manual sem `responsavel` ou `motivo`, peso duplicado, ou peso fora de `POSICIONADA_*`: devolve `TransicaoRejeitada`. A operação não muda e nenhuma ação é pedida. A orquestração registra a rejeição (RN-010). Peso não finito ou `lida_em` sem fuso também é rejeitado.

### 7.2 Queda ou reinício do backend

A situação é gravada **antes** de cada comando físico, e cada situação tem no máximo um comando pendente. Na retomada, a orquestração segue esta tabela, sem reenviar nada às cegas (`AGENTS.md` §7.2):

| Situação gravada | Retomada |
|---|---|
| Com comando pendente | Lê o sensor da cancela **antes** de comandar. Já na posição pedida: `CANCELA_CONFIRMADA`. Na posição contrária: repete o comando pelas regras da spec 004. `DESCONHECIDO`: `REINICIO_INCONCLUSIVO`, sem enviar comando. |
| `POSICIONADA_*` | Descarta as leituras em memória e recomeça a série da spec 002. |
| Demais situações | Continua aguardando os eventos. |
| `AGUARDANDO_INTERVENCAO` e terminais | Nada muda. |

### 7.3 Concorrência

- Cada transição exige a `versao` lida. A gravação compara essa versão, e quem perder relê e reavalia o evento (BE-502).
- O peso e a nova situação são gravados na mesma transação. Se a gravação falhar, a operação não avança e nenhum comando é emitido: isso garante "aceita e registrada" (RN-012).
- Um segundo `PESO_ACEITO` é rejeitado pela §7.1, o que impede pesagem duplicada.
- A reserva da balança (§6.3) e o limite de uma operação aberta por placa precisam ser garantidos na gravação, para que dois eventos simultâneos não passem juntos (BE-502).

### 7.4 Falha de dispositivo em cada etapa

| Situação | Resultado |
|---|---|
| Sensor de barreira impede o fechamento | A cancela não chega à posição: as tentativas da spec 004 se esgotam e vem `SEM_CONFIRMACAO`, que leva a `AGUARDANDO_INTERVENCAO`. |
| Cancela com `FALHA` ou `SEM_CONFIRMACAO` | `AGUARDANDO_INTERVENCAO`; a operação não avança, e a etapa fica em `situacao_anterior`. |
| Balança falha ou leitura rejeitada | Registra e continua na etapa até `TEMPO_ESGOTADO` (pela spec 004, a espera total é da BE-601). |
| Câmera indisponível ou resultado incerto | `POSICAO_INCONCLUSIVA`: não avança; sustentado, vira `TEMPO_ESGOTADO`. |
| Placa não reconhecida na volta | A situação segue `EM_CARGA_DESCARGA`, a entrada não abre, e o caso vai ao operador com a evidência (RN-003, RN-018). |

## 8. Regras de negócio

- **RN-012:** `ABRIR` saída só é pedido em `PESO_INICIAL_OK` e `PESO_FINAL_OK`, ou seja, depois de uma pesagem aceita e registrada com a posição confirmada. Só `FINALIZADA` encerra a operação, e ela exige a pesagem final.
- **RN-018:** na volta, a entrada só abre depois de `PLACA_RETORNO_ACEITA` ou da liberação manual, e de `BALANCA_DISPONIVEL`.
- **RN-019:** a entrada só abre com a balança reservada para esta operação.
- **RF-027:** `PESO_ACEITO` só vale em `POSICIONADA_*`.
- **RN-007:** só avança com `CANCELA_CONFIRMADA`.
- **RN-009:** uma nova operação para o mesmo agendamento só é criada se a anterior for `CANCELADA`.

## 9. Quem pode pedir cada ação

| Ação | Perfis |
|---|---|
| `TENTAR_NOVAMENTE`, liberação da §6.4 | `ADMINISTRADOR`, `OPERADOR` |
| `CONFIRMAR_POSICAO_MANUAL`, `CONFIRMAR_BALANCA_VAZIA_MANUAL`, `LIBERAR_RETORNO_MANUAL`, `ACEITAR_PESO_FINAL`, `CANCELAR` | `ADMINISTRADOR` |

`AUDITOR` só consulta. A verificação fica no backend, fora desta regra pura, para que novos perfis não mudem a máquina de estados (RF-031).

## 10. Dados envolvidos

Ver a §5. Cada transição, rejeição e evento registrado vira um registro de auditoria com situação de origem e de destino, evento, instante, `responsavel` e `motivo` (RNF-010). Placas e imagens não entram nesses registros (RNF-013).

## 11. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | O caminho completo de CARGA, da criação a `FINALIZADA`, percorre as situações na ordem da §6 e pede exatamente 8 comandos: abrir e fechar a entrada e a saída em cada uma das duas passagens. |
| CA-002 | O mesmo caminho em DESCARGA calcula o líquido como inicial − final. |
| CA-003 | Todo par situação/evento fora da §6 devolve `TransicaoRejeitada`, com a operação inalterada e sem ação (teste por tabela, cobrindo todos os pares). |
| CA-004 | `PESO_ACEITO` em qualquer situação fora de `POSICIONADA_*` é rejeitado; um segundo `PESO_ACEITO` não altera o peso guardado. |
| CA-005 | `ABRIR` entrada só é pedido a partir de `BALANCA_DISPONIVEL`. |
| CA-006 | `ABRIR` saída só é pedido ao chegar em `PESO_INICIAL_OK` ou `PESO_FINAL_OK`. |
| CA-007 | `FECHAR` entrada só é pedido com a posição confirmada, automática ou manualmente; `FECHAR` saída, só com a balança vazia, automática ou manualmente. |
| CA-008 | `EM_CARGA_DESCARGA` só avança com `PLACA_RETORNO_ACEITA` ou `LIBERAR_RETORNO_MANUAL`; `POSICAO_CONFIRMADA` nessa situação é rejeitada. |
| CA-009 | `SEM_MOVIMENTACAO` chega a `PESO_FINAL_OK` com o líquido calculado, sem trocá-lo por zero. |
| CA-010 | `NEGATIVO_FORA_TOLERANCIA` vai para `AGUARDANDO_INTERVENCAO` com `LIQUIDO_NEGATIVO` e não pede a saída. |
| CA-011 | `CANCELA_FALHA` e `CANCELA_SEM_CONFIRMACAO`, em cada uma das 8 situações com comando pendente, vão para `AGUARDANDO_INTERVENCAO` com a `situacao_anterior` correta e sem nova ação. |
| CA-012 | `POSICAO_INCONCLUSIVA` nunca muda a situação. |
| CA-013 | `POSICAO_AUSENTE` em `POSICIONADA_*` vai para `AGUARDANDO_INTERVENCAO` com `POSICAO_PERDIDA`. |
| CA-014 | `PESO_REJEITADO` e `BALANCA_FALHA` não mudam a situação nem guardam peso. |
| CA-015 | `TEMPO_ESGOTADO` vai para `AGUARDANDO_INTERVENCAO` nas situações da §6 e é rejeitado em `AGUARDANDO_BALANCA_*` e `EM_CARGA_DESCARGA`. |
| CA-016 | Evento automático em `AGUARDANDO_INTERVENCAO` é rejeitado. |
| CA-017 | `TENTAR_NOVAMENTE` volta à `situacao_anterior` e repete o comando pendente. |
| CA-018 | `CONFIRMAR_POSICAO_MANUAL` e `CONFIRMAR_BALANCA_VAZIA_MANUAL` só são aceitas a partir das situações da §6.1, e marcam `liberacao_manual`. |
| CA-019 | `LIBERAR_RETORNO_MANUAL` só é aceita em `EM_CARGA_DESCARGA` e marca `liberacao_manual`. |
| CA-020 | `ACEITAR_PESO_FINAL` só é aceita com `LIQUIDO_NEGATIVO`, marca `liberacao_manual`, mantém os valores e pede a saída. |
| CA-021 | Ação manual sem `responsavel` ou `motivo` é rejeitada. |
| CA-022 | Nenhuma ação manual recebe um valor de peso (verificado pelo tipo). |
| CA-023 | `CANCELAR` funciona em toda situação não terminal, não pede comando, e é rejeitado em `FINALIZADA` e `CANCELADA`. |
| CA-024 | Terminais rejeitam todo evento. |
| CA-025 | Toda `TransicaoAplicada` soma 1 à `versao`; rejeição e evento registrado não somam. |
| CA-026 | O módulo não importa nada proibido por P-4 e P-5 (teste de arquitetura da spec 001). |

A retomada (§7.2), a transação (§7.3), a reserva da balança (§6.3), a liberação de caminhão cancelado (§6.4) e o efeito no agendamento (§6.2) são verificados na BE-602, com os simuladores e o banco, e não nesta regra pura.

## 12. Impacto

- **Código:** cria `dominio/operacao/` na BE-213; usa `calcular_peso_liquido` da spec 002.
- **Orquestração (BE-601):** define os tempos-limite, a tabela da §7.2, a reserva da balança, a liberação da §6.4 e como o resultado das câmeras vira evento. É preciso uma **fonte de posição**, com interface e simulador, que ainda não existe (RF-027).
- **LPR:** a placa é lida também na volta, com os mesmos critérios de confiança e formato (RN-018). A comparação com a operação aberta é da BE-601.
- **Esquema (BE-502), sem alterar agora:**
  - `ck_pesagem_situacao` com os 20 valores;
  - novos campos `situacao_anterior`, `motivo_intervencao`, `versao` e `classificacao`;
  - `ux_pesagem_agendamento_id` hoje impede a nova pesagem da RN-009: precisa ser parcial, ignorando `CANCELADA`;
  - `ux_pesagem_veiculo_aberta` precisa listar todas as situações não terminais;
  - `ponto_controle.cancela_saida_id` hoje é opcional e passa a ser obrigatório;
  - uma forma de garantir a reserva única da balança (§6.3);
  - `motivo_liberacao` e `liberado_por` precisam valer para todas as ações manuais;
  - uma tabela de eventos de transição (§10) com responsável e motivo (C-002 itens 10 e 12).
- **Contrato (CT-103):** os valores das §5.1, §5.3 e §5.4 aparecem na API.
- **Glossário:** os termos novos entram em `CONVENCOES.md` §10 e em `specs/glossario.md` com a aprovação.
- **Segurança operacional:** as câmeras passam a condicionar o fechamento das duas cancelas. Os sensores de barreira agem de forma independente e continuam sendo a proteção física contra o fechamento sobre o veículo. Nada foi validado com hardware real.
- **Reversibilidade:** alta; é uma regra pura, ainda sem código.

## 13. Decisões do autor (2026-11-04)

| ID | Pergunta | Resposta |
|---|---|---|
| P-1 | Quando nasce a operação? | Na autorização; falhas de identificação viram eventos, e a liberação manual exige um agendamento existente. |
| P-2 | Quando as cancelas fecham? | A primeira abre com a placa e o agendamento e fecha com o caminhão em posição. Depois de pesar, a segunda abre e fecha assim que não houver mais caminhão. |
| P-2a | Por onde o caminhão vai à carga e volta? | Sai pela saída depois da pesagem inicial e volta pela entrada. |
| P-2b | O software lê os sensores de barreira? | Não. O sistema lê as câmeras; os sensores agem direto na cancela, e por isso há várias tentativas de fechamento. |
| P-3 | A carga é feita sobre a balança? | Não. |
| P-4 | Pode haver várias operações abertas? | Sim, uma por placa, e uma nova fila pode começar enquanto outro caminhão pesa. |
| P-4a | Caminhão válido com a balança ocupada? | A operação é criada e espera; a entrada só abre com a balança livre. |
| P-5 | Quem pode pedir cada ação? | A tabela da §9. |
| P-6 | O administrador pode substituir a câmera e aceitar líquido negativo? | Sim, com registro. Peso digitado continua proibido. |
| P-7 | Como sai um caminhão de operação cancelada? | O operador ou o administrador intervêm para liberar o caminhão que está na balança. |
| P-8 | Ao cancelar, o agendamento volta a `AGENDADO`? | Sim, se ainda valer no dia. |

## 14. Pontos confirmados na aprovação

- **Tentativas de fechamento:** a spec 004 fixa 2 tentativas por comando. A proposta mantém esse número e usa `TENTAR_NOVAMENTE` depois. Se um dia 2 forem poucas, a mudança é na spec 004.
- **Horário na volta:** na volta não se aplica de novo a RN-014, para não prender um caminhão cuja carga passou da faixa ou do dia. Confirmado pelo autor.
- **Spec 004:** ela diz que um resultado sem sucesso "mantém a etapa atual". Aqui a operação vai para `AGUARDANDO_INTERVENCAO`, guarda a etapa em `situacao_anterior` e volta a ela. É compatível, porque a operação não avança e nada se perde.
- **Liberação manual na volta:** `LIBERAR_RETORNO_MANUAL`, só para o administrador (§9).
