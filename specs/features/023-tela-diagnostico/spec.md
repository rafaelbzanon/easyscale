# Spec 023 — Tela de diagnóstico da visão computacional

- **Trilha:** Frontend
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-305 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-022, RF-034, RN-022, RNF-003, RNF-013
- **Contratos:** spec 011 (leituras, imagens, câmeras, simuladores); spec 009 §6.1 e §6.2 (canal e tela desatualizada). Casca: specs 016, 017 e 022.
- **Decisões:** ADR-0004 §4.3 (permissões de imagem), ADR-0005 §4 itens 6 e 8 (imagens sob demanda)

## 1. Objetivo

Inspecionar o que a visão computacional fez: a imagem atual das câmeras, o histórico de reconhecimentos e, de cada um, a imagem salva com as ROIs e todos os textos lidos (RF-022). No modo simulado, trocar os cenários dos simuladores para demonstrar os casos do artigo (RNF-003).

## 2. Fora de escopo

- Estado detalhado dos dispositivos e liberação manual de entrada: FE-306.
- Filtros por data, placa e pesagem na lista: só o filtro por decisão, para achar as leituras não autorizadas.

## 3. Comportamento

Rota `/diagnostico`, item "Diagnóstico" no menu (`CONSULTAR_OPERACAO`). Cada seção aparece só se a sessão tiver a permissão dela; o backend decide (`403`).

### 3.1 Câmeras (`CONSULTAR_IMAGENS_TEMPO_REAL`)

- Uma imagem por fonte: identificação e posição (`GET /api/cameras/{camera}/imagem-atual`).
- O intervalo vem de `intervalo_imagem_ms` em `GET /api/dispositivos`. A tela pede a imagem nesse intervalo só enquanto está visível e atualizada (011 §6.3). Desatualizada, para de pedir e mostra o aviso da spec 022.
- A tela usa o canal da spec 009 só para saber se está atualizada e mostrar o resultado da fonte (`identificacao.resultado`, `posicao.resultado`).
- `409 SEM_IMAGEM`: no lugar da imagem, "Sem imagem desta câmera", com o resultado da fonte.

### 3.2 Reconhecimentos (`CONSULTAR_OPERACAO`)

- `GET /api/leituras-placa`, paginada, mais recente primeiro. Filtro "Só não autorizadas" (`decisao=NAO_AUTORIZADA`).
- Colunas: hora, placa normalizada (ou "Sem placa"), decisão, motivo e confiança.
- Com `CONSULTAR_IMAGENS_DECISAO`, cada linha tem "Ver detalhes".

### 3.3 Detalhe da leitura (`CONSULTAR_IMAGENS_DECISAO`)

- `GET /api/leituras-placa/{id}`: texto bruto, placa normalizada, formato, correções de OCR (posição, lido → corrigido), confiança, decisão e motivo, origem da imagem.
- Cada ROI com **todos** os textos lidos e a confiança de cada um, inclusive os rejeitados (RF-022).
- Com `imagem_id`: `GET /api/imagens-decisao/{id}` e o conteúdo da imagem. As ROIs são desenhadas sobre a imagem, numeradas na mesma ordem da lista, nas coordenadas em pixels da imagem (011 §5.2).
- Imagem excluída: no lugar da imagem, "Imagem excluída por {nome} em {data}. Motivo: {motivo}." (011 §6.2).
- Com `EXCLUIR_IMAGENS_DECISAO`: "Excluir imagem", com motivo obrigatório (até 200 caracteres) e confirmação. Depois de excluída, recarrega os dados da imagem.

### 3.4 Simuladores (`CONTROLAR_SIMULADORES`)

- `GET /api/simuladores`. A seção só aparece se a rota responder `200`. Com `404` (algum dispositivo em `REAL`, 011 §6.4) ou `403`, a seção não aparece.
- Balança: cenário; `peso_kg` nos cenários que o exigem (`ESTAVEL`, `INSTAVEL`, `SEM_RESPOSTA_NA_PRIMEIRA`); `amplitude_kg` só em `INSTAVEL`. Os campos que não se aplicam vão como `null`.
- Cancela de entrada e de saída: cenário. Posição: cenário.
- Chegada: placa e confiança (de 0 a 1); sem placa, simula imagem sem texto. Mostra as chegadas na fila.
- Toda troca mostra os cenários devolvidos pelo backend. A tela avisa: "Trocar o cenário não aciona nada; vale a partir da próxima leitura ou comando."

## 4. Falhas

| Situação | Tela |
|---|---|
| `409 IMAGEM_EXCLUIDA` no conteúdo | O aviso de imagem excluída. |
| `404` em uma rota de simulador depois de aberta a seção | "Simuladores indisponíveis." e a seção some. |
| `422` em uma troca de cenário | A mensagem do backend; o cenário mostrado continua o que o backend devolveu antes. |
| Falha ao carregar a imagem atual | Mantém o aviso de falha no lugar da imagem; não mostra uma imagem velha como atual. |
| Outros erros | A mensagem comum (spec 016 §7). |

## 5. Critérios de aceitação

| CA | Critério |
|---|---|
| CA-001 | A seção de câmeras aparece só com `CONSULTAR_IMAGENS_TEMPO_REAL`; a de detalhe só com `CONSULTAR_IMAGENS_DECISAO`; a exclusão só com `EXCLUIR_IMAGENS_DECISAO`. |
| CA-002 | A imagem atual é pedida no intervalo configurado e deixa de ser pedida com a tela desatualizada. |
| CA-003 | `409 SEM_IMAGEM` mostra "Sem imagem desta câmera". |
| CA-004 | A lista mostra as leituras na ordem do backend, e o filtro envia `decisao=NAO_AUTORIZADA`. |
| CA-005 | O detalhe mostra todas as ROIs com todos os textos e as correções. |
| CA-006 | As ROIs são desenhadas sobre a imagem nas coordenadas do contrato, numeradas na ordem da lista. |
| CA-007 | Imagem excluída mostra quem, quando e o motivo, no lugar da imagem. |
| CA-008 | Excluir envia `{ motivo }` só depois da confirmação. |
| CA-009 | Simuladores: `404` esconde a seção; com `200`, a troca de cenário da balança envia `peso_kg` e `amplitude_kg` como `null` quando não se aplicam. |
| CA-010 | A chegada simulada envia `{ textos: [{ texto, confianca }] }`, ou `{ textos: [] }` sem placa. |

## 6. Perguntas em aberto

Nenhuma nova.
