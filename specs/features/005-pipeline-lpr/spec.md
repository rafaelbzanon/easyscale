# Spec 005 — Pipeline de LPR

- **Trilha:** Backend
- **Status:** Implementada (BE-402, 2026-10-30; aceita pelo autor em 2026-11-02). Aprovada pelo autor em 2026-10-29 (respostas de P-1 a P-10 iguais às recomendações; P-7 com observação)
- **Respostas do autor (2026-10-29):** P-1 = (a) OpenCV; P-2 = candidatos separados; P-3 = de 0 a 1; P-4 a P-6 = sim; P-7 = ainda não há imagens reais, o autor vai obter o acervo da empresa (imagens reais registradas durante pesagens); P-8 a P-10 = sim
- **Data:** 2026-10-29
- **Tarefa:** BE-401 (spec); implementação na BE-402 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-006, RF-007, RF-008, RF-022 (dados para o diagnóstico), RN-002 (parte da confiança), RN-003, RNF-009, RNF-011, RNF-012, RNF-013
- **Código (futuro):**
  - `backend/src/pesagem/lpr/` (`CONVENCOES.md` §2);
  - a regra de seleção, que é pura, em `backend/src/pesagem/dominio/placa/`.

---

## 1. Contexto e origem

- **[ARTIGO §2, §3.1–3.3]:** a imagem da placa vem de uma câmera ou de imagens já capturadas (RF-006). O reconhecimento tem três etapas, com OpenCV + EasyOCR (RF-007):
  1. pré-processamento;
  2. localização da região da placa;
  3. leitura dos caracteres.
- **Validação:** o artigo valida o protótipo com imagens de placas, sem câmera (RNF-012). Por isso, a primeira fonte de imagem é uma **pasta de imagens** (BE-401). As câmeras dependem da Q-06, que segue aberta.
- **Já definido:**
  - normalização da placa e chave de comparação: spec 003;
  - entrada autorizada só com confiança **igual ou superior** ao limiar configurado (RN-002);
  - o LPR **não decide autorização**, apenas informa (`AMBIENTE.md` §4.1);
  - um falso positivo de autorização pesa mais que um falso negativo (`AMBIENTE.md` §14.3);
  - o OCR fica atrás da fronteira `LeitorPlaca` (`AMBIENTE.md` §9.2, `CONVENCOES.md` §4.4).
- **Item 14 do C-002:** a escala da `confianca` é fixada aqui (P-3). A coluna do banco é da BE-502.

## 2. Objetivo

1. **Fonte de imagem:**
   - criar a interface `FonteImagem`;
   - criar a fonte por pasta de imagens.
2. **Pipeline:**
   - recebe uma imagem;
   - devolve as ROIs encontradas e os textos lidos em cada uma, com a confiança;
   - devolve tudo isso em um resultado estruturado, que serve também à tela de diagnóstico (RF-022).
3. **Seleção da placa (domínio, pura):**
   - recebe os textos candidatos;
   - devolve uma placa aceita ou uma rejeição com motivo;
   - aplica a spec 003 e o limiar de confiança vindo de configuração.
4. **Avaliação reprodutível sem câmera:**
   - formato do `gabarito.csv`;
   - métricas, com a aceitação incorreta em destaque.

## 3. Fora de escopo

- **Câmeras** (de rede, local) e arquivo de vídeo: dependem da Q-06 e terão spec própria. A interface `FonteImagem` já os comporta.
- **Votação entre quadros** (R-03): com pasta de imagens, uma imagem é uma tentativa. Fica para quando houver câmera.
- **Consulta ao cadastro e ao agendamento, e a decisão de autorização:** são da orquestração (BE-601) e da autorização (BE-201/BE-213).
- **Guarda da imagem de evidência e retenção:** dependem da Q-08 e da D-13, e a persistência é da BE-502. Aqui a imagem fica só em memória.
- **Contrato HTTP da tela de diagnóstico:** CT-105.
- **Meta numérica de acerto:** só será definida com dados reais (`AMBIENTE.md` §14.3).
- **GPU:** a D-09 assume CPU.

## 4. Atores

Nenhum ator humano. Quem chama é a orquestração. Os testes e a avaliação usam a fonte por pasta e um leitor simulado.

## 5. Dados e interfaces **[PROPOSTA]**

