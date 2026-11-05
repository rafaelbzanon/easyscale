# Spec 003 — Normalização de placa

- **Trilha:** Backend
- **Status:** Implementada (BE-211, 2026-10-29; aceita pelo autor em 2026-10-29, incluindo a correção do exemplo da CA-007)
- **Data:** 2026-10-29
- **Tarefa:** BE-203 (spec); implementação na BE-211 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-008, RN-002, RN-003, RN-017, RNF-009
- **Respostas do autor (2026-10-29):** P-1 = conjunto ampliado; P-2 = sim; P-3 = seguir a legislação (a placa convertida é o mesmo veículo); P-4 = espaço, hífen e ponto (recomendação confirmada)
- **Pasta do código (futura):** `backend/src/pesagem/dominio/placa/` (`CONVENCOES.md` §2)

---

## 1. Contexto e origem

- O texto que o OCR reconhece é tratado antes de ser comparado com as placas cadastradas **[ARTIGO §3.3]** (RF-008).
- O autor definiu que só valem placas brasileiras, no formato antigo `AAA9999` ou no formato Mercosul `AAA9A99` (Q-10, RN-017).
- As confusões típicas do OCR (O/0, I/1, B/8) devem ser corrigidas **com regras explícitas e testadas, sem "adivinhar" silenciosamente** (`AMBIENTE.md` §9).
- Um falso positivo de autorização pesa mais do que um falso negativo (`AMBIENTE.md` §14.3). Por isso a regra prefere rejeitar a corrigir demais.

## 2. Objetivo

Uma função **pura** que recebe a `placa_lida`, o texto bruto do OCR, e devolve:
- a `placa_normalizada`, o formato e a lista de correções aplicadas; ou
- uma rejeição, com o motivo.

## 3. Fora de escopo

- O OCR, a ROI, a confiança e o limiar de confiança. Isso é da BE-401. A regra de confiança da RN-002 é aplicada pela orquestração, não aqui.
- A consulta ao cadastro de veículos e aos agendamentos (orquestração e persistência). A **chave de comparação** (§5.2), que a consulta usa, é uma função pura deste módulo.
- Votação entre vários quadros de imagem (R-03, BE-401).
- Placas de outros países (RN-017).

## 4. Dados

Os identificadores seguem o `CONVENCOES.md` §10. Os tipos são **[PROPOSTA]**.

| Nome | Conteúdo |
|---|---|
| Entrada | `placa_lida: str`, exatamente o que o OCR devolveu. |
| `PlacaNormalizada` | `placa_normalizada: str` (7 caracteres, A–Z e 0–9, sem separador); `formato: FormatoPlaca`; `correcoes: tuple[CorrecaoCaractere, ...]`; `chave_comparacao: str` (§5.2). |
| `FormatoPlaca` | `ANTIGO` ou `MERCOSUL`. |
| `CorrecaoCaractere` | `posicao` (de 1 a 7), `lido` e `corrigido`. |
| `RejeicaoPlaca` | `motivo: MotivoRejeicaoPlaca` e `placa_lida`. |
| `MotivoRejeicaoPlaca` | `VAZIA`, `CARACTERE_INVALIDO`, `COMPRIMENTO_INVALIDO` ou `FORMATO_INVALIDO`. |

## 5. Comportamento normal

Os passos são aplicados nesta ordem:

1. **Limpeza.**
   - Converter para maiúsculas.
   - Remover só os **separadores permitidos**: espaço, hífen `-` e ponto `.` (P-4).
   - Qualquer outro caractere que não seja A–Z ou 0–9 faz a placa ser rejeitada. Isso inclui letra acentuada, `*`, `|` e caracteres de controle.
2. **Comprimento.** Depois da limpeza, a placa precisa ter exatamente 7 caracteres.
3. **Correção por posição.** Segue a tabela da §5.1 e só vale nas posições cujo tipo é igual nos dois formatos:
   - posições 1, 2 e 3 são sempre letra;
   - posições 4, 6 e 7 são sempre dígito;
   - **a posição 5 nunca é corrigida**, porque ela é justamente o que diferencia os dois formatos (dígito no antigo, letra no Mercosul). Corrigi-la seria escolher o formato no lugar do OCR.
