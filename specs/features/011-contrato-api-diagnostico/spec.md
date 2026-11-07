# Spec 011 — Contrato da API de diagnóstico

- **Trilha:** Contrato
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** CT-105; implementação na BE-705, uso na FE-305 e na FE-306 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-022, RF-023, RF-034, RN-003, RN-022, RNF-003, RNF-007, RNF-010, RNF-012, RNF-013
- **Decisões:** ADR-0004 (permissões), ADR-0005 (imagens sob demanda); specs 003, 004 e 005; spec 007 §3 (regras comuns); spec 009 (objetos e canal de eventos); spec 015 (orquestração e simuladores, combinada com o Gyro em 2026-11-07)

---

## 1. Contexto e origem

- A interface mostra as imagens das câmeras, as ROIs e as interpretações do reconhecimento (texto lido, placa normalizada, confiança, decisão e motivo), o histórico de reconhecimentos e o estado dos dispositivos com o modo real ou simulado (RF-022, RF-023; `AMBIENTE.md` §10.1).
- Só as imagens das decisões são salvas, até o administrador pedir a exclusão com motivo (RN-022). A imagem atual das câmeras é buscada sob demanda e não é salva (ADR-0005 §4.8).
- O artigo valida o protótipo em ambiente controlado, com imagens de placas e simulação serial da balança e das cancelas **[ARTIGO §2]** (RNF-003, RNF-007). A §6.4 dá a esse ambiente um controle pela API.
- Frontend e backend só se conhecem por este documento (S-3). Mudar algo aqui exige uma tarefa CT-9xx (S-4).

## 2. Objetivo

Definir as rotas, os campos, os erros e as permissões do diagnóstico e do controle dos simuladores, com critérios verificáveis pelos dois lados.

## 3. Fora de escopo

- Vídeo contínuo (ADR-0005 P-A).
- Nomes e tipos das câmeras físicas (Q-06). Há duas fontes: a de identificação, na entrada, e a de posição (spec 015).
- Novos eventos: o diagnóstico usa o canal da spec 009 (`balanca`, `cancela`, `posicao`, `identificacao`, `leitura_placa`).
- Simular falha da câmera de identificação ou do OCR: a spec 015 não prevê esse cenário.

## 4. Rotas e permissões

A forma das respostas, os erros e a paginação seguem a spec 007 §3. As rotas com `POST` seguem a spec 012 §6.9.