Os nomes seguem o `CONVENCOES.md` §4.4, §4.5 e §10. Os termos novos (marcados com \*) entram no glossário antes do código (§11).

### 5.1 Fonte de imagem (`lpr/fontes/`)

| Nome | Conteúdo |
|---|---|
| `FonteImagem` (interface) | `async def obter_imagem() -> ImagemCapturada \| FalhaImagem`. |
| `ImagemCapturada`\* | Três campos:<br>• `pixels`: matriz do OpenCV;<br>• `capturada_em`: `datetime` com fuso, de relógio injetado;<br>• `origem`: `str` com o nome do arquivo relativo à pasta. **O nome nunca contém a placa** (`CONVENCOES.md` §9). |
| `FalhaImagem`\* | `motivo: MotivoFalhaImagem` e `origem: str \| None`. |
| `MotivoFalhaImagem`\* | Três motivos:<br>• `SEM_IMAGEM`: a pasta acabou;<br>• `IMAGEM_INVALIDA`: o arquivo não decodifica, ou a imagem está vazia;<br>• `FONTE_INDISPONIVEL`: a pasta deixou de existir ou não pode ser lida. |
| `FontePastaImagens` | Criada com a pasta e o relógio. Comportamento na §6.1. |

### 5.2 Pipeline (`lpr/`)

| Nome | Conteúdo |
|---|---|
| `Roi` | `x`, `y`, `largura` e `altura`, em pixels da imagem original. |
| `TextoLido`\* | `texto: str` (bruto, como o OCR devolveu) e `confianca: Decimal` (P-3). |
| `TextoOcr`\* | `texto: str` e `confianca: float`, exatamente como o OCR devolveu. É entrada não confiável: o pipeline valida e converte para `TextoLido` (§6.2, passo 4). *Acrescentado na BE-402 (2026-10-30): a spec dizia que o leitor devolvia `TextoLido`; com isso, a validação e o truncamento ficariam repetidos em cada leitor.* |
| `LeitorPlaca` (interface) | `def ler(recorte) -> Sequence[TextoOcr]`. É **síncrona**, porque o OCR é trabalho de CPU; o pipeline a chama em `asyncio.to_thread` (P-9). |
| `LeitorEasyOcr` | Implementação real, na BE-402. |
| `LeitorEasyOcr` (detalhe) | Criado com a pasta dos modelos e a lista de idiomas, ambas vindas de configuração, sem valor padrão no código. Usa `gpu=False` (D-09) e `download_enabled=False` (P-10): sem modelo, levanta `ErroConfiguracaoLpr` na criação. Não usa `allowlist`, porque forçar o OCR a só devolver A–Z e 0–9 troca um caractere estranho por um "parecido" e pode criar uma placa válida errada. |
| `LeitorPlacaSimulado` | Devolve, a cada chamada, a próxima resposta de uma lista configurada (textos, ou uma exceção a levantar); esgotada a lista, devolve nenhum texto. Guarda o tamanho de cada recorte recebido. Serve para testar o pipeline sem o EasyOCR. |
| `baixar_modelos` | `python -m pesagem.lpr.baixar_modelos <pasta> <idioma>...`: o **comando explícito** que baixa os modelos (P-10). É o único ponto com download habilitado. |
| `LeituraRoi`\* | `roi: Roi` e `textos: tuple[TextoLido, ...]`. |
| `LeituraPlaca` | O resultado do pipeline para uma imagem:<br>• `origem` e `capturada_em`;<br>• `pixels`, mantidos para a evidência e o diagnóstico;<br>• `leituras: tuple[LeituraRoi, ...]`. |
| `FalhaLeitor`\* | O leitor levantou exceção ou devolveu confiança fora de `[0, 1]`. Tem o campo `origem`. |
| `reconhecer_placa(fonte, leitor, parametros)` | `async`. Devolve `LeituraPlaca`, ou então `FalhaImagem` ou `FalhaLeitor`. |
| `ParametrosLocalizacao`\* | Parâmetros da localização por OpenCV, vindos de configuração (P-1): `limiar_bordas_inferior` e `limiar_bordas_superior` (Canny), `area_minima_px`, `proporcao_minima` e `proporcao_maxima` (largura ÷ altura) e `maximo_rois`. Validados ao criar (`ErroConfiguracaoLpr`). Os **valores** não estão definidos: serão calibrados com o conjunto de avaliação e documentados como exemplo, nunca como padrão escondido no código. |

