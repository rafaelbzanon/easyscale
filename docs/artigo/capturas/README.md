# Capturas de tela para o artigo

Tudo roda em modo SIMULADO (nenhum equipamento físico), com dados fictícios, em 2026-11-07. Nomes, placas, CPFs e CNPJs são inventados (os documentos têm dígito verificador válido). Telas de computador: 1440×900 com fator 2. Totem: 1080 px de largura, retrato.
A imagem da câmera é sintética, gerada pelo simulador (cena 640×360 com uma placa desenhada); não é foto de caminhão real.

| Nº | Arquivo | Caso de uso | O que a figura mostra | Requisitos |
|---|---|---|---|---|
| 01 | `01-login.png` | Entrar no sistema | Tela de login, a única aberta sem sessão, além do totem. | RF-031 (ADR-0004) |
| 02 | `02-cadastros-veiculos.png` | Cadastros | Lista de veículos com placa antiga e Mercosul, tipo, transportadora, motorista padrão e pesos. | RF-001, RF-003, RF-026 |
| 03 | `03-agendamento-manual.png` | Agendamento manual | Formulário de novo agendamento com a primeira faixa com vaga já sugerida, para o usuário conferir e confirmar. | RF-004, RF-029, RN-001 |
| 04 | `04-agendamentos-do-dia.png` | Consulta de agendamentos | Agendamentos do dia, com faixa, status e origem (usuário ou autoatendimento) e as ações do administrador. | RF-005, RF-033, RN-013 |
| 05 | `05-autoatendimento-totem.png` | Autoatendimento do motorista | Passo da placa no totem, com o teclado da tela. | RF-033, RN-021 |
| 06 | `06-autoatendimento-conferencia.png` | Autoatendimento do motorista | Conferência dos dados antes de confirmar, com o CPF mascarado. | RF-033, RN-021, RNF-013 |
| 07 | `07-operacao-entrada-autorizada.png` | Chegada e autorização | Placa reconhecida e autorizada, cancela de entrada aberta com o comando confirmado e a pesagem na fila. | RF-006 a RF-010, RF-021, RN-002 |
| 08 | `08-operacao-pesagem-inicial.png` | Pesagem inicial | Caminhão posicionado, peso de 15.000 kg lido e aceito, peso inicial registrado e cancela de saída aberta. | RF-013, RF-014, RF-027, RN-004 |
| 09 | `09-operacao-peso-liquido.png` | Pesagem final | Peso final aceito na volta e peso líquido calculado (45.000 − 15.000 = 30.000 kg). | RF-016, RF-017, RN-006, RN-012 |
| 10 | `10-historico-eventos.png` | Histórico | Eventos de uma pesagem finalizada: transições, comandos de cancela, peso aceito e líquido (segunda página da lista). | RF-018, RF-019, RF-020 |
| 11 | `11-nao-autorizada.png` | Entrada recusada | Placa cadastrada, mas sem agendamento para hoje: "Não autorizada" com o motivo, e nenhuma pesagem criada. | RF-009, RN-003 |
| 12 | `12-diagnostico-reconhecimento.png` | Diagnóstico da placa | Detalhe de um reconhecimento: imagem sintética da câmera com a ROI sobre a placa, texto lido, placa normalizada, formato, confiança e decisão. | RF-022, RF-008, RN-017 |
| 13 | `13-falha-balanca.png` | Falha da balança | Balança sem resposta: falha sinalizada, nenhuma leitura e nenhum peso aceito. | RN-005, RNF-005, RNF-009 |
| 14 | `14-intervencao-cancela.png` | Intervenção manual | Cancela sem confirmação (estado desconhecido), pesagem aguardando intervenção e o pedido de "tentar novamente" com motivo. | RF-024, RN-007, RN-011 |
| 15 | `15-liberacao-manual-entrada.png` | Liberação manual | Administrador libera a entrada após leitura de confiança baixa, escolhendo o agendamento e informando o motivo. | RF-024, RN-016, RN-003 |
| 16 | `16-tela-desatualizada.png` | Tempo real | Servidor parado: aviso "Tela desatualizada", faixa zebrada, ações bloqueadas e modo desconhecido. | RF-021, RNF-014 |
| 17 | `17-dispositivos.png` | Estado dos dispositivos | Balança, cancelas, posição e identificação com o estado, o último comando e o modo SIMULADO. | RF-023, RNF-003 |
| 18 | `18-usuarios-perfis.png` | Usuários e perfis | Lista com os três perfis: administrador, operador e auditor. | RF-031, RF-032 |
| 19 | `19-controle-acesso-operador.png` | Controle de acesso | Operador sem o item "Usuários" no menu e com a recusa "Você não tem permissão" ao abrir a tela. | RF-031, RNF-014 |

## Notas

- A figura 16 mostra "modo desconhecido" no cabeçalho porque, sem o servidor, a tela não consegue confirmar o modo.
- A figura 08 mostra o peso inicial já registrado, com o caminhão ainda na balança. O instante exato da leitura dura menos de um segundo no simulador.
- Nas figuras 07 e 11, o peso grande da balança é a última leitura (com a idade ao lado), rotulada "não é peso aceito".
- A figura 10 mostra a segunda página dos eventos (32 no total), onde estão o peso final e o líquido.