4. **Formato.** Com a posição 5 em dígito, o formato é `ANTIGO`; com letra, é `MERCOSUL`.
5. **Resultado.** O retorno traz a `placa_normalizada`, o `formato` e todas as `correcoes`, para que a tela de diagnóstico mostre o que mudou (`AMBIENTE.md` §10).

### 5.1 Tabela de correção (P-1: conjunto ampliado, decisão do autor)

| Par | Onde se espera **letra** (posições 1–3), lido → corrigido | Onde se espera **dígito** (posições 4, 6 e 7), lido → corrigido |
|---|---|---|
| O/0 | `0` → `O` | `O` → `0` |
| I/1 | `1` → `I` | `I` → `1` |
| B/8 | `8` → `B` | `B` → `8` |
| S/5 | `5` → `S` | `S` → `5` |
| Z/2 | `2` → `Z` | `Z` → `2` |
| G/6 | `6` → `G` | `G` → `6` |
| A/4 | `4` → `A` | `A` → `4` |
| T/7 | `7` → `T` | `T` → `7` |

A tabela é uma correspondência de mão dupla: cada caractere tem no máximo uma correção, então o resultado não depende da ordem. Um caractere fora da tabela na posição errada rejeita a placa com `FORMATO_INVALIDO`. Por exemplo, um `Q` na posição 4 rejeita a placa, em vez de virar `0`.

### 5.2 Chave de comparação: placa antiga e placa Mercosul (P-3)

O autor decidiu seguir a legislação: o veículo que trocou a placa antiga pela Mercosul continua sendo o mesmo veículo.

- **Regra:** na conversão, o **segundo caractere numérico** da placa antiga, que fica na posição 5, é trocado por uma letra: 0→A, 1→B, 2→C, 3→D, 4→E, 5→F, 6→G, 7→H, 8→I, 9→J. Exemplo: `ABC1234` ↔ `ABC1C34`.
- **Fonte:** Resolução CONTRAN nº 780/2019, art. 2º, § 3º, e Anexo II, item 1 ("Tabela de Conversão dos caracteres alfanuméricos da PIV": 0→A … 9→J; exemplo oficial `ABC1234` → `ABC1C34`). **Verificado no texto oficial** em 2026-10-29: PDF do Ministério dos Transportes (gov.br, `resolucao7802019.pdf`). O Anexo II, item 2, diz ainda que as letras de A a J na posição 5 são usadas **apenas** para a conversão; logo a correspondência é exata nos dois sentidos.
- **`chave_comparacao`:**
  - para uma placa `ANTIGO`, é a placa com a posição 5 convertida pela tabela;
  - para uma placa `MERCOSUL`, é a própria placa.
  
  Toda comparação com o cadastro usa essa chave dos dois lados, então `ABC1234` e `ABC1C34` caem no mesmo veículo.
- **Não é correção:** a chave não altera a `placa_normalizada` nem entra em `correcoes`. A placa lida e a placa normalizada continuam registradas como foram vistas.
- **Letras K a Z na posição 5** não têm equivalente antigo; para elas, a chave é a própria placa.
- **Efeito colateral bom:** se o OCR ler a posição 5 como dígito numa placa Mercosul, ou como letra numa placa antiga, a chave ainda leva ao mesmo veículo, desde que o caractere seja o par da tabela.

## 6. Comportamento em falha

| Situação | Resultado |
|---|---|
| Texto vazio ou só com separadores | `VAZIA` |
| Caractere fora de A–Z, 0–9 e dos separadores permitidos | `CARACTERE_INVALIDO` |
| Comprimento diferente de 7 depois da limpeza | `COMPRIMENTO_INVALIDO` |
| Caractere que não pode ser corrigido na posição errada | `FORMATO_INVALIDO` |
| Mais de um motivo ao mesmo tempo | O primeiro, nesta ordem: `VAZIA` → `CARACTERE_INVALIDO` → `COMPRIMENTO_INVALIDO` → `FORMATO_INVALIDO` |

A rejeição **nunca** traz um palpite de placa. A orquestração encaminha o caso ao operador com a evidência (RN-003).

## 7. Regras de negócio