### 5.3 Seleção da placa (`dominio/placa/`)

O `dominio` não importa o `lpr` (`CONVENCOES.md` P-4). Por isso, a orquestração converte cada `TextoLido` para o tipo do domínio. É a mesma solução da spec 004, P-6.

| Nome | Conteúdo |
|---|---|
| `CandidatoPlaca`\* | `placa_lida: str` e `confianca: Decimal`. |
| `ParametrosLeituraPlaca`\* | `limiar_confianca: Decimal`. Ao ser criado, valida: valor finito e `0 < limiar ≤ 1`. Se não, `ErroParametrosInvalidos` (P-4). |
| `selecionar_placa(candidatos, parametros)` | Devolve `PlacaSelecionada` ou `RejeicaoLeituraPlaca`. Regras na §6.3. |
| `PlacaSelecionada`\* | `placa: PlacaNormalizada` (spec 003), `confianca: Decimal` e `indice: int`. O `indice` é a posição do candidato na entrada, para o diagnóstico apontar a ROI. |
| `RejeicaoLeituraPlaca`\* | `motivo: MotivoRejeicaoLeituraPlaca`. |
| `MotivoRejeicaoLeituraPlaca`\* | `SEM_CANDIDATO`, `PLACA_INVALIDA`, `AMBIGUA` ou `CONFIANCA_BAIXA`. |

### 5.4 Configuração

Os nomes são exemplos de formato; os finais saem na spec de configuração.

| Variável | Regra |
|---|---|
| `PESAGEM_LPR_LIMIAR_CONFIANCA` | **Obrigatória e sem valor padrão.** Se estiver ausente ou inválida, o sistema não inicia (`AMBIENTE.md` §8). O valor real sai da avaliação (P-4). |
| `PESAGEM_CAMERA_PASTA_IMAGENS` | A pasta da fonte. |
| Parâmetros da localização | Ver P-1. |
| Pasta dos modelos do EasyOCR | Ver P-10. |

## 6. Comportamento normal

### 6.1 Fonte por pasta

- **Na criação:**
  - lista os arquivos `.jpg`, `.jpeg` e `.png`, sem diferenciar maiúsculas de minúsculas, e ignora os outros;
  - **não** entra em subpastas;
  - ordena por nome. A ordem é determinística.
- **A cada chamada:** devolve o próximo arquivo, decodificado com o OpenCV.
- **No fim da lista:** devolve sempre `SEM_IMAGEM`. Nunca volta ao começo, para a mesma placa não "chegar" duas vezes sem ninguém perceber.
- **Leitura de arquivos:** é I/O, então roda em `asyncio.to_thread`.

### 6.2 Pipeline

1. Obtém a imagem da fonte. Se a fonte devolver uma falha, o pipeline a repassa **sem chamar o leitor**.
2. **Pré-processamento e localização (OpenCV):** encontra as ROIs candidatas (P-1). Se não houver nenhuma ROI, devolve `LeituraPlaca` com `leituras` vazio.
   - Pré-processamento: tons de cinza e detecção de bordas (Canny).
   - Localização: retângulo envolvente de cada contorno; ficam os que têm área e proporção dentro dos parâmetros, ordenados da maior área para a menor, até `maximo_rois`.
3. **OCR:** para cada ROI, entrega o recorte ao `LeitorPlaca`. Cada texto devolvido é um candidato **separado** (P-2).
4. **Confiança:** a do leitor é convertida para `Decimal` com 3 casas, **truncada para baixo**. Truncar nunca aumenta a confiança (P-3).
5. **Retorno:** devolve tudo, incluindo os textos que depois serão rejeitados, porque a tela de diagnóstico mostra todas as interpretações (RF-022).

O pipeline **não** normaliza, **não** aplica o limiar e **não** decide nada.

### 6.3 Seleção da placa (domínio)

Os passos são aplicados nesta ordem:

1. **Sem candidatos:** se não houver candidatos, o resultado é `SEM_CANDIDATO`.
2. **Normalização:** cada candidato passa pela normalização da spec 003. Os candidatos rejeitados são **ignorados** daqui em diante (por exemplo, `BRASIL` ou o nome de uma cidade). Se nenhum sobrar, o resultado é `PLACA_INVALIDA`.
3. **Ambiguidade:** os candidatos válidos são agrupados por `chave_comparacao`.
   - Mais de um grupo dá `AMBIGUA`, **mesmo que algum esteja abaixo do limiar** (P-5). Nunca se escolhe automaticamente (`AGENTS.md` §7.2).
