# ADR-0005 — Atualização em tempo real

- **Trilha:** Contrato
- **Status:** Aceita
- **Data:** 2026-11-04
- **Decisão relacionada:** D-06 — `AMBIENTE.md` §4, §10.1, §15
- **Tarefa:** CT-002 (`specs/tarefas-iniciais.md`)
- **Requisitos:** RF-021, RF-022, RF-023, RF-034, RNF-011, RNF-013, RNF-014
- **Aprovação:** autor, 2026-11-04 (respostas às perguntas da §6)

---

## 1. Contexto

- A tela operacional mostra em tempo real a placa, o peso, a etapa e os comandos de cancela (RF-021). O diagnóstico mostra imagens, ROIs e interpretações (RF-022), e a interface mostra o estado dos dispositivos (RF-023).
- O `AMBIENTE.md` §10.1 deixa em aberto se as imagens são "ao vivo ou quase ao vivo". Nenhum requisito traz um número de latência.
- Fatos que já valem:
  - comandos são pedidos por HTTP, e quem decide é o backend (RNF-014);
  - um único processo de backend (ADR-0002) com sessão por cookie (ADR-0004);
  - cada transição aumenta a `versao` da operação (spec 006);
  - imagens e placas são dados pessoais, e o acesso às imagens depende de permissão própria (ADR-0004, RNF-013);
  - o tipo de câmera ainda não foi definido (Q-06).
- O risco principal não é atraso, e sim o operador agir olhando uma **tela desatualizada sem perceber**.

## 2. Critérios

1. A tela mostra claramente quando os dados estão desatualizados.
2. Uma ação baseada em dado velho não tem efeito.
3. Funciona com o cookie de sessão e sem depender do tipo de câmera.
4. Simplicidade nos dois lados, sem dependência nova desnecessária.
5. Não sobrecarrega o backend, que também roda o OCR e os dispositivos (RNF-011).

## 3. Opções

### 3.1 Eventos (situação, peso, dispositivos)

| Opção | Backend | Frontend | Contras |
|---|---|---|---|
| **A. SSE** | Uma resposta HTTP que fica aberta e envia eventos; sem protocolo extra. | `EventSource`, nativo do navegador, reconecta sozinho e envia o cookie. | Só do servidor para o navegador, o que basta aqui, porque os comandos usam HTTP. Exige desligar o buffer no proxy (INT-001). |
| **B. WebSocket** | Conexão de duas vias, com autenticação e origem a conferir à mão. | Reconexão e reenvio precisam ser escritos. | Duas vias que o sistema não usa; abriria um segundo caminho para comandos, fora das rotas com permissão. |
| **C. Polling** | Só rotas comuns. É o mais simples. | Consulta periódica. | Cada intervalo é um atraso a mais, ou mais carga se for curto; difícil de acompanhar o peso. |

### 3.2 Imagens

| Opção | Prós | Contras |
|---|---|---|
| **D. Imagem sob demanda** (o navegador busca a imagem por `GET`) | Simples; usa as rotas e as permissões normais; a imagem da decisão é a mesma mostrada; pouca carga. | Não é vídeo fluido. |
| **E. MJPEG** | Quase vídeo, com pouco código. | Consome rede e CPU por visualizador, competindo com o OCR; mantém uma conexão aberta por câmera. |
| **F. Vídeo por WebRTC ou HLS** | Vídeo de verdade. | Requer um serviço de mídia e depende da câmera (Q-06); desproporcional ao protótipo. |

## 4. Decisão

**SSE para eventos (A) e imagens sob demanda (D).**

