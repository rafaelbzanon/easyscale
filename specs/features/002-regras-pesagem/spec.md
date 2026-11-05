# Spec 002 — Regras de pesagem

- **Trilha:** Backend
- **Status:** Implementada (BE-212, 2026-10-29; aceita pelo autor em 2026-10-29). Aprovada pelo autor em 2026-10-29 ("pode prosseguir", com as recomendações de P-1 a P-3)
- **Data:** 2026-10-29
- **Tarefa:** BE-202 (spec); implementação na BE-212 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-014, RF-016, RN-004, RN-006, RNF-009
- **Código:** `backend/src/pesagem/dominio/pesagem/` (`aceitacao_peso.py`, `calculo_peso.py`) e `backend/src/pesagem/dominio/erros.py` (`CONVENCOES.md` §2, §4.5)

---

## 1. Contexto e origem

- Pelo artigo, o sistema registra as pesagens inicial e final e calcula o peso líquido automaticamente **[ARTIGO §1, §3.5, §4]** (RF-014, RF-016).
- O autor definiu em 2026-10-29 (Q-02, RN-006):
  - **CARGA:** líquido = final − inicial.
  - **DESCARGA:** líquido = inicial − final.
  - **Tolerância de movimentação:** ±20 kg, configurável. Dentro dela, a operação conta como "sem carga nem descarga".
  - Abaixo de −20 kg, o administrador intervém.
- Uma leitura só é aceita se estiver bem formada, dentro de uma faixa plausível e estável, e os parâmetros vêm de configuração (RN-004). Uma leitura rejeitada nunca é ajustada nem preenchida (`AGENTS.md` §7.2).
- O esquema de referência já calcula o líquido com a mesma fórmula, numa coluna gerada, e guarda os pesos como `NUMERIC(12,3)` (C-002 item 2).

## 2. Objetivo

Definir duas regras **puras**, sem I/O, sem relógio e sem configuração lida diretamente:
1. **Aceitação de peso:** decidir se uma sequência de leituras da balança produz um peso aceito.
2. **Peso líquido:** calcular o líquido e classificar o resultado.

## 3. Fora de escopo

- Ler a serial, decodificar quadros (`parser_quadro.py`) e tratar tempo esgotado. Isso é da BE-301. Esta spec recebe leituras já decodificadas.
- Decidir **quando** pesar, e se o peso é o inicial ou o final, e o que o administrador pode fazer depois do encaminhamento. Isso é da máquina de estados (BE-201).
- Verificar se o caminhão está no perímetro da balança (RF-027, Q-17).
- Persistência e ler os parâmetros do ambiente (BE-502, BE-701).
- Os **valores** dos parâmetros de aceitação (faixa, quantidade de leituras, variação, janela). Eles vêm de configuração; ver P-3.

## 4. Atores

Nenhum ator humano. Quem chama as regras é a orquestração (BE-601).

## 5. Dados de entrada e saída

Os identificadores seguem o `CONVENCOES.md`. Os tipos são **[PROPOSTA]**.

| Nome | Conteúdo |
|---|---|
| `LeituraPeso` | `peso_kg: Decimal` e `lida_em: datetime`, sempre com fuso horário. |
| `ParametrosAceitacaoPeso` | `peso_minimo_kg` e `peso_maximo_kg` (`Decimal`); `quantidade_leituras_estaveis` (`int`); `variacao_maxima_kg` (`Decimal`); `janela_estabilidade_ms` (`int`). |
| `ParametrosPesoLiquido` | `tolerancia_movimentacao_kg` (`Decimal`). *Incluído em 2026-10-29 (BE-212, aprovado pelo autor) para validar a tolerância ao criar os parâmetros, junto com a configuração, e não só no cálculo.* |
| `ResultadoAceitacaoPeso` | Ou um peso aceito (`peso_kg` e `lida_em`), ou uma rejeição com `motivo`. |
| `MotivoRejeicaoPeso` | `LEITURA_INVALIDA`, `FORA_DE_FAIXA`, `LEITURAS_INSUFICIENTES`, `INSTAVEL` ou `FORA_DE_ORDEM`. |
| `ResultadoPesoLiquido` | `peso_liquido_kg: Decimal`, sempre **o valor calculado**, e `classificacao`. |
| `ClassificacaoPesoLiquido` | `COM_MOVIMENTACAO`, `SEM_MOVIMENTACAO` ou `NEGATIVO_FORA_TOLERANCIA`. |

O tipo é `Decimal`, e não `float`: isso evita erro de arredondamento binário e casa com o `NUMERIC(12,3)` do esquema.

## 6. Comportamento normal

### 6.1 Aceitação de peso