4. **Confiança do grupo:** a confiança do único grupo é a **menor** entre os candidatos dele, e o candidato devolvido é o dessa menor confiança (P-5). Em empate, vale o primeiro na ordem de entrada.
5. **Limiar:** se a confiança for menor que o limiar, o resultado é `CONFIANCA_BAIXA`. O limiar é **inclusivo**: confiança igual ao limiar é aceita (RN-002).
6. **Aceite:** se nada acima rejeitou, o resultado é `PlacaSelecionada`.

### 6.4 Avaliação sem câmera (RNF-012) — ver P-7 e P-8

- **Local:** a pasta de avaliação tem as imagens e um `gabarito.csv`. Os nomes das imagens são sequenciais e não contêm a placa (`CONVENCOES.md` §9).
- **Formato do `gabarito.csv`:**
  - UTF-8, separado por vírgula, com cabeçalho obrigatório;
  - colunas `arquivo,placa_esperada,observacao`;
  - `arquivo`: caminho relativo à pasta. A subpasta (`diurno/`, `noturno/`, `inclinadas/`) indica a condição;
  - `placa_esperada`: a placa normalizada (7 caracteres). Fica **vazia** quando a imagem não tem placa legível e o esperado é a rejeição;
  - `observacao`: opcional e livre, **sem dado pessoal**.
- **Gabarito inválido:** a avaliação para com `ErroGabaritoInvalido` e não produz métricas. São inválidos:
  - cabeçalho errado;
  - `arquivo` repetido ou inexistente;
  - imagem na pasta que não está no gabarito;
  - `placa_esperada` inválida pela spec 003.
- **Resultado por imagem:** a comparação usa a `chave_comparacao`.

  | Resultado | Quando |
  |---|---|
  | `ACERTO` | Placa selecionada e igual à esperada. |
  | `ACEITACAO_INCORRETA` | Placa selecionada e diferente da esperada, ou placa selecionada quando nenhuma era esperada. **Falso positivo de autorização.** |
  | `REJEICAO_SEGURA` | Havia placa esperada, mas houve rejeição (falso negativo: o caso vai para o operador). |
  | `REJEICAO_CORRETA` | Nenhuma placa esperada, e houve rejeição. |

- **Relatório:**
  - a contagem e a taxa de cada resultado, no total e por subpasta;
  - **a taxa de aceitação incorreta vem primeiro**;
  - o limiar usado e a latência do OCR por imagem (média e máxima), que ajudam a resolver a D-05;
  - **nunca** as placas: o relatório traz só o nome do arquivo.
- **Sem meta numérica:** enquanto não houver meta, a avaliação não reprova nada; ela mede e relata.

## 7. Comportamento em falha

| Situação | Resultado | Observação |
|---|---|---|
| Pasta da fonte inexistente na criação | `ErroConfiguracaoLpr` | Na partida. |
| Pasta removida durante o uso | `FalhaImagem(FONTE_INDISPONIVEL)` | — |
| Arquivo corrompido ou vazio | `FalhaImagem(IMAGEM_INVALIDA, origem)` | A próxima chamada segue para o arquivo seguinte. |
| Fim da pasta | `FalhaImagem(SEM_IMAGEM)` | Não volta ao começo. |
| O leitor levanta exceção | `FalhaLeitor` | A exceção vem de biblioteca de terceiros. Ela é convertida em resultado e registrada em log com o tipo do erro, **sem a imagem e sem o texto**. Não é engolida (`AGENTS.md` §10). |
| O leitor devolve confiança não finita ou fora de `[0, 1]` | `FalhaLeitor` | A imagem inteira é descartada, nunca "corrigida". |
| Nenhuma ROI, ou nenhum texto | `LeituraPlaca` vazia → `SEM_CANDIDATO` | Não autoriza; vai para o operador com a imagem (RN-003). |
| Limiar ausente, não numérico, não finito, `≤ 0` ou `> 1` | Erro de configuração na partida | Nunca usa um limiar "chutado". |
| Modelos do EasyOCR ausentes | Erro na partida (P-10) | Nunca baixa da internet durante a operação. |