### 4.1 Diagnóstico

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/leituras-placa` | Histórico de reconhecimentos, inclusive os não autorizados (§5.1) | 200 | `CONSULTAR_OPERACAO` |
| `GET /api/leituras-placa/{leitura_placa_id}` | Uma leitura, com ROIs e textos (§5.2) | 200 | `CONSULTAR_IMAGENS_DECISAO` |
| `GET /api/imagens-decisao/{imagem_id}` | Dados da imagem salva (§5.3) | 200 | `CONSULTAR_IMAGENS_DECISAO` |
| `GET /api/imagens-decisao/{imagem_id}/conteudo` | Bytes da imagem salva | 200, `image/jpeg` | `CONSULTAR_IMAGENS_DECISAO` |
| `POST /api/imagens-decisao/{imagem_id}/excluir` | Exclui os bytes (§6.2) | 200, com os dados da imagem | `EXCLUIR_IMAGENS_DECISAO` |
| `GET /api/cameras/{camera}/imagem-atual` | Imagem mais recente da fonte (§6.3); `camera` é `identificacao` ou `posicao` | 200, `image/jpeg` | `CONSULTAR_IMAGENS_TEMPO_REAL` |
| `GET /api/dispositivos` | Estado dos dispositivos (§5.4) | 200 | `CONSULTAR_OPERACAO` |

### 4.2 Simuladores (§6.4)

| Método e rota | Efeito | Sucesso | Permissão |
|---|---|---|---|
| `GET /api/simuladores` | Cenários atuais | 200 | `CONTROLAR_SIMULADORES` |
| `POST /api/simuladores/balanca` | Troca o cenário da balança | 200, com os cenários | `CONTROLAR_SIMULADORES` |
| `POST /api/simuladores/cancelas/{cancela}` | Troca o cenário de uma cancela; `cancela` é `entrada` ou `saida` | 200, com os cenários | `CONTROLAR_SIMULADORES` |
| `POST /api/simuladores/posicao` | Troca o cenário da fonte de posição | 200, com os cenários | `CONTROLAR_SIMULADORES` |
| `POST /api/simuladores/chegadas` | Simula a chegada de uma placa | 202 | `CONTROLAR_SIMULADORES` |

`CONTROLAR_SIMULADORES` é uma permissão nova, só do `ADMINISTRADOR`, a incluir no ADR-0004 §4.3.

### 4.3 Acesso por perfil (ADR-0004 §4.3)

| Perfil | Acesso |
|---|---|
| `ADMINISTRADOR` | Tudo, inclusive excluir imagens e controlar os simuladores. |
| `OPERADOR` | Consulta, imagens das decisões e imagem atual. |
| `AUDITOR` | Consulta e imagens das decisões; **não** vê a imagem atual (Q-08). |

## 5. Recursos e campos

Campo sem valor vem `null`. Decimais trafegam como texto (spec 007 §3.1).

### 5.1 Lista de leituras

Itens no formato `LeituraPlaca` da spec 009 §5.2.

Filtros: `data_inicio`, `data_fim` (sobre `decidida_em`, no fuso do pátio), `decisao`, `motivo`, `pesagem_id`, `placa` (compara pela `chave_comparacao` da `placa_normalizada`, spec 003). Ordem: `decidida_em` decrescente, `id` decrescente.

### 5.2 Leitura com interpretações

A `LeituraPlaca` da spec 009 §5.2, mais:

| Campo | Tipo | Conteúdo |
|---|---|---|
| `formato` | texto | `ANTIGO` ou `MERCOSUL` (spec 003); `null` sem placa selecionada. |
| `correcoes` | lista | `{ "posicao": 1..7, "lido": "O", "corrigido": "0" }` (spec 003); vazia sem correção ou sem placa. |
| `origem` | texto | Nome da origem da imagem (spec 005 `ImagemCapturada.origem`). |
| `leituras` | lista | Uma por ROI, na ordem do pipeline (spec 005 §6.2): `{ "roi": { "x", "y", "largura", "altura" }, "textos": [{ "texto", "confianca" }] }`. Traz **todos** os textos, inclusive os rejeitados (RF-022). Vazia sem ROI. |

As coordenadas da ROI são pixels da imagem salva, que é a imagem original, sem redimensionar. Assim a tela desenha a ROI sobre a imagem sem conversão.

### 5.3 Imagem de decisão

| Campo | Tipo | Conteúdo |
|---|---|---|
| `id` | inteiro | — |
| `origem` | texto | — |
| `capturada_em` | data e hora | — |
| `roi` | objeto | `{ "x", "y", "largura", "altura" }`, ou `null` (spec 014). |
| `excluida` | booleano | Os bytes foram excluídos (§6.2). |
| `excluida_por`, `excluida_por_nome`, `excluida_em`, `motivo_exclusao` | — | Preenchidos só quando `excluida`. |

### 5.4 Estado dos dispositivos

```json
{ "gerado_em": "...", "intervalo_imagem_ms": 2000, "dispositivos": {} }
```

- `dispositivos`: o `EstadoDispositivos` da spec 009 §5.4, com o modo de cada dispositivo (RF-023).
- `intervalo_imagem_ms`: de `PESAGEM_TEMPO_REAL_INTERVALO_IMAGEM_MS` (§6.3). O número acima é só um exemplo.
- A atualização vem pelos eventos da spec 009 §6.1, com a mesma regra de tela desatualizada (§6.2 da spec 009).

### 5.5 Cenários dos simuladores

```json
{
  "balanca": { "cenario": "ESTAVEL", "peso_kg": "15000.000", "amplitude_kg": null },
  "cancelas": [
    { "cancela": "ENTRADA", "cenario": "CONFIRMADO" },
    { "cancela": "SAIDA", "cenario": "CONFIRMADO" }
  ],
  "posicao": { "cenario": "AUSENTE" },
  "chegadas_na_fila": 0
}
```

| Campo | Valores |
|---|---|
| `balanca.cenario` | `ESTAVEL`, `INSTAVEL`, `SEM_RESPOSTA`, `SEM_RESPOSTA_NA_PRIMEIRA`, `QUADRO_CORROMPIDO`, `DESCONECTADA` (spec 004 §6.3). |
| `balanca.peso_kg` | Obrigatório em `ESTAVEL`, `INSTAVEL` e `SEM_RESPOSTA_NA_PRIMEIRA`; `null` nos demais. Qualquer decimal finito, inclusive negativo ou com muitas casas: o simulador não valida o peso, quem rejeita é a spec 002. |
| `balanca.amplitude_kg` | Obrigatório e maior que 0 só em `INSTAVEL`; `null` nos demais. |
| `cancelas[].cenario` | `CONFIRMADO`, `CONFIRMADO_NA_SEGUNDA`, `NAO_MOVE`, `FALHA`, `SENSOR_SEM_RESPOSTA` (spec 004 §6.3). |
| `posicao.cenario` | `CONFIRMADA`, `AUSENTE`, `INCONCLUSIVA` (spec 015). |
| `chegadas_na_fila` | Chegadas ainda não analisadas. |

## 6. Regras

### 6.1 Leituras e privacidade

- Só existem leituras registradas pela orquestração: uma nova decisão igual à anterior não gera registro (spec 015).
- As leituras trazem a placa e são consulta de quem tem `CONSULTAR_OPERACAO`. Os textos e as ROIs ficam na rota do item, com `CONSULTAR_IMAGENS_DECISAO`, porque são a interpretação da imagem (ADR-0004 §4.3).

### 6.2 Imagens das decisões (RN-022)

- **Quais:** leitura com ao menos um candidato, posição confirmada que fez a operação avançar e confirmações manuais que substituem a câmera (spec 015). A referência é o `imagem_id` da `LeituraPlaca` e dos eventos da spec 010.
- **Excluir:** corpo `{ "motivo": "..." }`, obrigatório, não vazio, até 200 caracteres. Apaga **só os bytes**; os dados da imagem, a decisão e a operação continuam. Grava quem excluiu (usuário da sessão), quando e o motivo (RN-022, RNF-010).
- **Imagem excluída:**
  - `GET /api/imagens-decisao/{imagem_id}` responde `200` com `excluida: true` e os dados da exclusão;
  - `GET .../conteudo` responde `409` com `[{ "campo": "imagem_id", "codigo": "IMAGEM_EXCLUIDA" }]`;
  - excluir de novo responde o mesmo `409`.
- A tela mostra "imagem excluída", com quem, quando e o motivo, no lugar da imagem.
- A resposta dos bytes vai com `Cache-Control: no-store`, para a imagem não ficar no cache do navegador depois de excluída (RNF-013).

### 6.3 Imagem atual das câmeras (ADR-0005 §4.8)

- Devolve a imagem mais recente que a orquestração analisou naquela fonte (RF-034). Não é salva.
- `Last-Modified` traz o instante da captura; `Cache-Control: no-store`.
- Sem imagem ainda, ou com a fonte em falha: `409` com `[{ "campo": "camera", "codigo": "SEM_IMAGEM" }]`. A tela mostra o estado da fonte pela `identificacao` ou pela `posicao` da spec 009 §5.4.
- **Atualização:** o frontend pede a imagem a cada `intervalo_imagem_ms`, só enquanto a tela de diagnóstico está aberta e visível, e para quando a tela está desatualizada (spec 009 §6.2).
- `PESAGEM_TEMPO_REAL_INTERVALO_IMAGEM_MS` é obrigatória e sem valor padrão; sem ela, o backend não inicia.

### 6.4 Controle dos simuladores (RNF-003, RNF-007; decisão delegada do Maestro)

- **Por quê:** o artigo valida o protótipo em ambiente controlado, com simulação da balança e das cancelas **[ARTIGO §2]**. Para demonstrar e testar os cenários do artigo (placa com e sem agendamento, falha de reconhecimento, falha da balança, cancela) sem editar arquivos nem reiniciar, o administrador troca o cenário pela tela.
- **Nunca existe com hardware real.** As rotas da §4.2 só são registradas na partida quando **todos** os dispositivos estão em `SIMULADO` (spec 015 §6.9). Com qualquer um em `REAL`, nenhuma delas existe e todas respondem `404 NAO_ENCONTRADO`, mesmo sem sessão. Motivo: com um único equipamento real, uma chegada simulada poderia abrir uma cancela de verdade. O modo vem só da configuração e não muda em execução (spec 004 §5.3).
- **Efeito:** o novo cenário vale a partir da próxima leitura ou comando (spec 004 CA-006). Trocar o cenário não aciona nada: só muda o que o simulador devolve.
- **Corpos da troca de cenário:** o mesmo objeto do item na §5.5, com todos os campos, e `null` onde não se aplica:
  - `POST /api/simuladores/balanca`: `{ "cenario": "INSTAVEL", "peso_kg": "15000.000", "amplitude_kg": "5.000" }`;
  - `POST /api/simuladores/cancelas/{cancela}`: `{ "cenario": "NAO_MOVE" }`; a cancela vem só da rota;
  - `POST /api/simuladores/posicao`: `{ "cenario": "CONFIRMADA" }`.
- **Chegada:** corpo `{ "textos": [{ "texto": "ABC1D23", "confianca": "0.950" }] }`. Lista vazia simula uma imagem sem texto (`SEM_CANDIDATO`). `confianca` de 0 a 1. Cada pedido é uma chegada, que entra na fila e vira uma `LeituraPlaca` sintética no próximo ciclo de análise, pela mesma seleção e decisão das placas reais. A resposta `202` traz os cenários da §5.5; a decisão chega pelo evento `leitura_placa` da spec 009. A imagem é sintética, sem dado pessoal.
- **Sem atalho:** nenhuma rota de simulador cria operação, autoriza, aciona cancela ou registra peso. Tudo passa pelo fluxo normal (specs 006 e 015).
- **Validação:** cenário desconhecido, `peso_kg` ou `amplitude_kg` ausentes onde são obrigatórios ou presentes onde não são, decimal inválido ou `confianca` fora de `[0, 1]`: `422 CAMPO_INVALIDO`, e nada muda.

### 6.5 Falhas

| Situação | Resposta |
|---|---|
| `leitura_placa_id` ou `imagem_id` inexistente | `404 NAO_ENCONTRADO`. |
| `camera` ou `cancela` fora dos valores | `404 NAO_ENCONTRADO`. |
| Imagem excluída | §6.2. |
| Fonte sem imagem | §6.3. |
| Banco indisponível | `500 ERRO_INTERNO`. Na exclusão, nada é apagado. |
| Tempo de resposta | Sem número definido; não há dado para isso. |

## 7. Dados pessoais

- Imagens e placas são dados pessoais (RNF-013). As imagens não vão para logs nem para o canal de eventos (ADR-0005 §4.6).
- O `motivo` da exclusão e os textos lidos não vão para os logs de acesso. A query string também não (spec 007 §3.4).

## 8. Critérios de aceitação

Verificáveis no backend (testes de API com os simuladores) e no frontend (respostas simuladas com estes tipos, S-6).

| CA | Critério |
|---|---|
| CA-001 | As rotas da §4.1 existem com as permissões indicadas; sem sessão `401`, sem permissão `403`. |
| CA-002 | `AUDITOR` vê leituras, interpretações e imagens das decisões, e recebe `403` na imagem atual e na exclusão; `OPERADOR` recebe `403` na exclusão e nos simuladores. |
| CA-003 | A lista de leituras traz as não autorizadas, com o motivo, e filtra por `decisao`, `motivo` e `placa` pela `chave_comparacao`. |
| CA-004 | O item da leitura traz todas as ROIs e todos os textos, inclusive os rejeitados (como `BRASIL`), com a confiança em texto de 3 casas. |
| CA-005 | Uma leitura com correção de OCR traz a correção em `correcoes`, com posição, lido e corrigido. |
| CA-006 | O conteúdo da imagem vem como `image/jpeg` com `Cache-Control: no-store`, e a ROI cai dentro das dimensões da imagem. |
| CA-007 | Excluir sem motivo dá `422`; com motivo, os dados da imagem ficam com `excluida: true`, quem, quando e o motivo, e a leitura e a operação não mudam. |
| CA-008 | Depois de excluída, o conteúdo dá `409 IMAGEM_EXCLUIDA`, e excluir de novo também. |
| CA-009 | A imagem atual vem com `Last-Modified`; sem imagem, `409 SEM_IMAGEM`; nenhuma imagem atual é gravada no banco. |
| CA-010 | Frontend: a imagem atual só é pedida com a tela aberta e visível, no intervalo de `intervalo_imagem_ms`, e para com a tela desatualizada. |
| CA-011 | `GET /api/dispositivos` traz o modo de cada dispositivo e o mesmo `EstadoDispositivos` da spec 009. |
| CA-012 | Com todos os dispositivos em `SIMULADO`, as rotas da §4.2 existem e só o `ADMINISTRADOR` as usa. |
| CA-013 | Com qualquer dispositivo em `REAL`, todas as rotas da §4.2 dão `404`, com ou sem sessão. |
| CA-014 | Balança em `SEM_RESPOSTA` pelo simulador leva ao evento `balanca` com `FALHA` (spec 009 CA-024); em `ESTAVEL` com `peso_kg`, o peso é aceito pela spec 002. |
| CA-015 | Cancela de entrada em `SENSOR_SEM_RESPOSTA` leva ao `CANCELA_SEM_CONFIRMACAO` da spec 009 CA-025. |
| CA-016 | Uma chegada com `ABC1D23` de confiança acima do limiar, para um veículo com agendamento válido, gera `leitura_placa` `AUTORIZADA` e uma pesagem; com confiança abaixo, `CONFIANCA_BAIXA`; com lista vazia, `SEM_CANDIDATO`. |
| CA-017 | Trocar cenário não envia comando a nenhuma cancela (verificado pela lista de comandos do simulador, spec 004 §6.3). |
| CA-018 | Cenário inválido, `amplitude_kg` em `ESTAVEL` ou `confianca` `1.5` dá `422`, e os cenários não mudam. |

## 9. Impacto

- **Backend (BE-705):** rotas e conversão de erros; depende da orquestração (BE-602), da persistência (BE-503) e do login (BE-706).
- **Frontend (FE-305, FE-306):** diagnóstico, estado dos dispositivos e controle dos simuladores usam só este contrato e o canal da spec 009.
- **Orquestração (spec 015):** guarda a imagem mais recente de cada fonte; salva a imagem original, em JPEG e sem redimensionar; o `Simuladores` atende a §6.4.
- **Esquema (spec 014):** `leitura_placa` com `formato`, `correcoes` e `leituras`, e `imagem_decisao` com os campos de exclusão, já previstos. Índice para a ordem da §5.1 (`decidida_em`, `id`).
- **ADR-0004:** nova permissão `CONTROLAR_SIMULADORES`, só do `ADMINISTRADOR`.
- **Integração (INT-001):** `PESAGEM_TEMPO_REAL_INTERVALO_IMAGEM_MS` no `.env.exemplo`; a demonstração roda com todos os dispositivos em `SIMULADO` (RNF-007).
- **Segurança operacional:** o controle dos simuladores não existe com nenhum equipamento real e não abre atalho no fluxo. Nada foi validado com hardware real.
- **Reversibilidade:** alta, sem código ainda.

## 10. Perguntas em aberto

| ID | Pergunta | Até a resposta |
|---|---|---|
| P-1 | Adequação à LGPD das imagens e das placas guardadas (Q-08). | Vale a RN-022: guardadas até a exclusão pelo administrador. |
| P-2 | Quais câmeras físicas existem e como se chamam (Q-06)? | Duas fontes, `identificacao` e `posicao`. |