A regra recebe as leituras mais recentes, em ordem cronológica, e os parâmetros. Ela aceita quando, ao mesmo tempo:
1. todas as leituras analisadas são válidas: `peso_kg` é um número finito e `lida_em` tem fuso;
2. as `lida_em` estão em ordem estritamente crescente;
3. as últimas `quantidade_leituras_estaveis` leituras cabem em `janela_estabilidade_ms`, contando da primeira à última;
4. nessas leituras, a diferença entre o maior e o menor peso é **≤** `variacao_maxima_kg`;
5. todas essas leituras estão em `[peso_minimo_kg, peso_maximo_kg]`, com os limites incluídos.

**Peso aceito:** a **última** leitura da série estável, com seu `peso_kg` e `lida_em` sem alteração. Não se usa média nem arredondamento (P-2).

### 6.2 Peso líquido

A regra recebe `tipo_operacao` (`CARGA` ou `DESCARGA`), `peso_inicial_kg`, `peso_final_kg` (ambos já aceitos pela §6.1) e `ParametrosPesoLiquido`, que traz a `tolerancia_movimentacao_kg`.
- **CARGA:** `peso_liquido_kg = peso_final_kg − peso_inicial_kg`.
- **DESCARGA:** `peso_liquido_kg = peso_inicial_kg − peso_final_kg`.

**Classificação:**

| Condição | Classificação | Significado |
|---|---|---|
| `peso_liquido_kg > +tolerância` | `COM_MOVIMENTACAO` | Operação normal. |
| `−tolerância ≤ peso_liquido_kg ≤ +tolerância` | `SEM_MOVIMENTACAO` | O caminhão entrou e saiu sem carregar nem descarregar. É um resultado aceito. |
| `peso_liquido_kg < −tolerância` | `NEGATIVO_FORA_TOLERANCIA` | **Não aceito.** A orquestração encaminha ao administrador (RN-006, RN-016). |

O `peso_liquido_kg` devolvido é **sempre o calculado**, mesmo em `SEM_MOVIMENTACAO`. Ele nunca é trocado por zero (RN-004).

## 7. Comportamento em falha

| Situação | Resultado | Observação |
|---|---|---|
| Lista de leituras vazia, ou com menos de `quantidade_leituras_estaveis` itens | Rejeição `LEITURAS_INSUFICIENTES` | Nunca um peso. |
| `peso_kg` não finito (`NaN`, `Infinity`) ou `lida_em` sem fuso | Rejeição `LEITURA_INVALIDA` | A leitura inválida não é descartada em silêncio para a regra seguir com as outras. |
| Instantes repetidos ou fora de ordem | Rejeição `FORA_DE_ORDEM` | Proteção contra dados reordenados ou duplicados. |
| Série estável que não cabe na janela de tempo, ou com variação acima do limite | Rejeição `INSTAVEL` | — |
| Peso abaixo do mínimo ou acima do máximo, incluindo peso negativo quando o mínimo é ≥ 0 | Rejeição `FORA_DE_FAIXA` | — |
| Mais de um motivo ao mesmo tempo | Rejeição com o primeiro motivo, nesta ordem: `LEITURAS_INSUFICIENTES` → `LEITURA_INVALIDA` → `FORA_DE_ORDEM` → `INSTAVEL` → `FORA_DE_FAIXA` | A ordem é fixa para os testes serem determinísticos. |
| Parâmetros incoerentes: mínimo ≥ máximo, mínimo < 0, quantidade < 2, variação < 0, janela ≤ 0, tolerância < 0, ou mínimo, máximo, variação ou tolerância não finitos (`NaN`, `Infinity`; incluído em 2026-10-29, BE-212, aprovado pelo autor) | Erro de configuração (um tipo de erro próprio do domínio), levantado **ao criar os parâmetros** | O sistema não deve operar com configuração inválida (fail-safe). |
| `tipo_operacao` fora de `CARGA`/`DESCARGA` | Erro do domínio, não uma classificação | — |
| `peso_inicial_kg` ou `peso_final_kg` ausente | Impossível pelo tipo; o mypy estrito acusa | O líquido só é calculado com os dois pesos aceitos (RN-006). |

## 8. Regras de negócio

- **RN-004:** aceitação com parâmetros vindos de configuração e sem ajuste de valor, pela §6.1.
- **RN-006:** fórmula, tolerância e encaminhamento do negativo, pela §6.2. A tara cadastrada **não** substitui um peso medido (C-002 item 16).
- **RNF-009 (fail-safe):** qualquer dúvida na §6.1 vira rejeição, nunca um peso aceito.

## 9. Estados afetados

Nenhum estado é alterado aqui. As regras devolvem resultados, e a BE-201 usa esses resultados nas transições (por exemplo, `NEGATIVO_FORA_TOLERANCIA` vira um estado que espera o administrador).