- **RN-017:** só os formatos `ANTIGO` e `MERCOSUL` são aceitos.
- **Sem adivinhação:** toda correção está na tabela da §5.1 e aparece em `correcoes`. Não há correção baseada em semelhança com placas já cadastradas.
- **RNF-009 (fail-safe):** quando houver dúvida, a placa é rejeitada.

## 8. Estados afetados

Nenhum. Uma placa rejeitada leva ao estado de "não autorizado, encaminhado" da BE-201.

## 9. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | `ABC1234` → `ABC1234`, formato `ANTIGO`, sem correções. |
| CA-002 | `ABC1D23` → `ABC1D23`, formato `MERCOSUL`, sem correções. |
| CA-003 | `abc-1234`, ` ABC 1234 ` e `ABC.1234` → `ABC1234`. Separadores e letras minúsculas não contam como correção. |
| CA-004 | `A8C1234` → `ABC1234`, com a correção (2, `8`, `B`). Isso vale para os 8 pares da tabela §5.1 em cada posição permitida, por teste parametrizado. |
| CA-005 | `ABC1O23`: a posição 5 não é corrigida, e o resultado é `MERCOSUL` `ABC1O23`. `ABC1023` dá `ANTIGO`. |
| CA-006 | `ABCO234` → `ABC0234`, com a correção (4, `O`, `0`). |
| CA-007 | `ABC53S4` (`S` na posição 6) → `ABC5354`, com a correção (6, `S`, `5`). `ABCQ234` (`Q` na posição 4, fora da tabela) → `FORMATO_INVALIDO`. *Corrigido na BE-211 (2026-10-29): o exemplo aprovado, `ABC5S34`, tinha o `S` na posição 5, que pela §5 não é corrigida.* |
| CA-008 | `""` e `" - "` → `VAZIA`. |
| CA-009 | `ABC*234` e `ÁBC1234` → `CARACTERE_INVALIDO`. |
| CA-010 | `ABC123` e `ABC12345` → `COMPRIMENTO_INVALIDO`. |
| CA-011 | Uma entrada com dois motivos devolve o primeiro, pela ordem da §6. |
| CA-012 | A `placa_lida` original fica preservada na rejeição, para ser mostrada como evidência. |
| CA-013 | A `chave_comparacao` de `ABC1234` é `ABC1C34` e a de `ABC1C34` é ela mesma. Há testes para os 10 dígitos e para uma letra de K a Z na posição 5. |
| CA-014 | Uma placa com correções sai com elas registradas e **pode** seguir para a autorização automática (P-2); a regra não marca a placa como "precisa de operador". |

## 10. Impacto

- **Código:** cria `dominio/placa/` na BE-211.
- **Esquema (BE-502):** a `leitura_placa` precisa guardar a `placa_lida`, a `placa_normalizada`, o `formato`, as correções e o motivo da rejeição (C-002 item 6). A placa do `veiculo` precisa de unicidade pela `chave_comparacao`, para impedir que `ABC1234` e `ABC1C34` sejam cadastrados como dois veículos (afeta também CT-101).
- **Segurança operacional:** a regra só corrige onde o tipo esperado é igual nos dois formatos, e toda correção fica visível. Com o conjunto ampliado (P-1) e a autorização automática de placa corrigida (P-2), aumenta a chance de uma leitura errada virar a placa de **outro** veículo cadastrado. As barreiras que continuam valendo são: confiança mínima, um único agendamento válido no dia e na faixa, e as correções visíveis no diagnóstico. Medir isso com o conjunto de imagens de teste (BE-402).
- **Reversibilidade:** alta.

## 11. Perguntas

| ID | Pergunta | Resposta |
|---|---|---|
| P-1 | Quais confusões do OCR corrigir? | **Conjunto ampliado**: O/0, I/1, B/8, S/5, Z/2, G/6, A/4 e T/7 (autor, 2026-10-29). |
| P-2 | Placa corrigida pode autorizar sozinha? | **Sim**, se as outras condições da RN-002 forem atendidas (autor, 2026-10-29). |
| P-3 | Placa antiga e convertida são o mesmo veículo? | **Sim, conforme a legislação** (autor, 2026-10-29): §5.2. Tabela conferida no texto oficial. |
| P-4 | Quais separadores remover? | **Espaço, hífen e ponto** (recomendação confirmada pelo autor, 2026-10-29). |