`ErroConfiguracaoLpr` e `ErroGabaritoInvalido` derivam de `ErroLpr` (`CONVENCOES.md` §4.5). As falhas de operação são resultados, não exceções, como na spec 004 (P-2).

## 8. Regras de negócio e privacidade

- **RN-002:** o limiar é inclusivo. A seleção é só uma das condições: cadastro, agendamento único e estado continuam com a orquestração.
- **RN-003 e RNF-009:** toda dúvida (sem candidato, placa inválida, ambígua ou confiança baixa) vira rejeição com motivo. Nunca há palpite.
- **RNF-013 (privacidade):**
  - o LPR **não grava** imagens nem recortes em disco;
  - o LPR **não registra** placas em log;
  - a imagem fica só no resultado em memória. Guardar ou não a evidência é decisão da Q-08 e da D-13.
- **RNF-011:** o OCR e a leitura de arquivo nunca rodam no laço de eventos (P-9).

## 9. Estados afetados

Nenhum estado da operação. Uma rejeição leva ao estado "não autorizado, encaminhado" da BE-201.

## 10. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | **Fonte, listagem:** uma pasta com `b.png`, `a.JPG`, `c.jpeg`, `d.txt` e uma subpasta devolve `a.JPG`, `b.png` e `c.jpeg`, nessa ordem. O `.txt` e a subpasta são ignorados. |
| CA-002 | **Fonte, fim da pasta:** depois do último arquivo, `obter_imagem()` devolve `SEM_IMAGEM`, e continua devolvendo nas chamadas seguintes. |
| CA-003 | **Fonte, arquivo inválido:** um arquivo corrompido devolve `IMAGEM_INVALIDA` com `origem`, e a chamada seguinte devolve o próximo arquivo válido. |
| CA-004 | **Fonte, pasta:** pasta inexistente na criação levanta `ErroConfiguracaoLpr`. Pasta removida depois da criação devolve `FONTE_INDISPONIVEL`. |
| CA-005 | **Fonte, dados da imagem:** `capturada_em` vem do relógio injetado, com fuso, e `origem` é o nome do arquivo. |
| CA-006 | **Localização:** numa imagem sintética com um retângulo de placa desenhado, ao menos uma ROI contém inteiramente o retângulo. A imagem é gerada pelo próprio teste, sem dado pessoal (P-7). |
| CA-007 | **Localização:** numa imagem sintética sem placa (fundo uniforme), não há ROI, e o leitor não é chamado. |
| CA-008 | **Pipeline e leitor:** com o `LeitorPlacaSimulado`, cada ROI é entregue ao leitor e cada texto volta como candidato separado, ligado à sua ROI. |
| CA-009 | **Pipeline, falha da fonte:** a falha é repassada, e o leitor não é chamado. |
| CA-010 | **Pipeline, falha do leitor:** exceção ou confiança `NaN`, `-0.1` ou `1.01` resultam em `FalhaLeitor`. O log não contém o texto lido. |
| CA-011 | **Confiança:** `0.98765` vira `0.987`, `0.9999` vira `0.999` e `1.0` vira `1.000`. A confiança nunca aumenta. |
| CA-012 | **Seleção, aceite:** um único candidato válido, com confiança igual ao limiar, é aceito. Um pouco acima também. |
| CA-013 | **Seleção, limiar:** com confiança `0.001` abaixo do limiar, o resultado é `CONFIANCA_BAIXA`. |
| CA-014 | **Seleção, sem placa:** sem candidatos, o resultado é `SEM_CANDIDATO`. Só com candidatos inválidos (`BRASIL`, `GRAMADO`), é `PLACA_INVALIDA`. |
| CA-015 | **Seleção, ambiguidade:** dois candidatos válidos com chaves diferentes resultam em `AMBIGUA`, mesmo que um deles esteja abaixo do limiar. |
| CA-016 | **Seleção, mesma placa:** `ABC1234` (0.95) e `ABC1C34` (0.80) têm a mesma chave. Não é ambiguidade: a confiança considerada é `0.80` e o candidato devolvido é o de `0.80`. |
| CA-017 | **Seleção, ordem dos motivos:** `BRASIL` mais uma placa válida abaixo do limiar resulta em `CONFIANCA_BAIXA`, não em `PLACA_INVALIDA`. |
| CA-018 | **Seleção, limiar inválido:** `0`, `-0.5`, `1.5`, `NaN` e `Infinity` levantam `ErroParametrosInvalidos` ao criar `ParametrosLeituraPlaca`. O valor `1` é aceito. |
| CA-019 | **Avaliação, gabarito:** um gabarito válido é lido. Cada caso inválido da §6.4 levanta `ErroGabaritoInvalido`. |
| CA-020 | **Avaliação, métricas:** a classificação dos quatro resultados usa a `chave_comparacao` (`ABC1234` esperado e `ABC1C34` selecionado contam como `ACERTO`). O relatório não contém placas. |
| CA-021 | **Arquitetura:**<br>• só o `lpr` importa `cv2` e `easyocr`;<br>• o `dominio` não importa o `lpr`;<br>• o `lpr` não importa o `dominio`;<br>• o `LeitorPlacaSimulado` não importa `easyocr`. |
| CA-022 | **Privacidade:** nenhum arquivo é criado durante o pipeline (verificado numa pasta temporária), e nenhum registro de log contém o texto lido. |