## 10. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | Uma série estável, dentro da faixa e da janela, é aceita, e o peso aceito é a última leitura sem alteração. |
| CA-002 | Uma série com variação 1 unidade acima de `variacao_maxima_kg` é rejeitada como `INSTAVEL`. Com variação exatamente igual ao limite, é aceita. |
| CA-003 | Uma série que excede `janela_estabilidade_ms` por 1 ms é rejeitada como `INSTAVEL`. Exatamente no limite, é aceita. |
| CA-004 | Um peso igual a `peso_minimo_kg` ou a `peso_maximo_kg` é aceito. 0,001 kg fora dos limites é rejeitado como `FORA_DE_FAIXA`. |
| CA-005 | Uma lista vazia ou curta demais dá `LEITURAS_INSUFICIENTES`. |
| CA-006 | `NaN`, `Infinity` ou `lida_em` sem fuso dão `LEITURA_INVALIDA`. |
| CA-007 | Instantes repetidos ou decrescentes dão `FORA_DE_ORDEM`. |
| CA-008 | Com mais de um motivo, o motivo devolvido segue a ordem da §7. |
| CA-009 | Cada combinação incoerente de parâmetros da §7, incluindo valores não finitos, levanta o erro de configuração ao criar `ParametrosAceitacaoPeso` ou `ParametrosPesoLiquido`. |
| CA-010 | CARGA calcula final − inicial e DESCARGA calcula inicial − final, com `Decimal` exato (por exemplo, 3 casas decimais sem perda). |
| CA-011 | Com tolerância de 20 kg: líquido +20, 0 e −20 dão `SEM_MOVIMENTACAO`; +20,001 dá `COM_MOVIMENTACAO`; −20,001 dá `NEGATIVO_FORA_TOLERANCIA`. |
| CA-012 | Em `SEM_MOVIMENTACAO`, o `peso_liquido_kg` devolvido é o valor calculado (por exemplo, 12), não 0. |
| CA-013 | Um `tipo_operacao` inválido levanta erro do domínio. |
| CA-014 | O módulo não importa nada proibido pelas regras P-4 e P-5. O teste de arquitetura da spec 001 já cobre isso. |

## 11. Impacto

- **Código:** cria `dominio/pesagem/` na BE-212. Nenhum outro módulo existe ainda.
- **Configuração:** variáveis futuras para os 6 parâmetros (`PESAGEM_BALANCA_PESO_MINIMO_KG`, ..., `PESAGEM_PESAGEM_TOLERANCIA_MOVIMENTACAO_KG`), com nomes finais definidos na BE-701. A tolerância tem valor padrão de **20 kg**, decisão do autor. Os outros 5 parâmetros **não têm valor padrão** (P-3).
- **Esquema (BE-502):** a coluna gerada já usa a mesma fórmula. Ainda falta lugar para a `classificacao`, e o `ck_pesagem_pesos` exige ≥ 0, o que é coerente com `peso_minimo_kg ≥ 0`.
- **Glossário:** termos novos `sem_movimentacao` / `com_movimentacao` (classificação) e `tolerancia_movimentacao_kg`. Eles entram em `CONVENCOES.md` §10 e no `glossario.md` com a aprovação desta spec.
- **Segurança operacional:** a regra só aceita peso com evidência de estabilidade, e o negativo vai para o administrador.
- **Reversibilidade:** alta, porque são funções puras.

## 12. Perguntas (respondidas em 2026-10-29 com as recomendações: P-1 = (a); P-2 = (a); P-3 = sem padrão)

| ID | Pergunta | Opções | Recomendação |
|---|---|---|---|
| P-1 | Como decidir que o peso está estável? | (a) **Só pelo software**: N leituras dentro de X kg numa janela de T ms; (b) só pelo indicador de estabilidade enviado pela balança, que depende do protocolo (Q-01); (c) as duas condições juntas, quando o indicador existir. | **(a) agora**; passar para (c) quando a Q-01 for respondida. O critério do software funciona com o simulador e não depende de um protocolo desconhecido. |
| P-2 | Qual valor da série estável é registrado? | (a) **a última leitura**; (b) a mediana; (c) a média. | **(a).** É um valor realmente lido, e a variação dele já foi limitada. A média seria um valor que a balança nunca mostrou. |
| P-3 | Há valores conhecidos para faixa (mínimo e máximo), N, variação e janela? | Informar os valores, ou deixar sem padrão até a Q-01 (a capacidade e a resolução da balança real). | **Sem padrão.** O sistema se recusa a iniciar sem esses valores configurados, e os testes usam valores próprios. Isso evita inventar números. |
