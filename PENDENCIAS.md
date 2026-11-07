# PENDENCIAS.md — o que falta o autor decidir ou fazer

Atualizado em 2026-11-07, ao fim da sessão que concluiu o protótipo em modo simulado e preparou o transporte serial da balança (spec 029).

O sistema funciona de ponta a ponta com simuladores: 1002 testes no backend, 176 no frontend, 18 testes ponta a ponta e a validação dos casos de uso pelo navegador. Nada foi testado com balança, cancela ou câmera reais. Os detalhes de cada item estão na spec citada; a lista completa de perguntas também está em `specs/README.md` §4.

Ordem sugerida: 1 → 2 → 3 (antes de qualquer teste com equipamento) → o resto quando der.

---

## 1. Revisar o que foi aprovado por delegação

Nesta sessão você delegou as portas de aprovação. Tudo o que saiu assim está marcado "delegada" ou "revisão final pendente". Para cada item: ler, aprovar ou pedir mudança, e trocar o status.

| O quê | Onde |
|---|---|
| ADRs de banco (SQLAlchemy Core + Alembic), framework (React + Vite) e ferramentas do frontend | `docs/decisoes/ADR-0006` a `ADR-0008` |
| Permissão nova `CONTROLAR_SIMULADORES` | `ADR-0004` §4.3 |
| Contratos da API: operação, histórico, diagnóstico, autenticação, autoatendimento | specs 009 a 013 |
| Persistência, orquestração | specs 014 e 015 |
| Telas | specs 016 a 024 |
| Docker, compose, testes ponta a ponta | specs 025 a 028 |
| Dispositivos seriais (preparação, sem protocolo) | spec 029 |
| Mudanças de convenção (pastas, grupos de variáveis `OPERACAO` e `PESAGEM`, termos novos do glossário) | `CONVENCOES.md`, `specs/glossario.md` |

## 2. Decisões de comportamento operacional

Afetam o que acontece na balança. Em todas há um comportamento seguro valendo até você responder.

| ID | Pergunta | Hoje | Onde |
|---|---|---|---|
| Q-D | Ao cancelar uma pesagem com a cancela de entrada aberta ou desconhecida, o sistema deve fechar a entrada? | Nada fecha a entrada; a fila da balança para até a cancela voltar a `FECHADA`. O validador viu a fila travar assim no simulado | spec 015 §14 |
| Q-A | Na liberação de caminhão cancelado, se a câmera não confirmar a balança vazia, o administrador pode confirmar à mão? | Não pode; a liberação falha e pode ser repetida | spec 015 §14, spec 009 P-2 |
| Q-B | Como a câmera superior distingue "o caminhão desta operação"? | Como só cabe um caminhão na balança, o resultado vale para a operação que a ocupa | spec 015 §14 |
| 009 P-1 | A liberação manual de entrada deve ter limite de tempo desde a leitura da placa? | Só vale a leitura mais recente | spec 009 |
| 015 P-4, P-9 | Confirmar: a liberação manual substitui só falhas de identificação e "antes da faixa", e não confere a placa com o veículo do agendamento | Como descrito | spec 015 §13 |
| — | Confirmar: se a orquestração parar, o backend mostra os dispositivos como desconhecidos e encerra o processo; o compose o reinicia e a retomada segue a spec 006 §7.2 | Como descrito | spec 027 §4.1 |
| — | Confirmar: o ponto de controle único (balança, cancela de entrada e de saída) é criado pela migração `0004`, porque nenhuma tela cadastra equipamentos | Como descrito | spec 014, migração `0004` |

## 3. Para ligar equipamentos reais

O modo `REAL` não sobe hoje, de propósito. Para mudar isso:

| O que providenciar | Para quê | Onde |
|---|---|---|
| Marca e modelo do indicador da balança, o manual do protocolo e quadros reais capturados da serial | Escrever o protocolo do modelo (um arquivo) e o teste com os quadros | Q-01; `docs/equipamentos/README.md` (roteiro); spec 029 |
| Parâmetros seriais da balança: porta, taxa, paridade, bits de dados, bits de parada | Preencher as variáveis `PESAGEM_BALANCA_*` | spec 029 |
| Modelo do controlador das cancelas, os comandos de abrir e fechar e **como o sensor de status (cabo dedicado) chega ao computador** | Escrever a `CancelaSerial`, que ficou de fora por depender disso | Q-01; spec 029 P-1 |
| Ligar o fechamento da porta serial ao desligamento da aplicação | Hoje a porta é liberada pelo sistema operacional quando o processo termina; `fechar()` existe mas não é chamado | spec 029 |
| Reconstruir a imagem do backend | O `pyserial` entrou nas dependências e a imagem não foi refeita nesta sessão | spec 025 |
| Câmeras: quantas, tipo (rede ou USB), resolução, qual lê a placa, como se chamam | Escrever as fontes de câmera real | Q-06, Q-C |
| Critério de análise da câmera superior para dizer que o caminhão está em posição | Escrever a fonte de posição real | Q-17, Q-B |
| Máquina e sistema operacional da demonstração; se há GPU | Decidir se o backend roda em contêiner com a porta serial mapeada (fácil em Linux, limitado em Windows/macOS) | Q-07; `AMBIENTE.md` R-05 |
| Calibrar os valores de demonstração: limites de peso, leituras estáveis, variação, tempos-limite, limiar de confiança do OCR | O `.env.exemplo` tem valores só para demonstração | spec 027 P-1 |
| Acervo de imagens reais de placas com gabarito, e a autorização para usá-lo | Medir o OCR e fixar o limiar de confiança; definir idiomas e pasta dos modelos do EasyOCR | Q-09; spec 005; spec 025 P-2 |
| Teste assistido com o equipamento, registrado | Só ele valida o comportamento real (`AGENTS.md` §4.9) | — |

## 4. Dados pessoais e escopo

| ID | Pergunta | Onde |
|---|---|---|
| Q-08 | Adequação à LGPD de placas, dados de motorista e imagens guardadas | RN-022; spec 011 P-1 |
| Q-03 | O que são "documentos": a nota fiscal deve ser conferida? Comprovante de pesagem? Hoje só o código da nota é guardado na descarga, sem verificação | RF-033, RN-021 |
| 010 P-1 | No histórico, nome do motorista, transportadora e produto devem ser os do momento da pesagem? Hoje mostram o cadastro atual | spec 010 |
| 014 P-1 | O número de pesagem do banco legado precisa voltar? | spec 014 |

## 5. Regras de acesso e telas

| ID | Pergunta | Hoje | Onde |
|---|---|---|---|
| 012 P-3 | Tamanho mínimo e composição da senha | Só não pode ser vazia; o validador criou um usuário com senha "123" | spec 012 |
| 012 P-7 | Como recuperar o acesso se ninguém sabe a senha de um administrador ativo? | Não há caminho: o comando só cria administrador quando não existe nenhum ativo | spec 012 |
| 012 P-1, P-4 | Administrador muda nome e perfil de um usuário? Usuário troca a própria senha? | Não | spec 012 |
| — | CNPJ alfanumérico: confirmar a regra da IN RFB 2.229/2024 | Implementado por ela | spec 007 §5.1 |
| 013 P-1 | Agendamento do totem fica sem transportadora? | Fica sem | spec 013 |
| Q-F1, Q-F7 | Tamanho da tela do totem | Testado em 1080×1920 e 1920×1080 | specs 016, 020 |
| Q-F2 | O totem mostra o modo REAL/SIMULADO? | Não mostra | spec 016 |
| Q-F6, Q-F8 | Antecedência máxima no totem e tempo de inatividade; avisar quanto falta para desbloquear | 7 dias e 60 s; não avisa | spec 020 |
| Q-F4, Q-F9 | Datas e horas da tela no fuso do navegador, não no do pátio | Como descrito | specs 019, 021 |
| — | Com a balança em falha, a tela de operação ainda mostra o último peso lido em fonte grande, rotulado "não é peso aceito" | Como descrito | spec 022 |
| 025 P-1 | Criar uma rota de saúde na API, com checagem do banco | O compose usa `GET /api/sessoes/atual` aceitando 401 | specs 025, 027 |

## 6. Projeto e repositório

| O quê | Situação |
|---|---|
| Licença (D-12) | O `LICENSE` MIT existe, mas a decisão nunca foi registrada |
| Glossário | `specs/glossario.md` segue "Em revisão" desde a C-101 |
| Aceite da BE-102 (spec 001) | Nunca registrado |
| Commit pendente | Capturas do artigo (`docs/artigo/capturas/`), formatação do peso sem zeros à direita, imagem sintética da placa no simulador, preparação serial (spec 029) e este arquivo |
| `.maestri/` | Arquivos de coordenação dos agentes, fora do Git; decidir se entram no `.gitignore` ou são apagados |
| Limpeza local | Contêiner `loom-pesagem-db`, imagens `pesagem-*:teste` e o administrador de teste `admin` no volume `pesagem-dados-db` (`docker compose down -v` apaga) |