Os testes de CA-006 a CA-010 usam OpenCV, mas não o EasyOCR. O EasyOCR só aparece na avaliação (P-8), o que mantém separados os testes do pipeline e os do OCR (`AMBIENTE.md` §14.3).

## 11. Impacto

- **Código novo:**
  - `lpr/__init__.py`, `lpr/erros.py`, `lpr/resultado.py`, `lpr/leitor_placa.py`, `lpr/leitor_simulado.py`, `lpr/leitor_easyocr.py`, `lpr/preprocessamento.py`, `lpr/localizacao.py` e `lpr/pipeline.py`;
  - `lpr/fontes/interface.py` e `lpr/fontes/pasta_imagens.py`;
  - `dominio/placa/selecao.py`;
  - `lpr/baixar_modelos.py`, o comando explícito da P-10 (acrescentado na BE-402);
  - testes espelhados em `tests/unitarios/lpr/` e `tests/unitarios/dominio/placa/test_selecao.py`; a avaliação em `tests/avaliacao/test_avaliacao_lpr.py` (P-8).
- **Dependências (BE-402, pedem aprovação com justificativa e versões verificadas na hora):**
  - OpenCV (**recomendo** `opencv-python-headless`, sem interface gráfica, adequado ao Docker) e EasyOCR. As duas são tecnologias [DEFINIDO].
  - O EasyOCR traz o PyTorch, que é pesado.
  - **A verificar:** se há pacotes para o Python 3.14 local e para o 3.12 mínimo, e se há tipos para o `mypy` estrito. Se não houver, pode ser preciso um `ignore_missing_imports` só para o `easyocr`, que entraria no `pyproject.toml` com justificativa.
- **`backend/pyproject.toml`:** marcador `avaliacao`, fora da execução padrão (P-8).
- **Trilha A (sincronizar depois da aprovação):**
  - os termos novos (\*) no `CONVENCOES.md` §10 e no `specs/glossario.md`;
  - a escala da `confianca` no glossário;
  - `selecao.py`, `leitor_simulado.py`, `pipeline.py` e `fontes/interface.py` na árvore da §2.
- **`AMBIENTE.md`:** D-05 (OCR em `asyncio.to_thread`), D-08 (modelos), Q-09 (imagens de teste).
- **BE-502:**
  - `leitura_placa.confianca` passa de `NUMERIC(5,2)` para a escala 0–1 com 3 casas;
  - as ROIs e os motivos de rejeição (item 6 do C-002).
- **Segurança operacional:** nada é acionado. O risco é a aceitação incorreta, mitigada pelas regras da §6.3 e medida na §6.4 (R-03).
- **Reversível:** sim. Nada é persistido e nenhuma interface pública existe ainda.

## 12. Perguntas