1. **Só leitura:** o canal de eventos não aceita comandos. Toda ação continua nas rotas HTTP, com permissão.
2. **Fonte da verdade:** ao abrir a tela e a cada reconexão, o frontend busca o estado atual por `GET`. O evento só atualiza a tela: se um evento se perder, o próximo `GET` corrige.
3. **Ordem:** os eventos de operação trazem `versao`, e o frontend ignora versão menor ou igual à que já tem.
4. **Aviso de tela desatualizada:** o servidor envia um sinal periódico (`heartbeat`). Sem sinal dentro do limite, ou com a conexão caída, a tela mostra um aviso claro e bloqueia as ações. Os dois tempos vêm de configuração, e os valores serão definidos no contrato.
5. **Ação com dado velho:** toda ação manual envia a `versao` que o usuário estava vendo. Se ela não for a atual, o backend recusa com `409`, sem efeito.
6. **Permissões:** a conexão exige sessão e `CONSULTAR_OPERACAO`. Se a sessão acabar, o servidor encerra a conexão. Os eventos **nunca** levam imagem, só a referência a ela. A imagem de uma decisão exige `CONSULTAR_IMAGENS_DECISAO`, e a imagem atual do diagnóstico exige `CONSULTAR_IMAGENS_TEMPO_REAL`.
7. **Peso em tempo real:** o peso lido é enviado com intervalo mínimo configurado, para não gerar um evento por quadro da balança. É marcado como leitura, e não como peso aceito.
8. **Imagens:**
   - a imagem de uma decisão é buscada quando o evento a indica;
   - no diagnóstico, a imagem atual é atualizada periodicamente, só enquanto a tela está aberta, com intervalo configurado.
9. **Distribuição:** na memória do processo, porque há um só processo (ADR-0002). Se a D-05 separar processos, esta parte precisa ser revista.
10. **Nenhuma decisão de segurança depende desse canal.** Com todos os navegadores desconectados, a operação segue pelo backend.

### 4.1 Análise em tempo real (RF-034)

Este ADR trata do que chega à **tela**. A **análise** das imagens é outra coisa, acontece no backend e não depende de haver alguém olhando:

1. O backend analisa as imagens das câmeras em tempo real durante a operação, com o navegador aberto ou não.
2. A análise usa sempre a imagem **mais recente** e descarta as anteriores, sem formar fila: uma decisão nunca é tomada sobre uma imagem antiga. Imagem mais velha que o limite configurado conta como incerta (`POSICAO_INCONCLUSIVA`, spec 006).
3. A frequência e o limite de idade vêm de configuração. A forma de executar fica na D-05 (BE-601), e o desempenho real precisa ser medido.

## 5. Consequências

- **Dependências:** nenhuma nova nos dois lados. A forma de implementar o SSE no FastAPI será confirmada na BE-703; **não verificado** ainda.
- **Contrato (CT-103, CT-105):** define a rota de eventos, os tipos de evento, os dois tempos do item 4, o `409` e as rotas de imagem.
- **Frontend (FE-303, FE-305):** indicador de conexão, bloqueio de ações e ressincronização ao reconectar.
- **Integração (INT-001):** desligar o buffer do proxy na rota de eventos. Com HTTPS, o HTTP/2 evita o limite de conexões por domínio do HTTP/1.1, que poderia travar várias abas abertas.
- **Autoatendimento (FE-307):** não usa o canal de eventos.
- **Orquestração (BE-601):** captura e analisa as imagens continuamente (§4.1), o que aumenta o risco de disputa de CPU com a API (R-04).
- **Limites conhecidos:** sem vídeo fluido na tela; a latência real ainda não foi medida e só poderá ser na BE-703 ou na FE-303.
- **Reversibilidade:** alta nos eventos, porque trocar SSE por WebSocket não muda os tipos. Vídeo pode ser somado depois, sem mexer nos eventos.

## 6. Perguntas para aprovação

| ID | Pergunta | Recomendação |
|---|---|---|
| P-A | Imagens atualizadas periodicamente bastam, ou é preciso vídeo fluido? | **Imagens periódicas.** O RF-022 pede para inspecionar imagens e ROIs, e o vídeo competiria com o OCR. Se precisar de vídeo, escolha a opção E ou F. |
| P-B | Bloquear as ações na tela desatualizada? | **Sim,** até reconectar. Com o bloqueio, uma queda de rede impede ações manuais naquela tela, mas a operação continua. |

**Respostas do autor (2026-11-04):**

- **Opção:** SSE para eventos e imagens sob demanda.
- **P-A:** imagens salvas para registro, sim; mas o sistema deve analisar as imagens em tempo real. Daí a §4.1 e o RF-034. A tela segue com imagens atualizadas periodicamente. Só as imagens das decisões são salvas (Q-08).
- **P-B:** sim.