| P | Pergunta | Recomendação | Resposta |
|---|---|---|---|
| P-1 | **Como localizar a placa?**<br>(a) OpenCV: contornos com filtro de proporção e área, gerando ROIs candidatas, que o EasyOCR lê.<br>(b) Detector de texto do próprio EasyOCR na imagem inteira.<br>(c) (a), e (b) como reserva. | **(a)**. Segue o artigo (localização com OpenCV, RF-007) e gera a ROI que a tela de diagnóstico mostra. A (c) dobra o custo e aumenta a chance de ambiguidade. Se a avaliação mostrar que a (a) falha muito, reabrimos. | (a) (autor, 2026-10-29) |
| P-2 | **Textos de uma mesma ROI:**<br>(a) cada texto é um candidato separado;<br>(b) juntar os textos da ROI da esquerda para a direita. | **(a)**. A faixa superior da placa (`BRASIL`, nome da cidade) também é lida. Juntar tudo estragaria a placa, enquanto separado a spec 003 descarta o que não é placa. Se o OCR dividir a placa em dois pedaços, ela é rejeitada (seguro). | (a) (autor, 2026-10-29) |
| P-3 | **Escala da confiança:**<br>(a) de 0 a 1, `Decimal` com 3 casas, truncada para baixo;<br>(b) de 0 a 100, como no `NUMERIC(5,2)` do esquema. | **(a)**. É a escala que o EasyOCR devolve, então não há conversão. Truncar nunca aumenta a confiança. | (a), de 0 a 1 (autor, 2026-10-29) |
| P-4 | **Limiar:** obrigatório, sem padrão, com `0 < limiar ≤ 1`, e valor real definido pela avaliação? | **Sim**. Não há número no artigo, e inventar um seria inventar regra. Para desenvolver, você define o valor no seu `.env` local. | Sim (autor, 2026-10-29) |
| P-5 | **Mesma placa em mais de um candidato:** usar a **menor** confiança? E um candidato válido diferente, mesmo abaixo do limiar, conta como ambiguidade? | **Sim e sim**. As duas escolhas são as mais conservadoras: na dúvida, rejeita e encaminha. | Sim e sim (autor, 2026-10-29) |
| P-6 | **Fim da pasta:** devolver sempre `SEM_IMAGEM`, sem voltar ao começo? | **Sim**. Evita que a mesma imagem "chegue" de novo sem ninguém perceber. | Sim (autor, 2026-10-29) |
| P-7 | **Imagens de teste (Q-09):** você tem imagens reais de placas? Em que condições de licença e de consentimento? | **Testes automáticos:** imagens **sintéticas**, geradas pelo próprio teste, sem dado pessoal, que podem ficar no repositório.<br>**Imagens reais:** ficam **fora do repositório** por padrão, numa pasta indicada por configuração. Só entram no repositório com licença e privacidade claras, registradas em `dados-teste/placas/README.md`. | Ainda não há imagens. O autor vai obter o acervo da empresa (imagens reais registradas durante pesagens). Até lá: só imagens sintéticas. O acervo real fica **fora do repositório** (§12.1). |
| P-8 | **Como rodar a avaliação?** | Um teste do pytest marcado `avaliacao`, **fora da execução padrão**. Ele só roda quando chamado explicitamente e quando a pasta está configurada. O código fica em `backend/tests/avaliacao/`, que pode importar o `lpr` e o `dominio`. O cálculo das métricas tem testes unitários próprios. | Sim (autor, 2026-10-29) |
| P-9 | **OCR sem bloquear a API (D-05):** o `LeitorPlaca` é síncrono e o pipeline o chama em `asyncio.to_thread`? | **Sim**, sem dependência nova, como na spec 004. A avaliação mede a latência. Se ela for alta, a D-05 é reaberta (processo separado). | Sim (autor, 2026-10-29) |
| P-10 | **Modelos do EasyOCR (D-08):**<br>• baixar uma vez, por comando explícito, para uma pasta configurada;<br>• na operação, rodar sem download (modelos ausentes impedem a partida);<br>• usar CPU (D-09). | **Sim**. O sistema não depende de internet na balança, e nada é baixado sem você saber. O nome exato das opções do EasyOCR será verificado na documentação durante a BE-402. | Sim (autor, 2026-10-29) |

### 12.1 Observação sobre o acervo real (P-7)

As imagens da empresa são registros reais de pesagens. Elas podem mostrar placas, motoristas e outros veículos, então são dados pessoais (RNF-013, R-08).

- Ficam **fora do repositório**, numa pasta local indicada por configuração.
- Não são copiadas para o Git, para os logs nem para os relatórios. O relatório da §6.4 traz só nomes de arquivo sequenciais.
- **A confirmar com o autor antes de usar o acervo:** a empresa autoriza o uso para o TCC? Há restrição de publicação, por exemplo de imagens ilustrativas no artigo? Isso fica na Q-09.
- Montar o `gabarito.csv` com as placas esperadas é trabalho manual do autor. O gabarito também contém placas, então também fica fora do repositório.
