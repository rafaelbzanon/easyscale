# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + React Router, Tailwind CSS v4, TypeScript estrito (ADR-0007). Testes e lint: ADR-0008. Build estático, sem renderização no servidor.

## Users

- **Operador** (`OPERADOR`): na sala da balança, em monitor de mesa a cerca de 60 cm, com luz ambiente comum. Acompanha a operação de relance enquanto atende o motorista e o telefone. Cria agendamentos, pede nova tentativa e libera caminhão cancelado.
- **Administrador** (`ADMINISTRADOR`): mesmas telas, mais cadastros, usuários, faixas e as intervenções manuais (confirmar posição, aceitar peso final, cancelar, liberar entrada).
- **Auditor** (`AUDITOR`): só consulta operação, histórico e imagens das decisões.
- **Motorista**: no totem do pátio, tela de toque sem teclado físico. O leitor do código da nota age como teclado. Usa a tela poucas vezes, às vezes com pressa, luva ou celular na mão.

## Product Purpose

EasyScale automatiza a pesagem rodoviária depois do agendamento manual: identifica o caminhão pela placa (LPR), confere o agendamento, comanda as cancelas, lê a balança e calcula o peso líquido, com histórico para auditoria. É o protótipo de um TCC (IFRS Veranópolis), validado com simuladores.

Sucesso na interface: o operador sabe, num relance, o que está acontecendo na balança, o que falhou e o que pode fazer, sem nunca agir sobre uma tela velha.

## Positioning

O sistema decide sozinho só quando tem certeza, e mostra a evidência quando não tem: imagem, ROI, texto lido, confiança e motivo da recusa. A tela existe para tornar a recusa segura legível, não para esconder a automação.

## Operating Context

- Fluxo: agendamento manual → leitura da placa → autorização → pesagem inicial → carga/descarga → pesagem final → peso líquido (`AMBIENTE.md` §2).
- Tempo real por SSE com aviso de tela desatualizada e bloqueio de ações (ADR-0005, spec 009 §6.2).
- Equipamentos podem estar em modo `SIMULADO` ou `REAL`, por dispositivo (spec 009 §5.4).
- Rede local do pátio; HTTPS na demonstração (ADR-0004).

## Capabilities and Constraints

- O frontend nunca decide segurança: só apresenta e pede ações (RNF-014). O operador não abre cancela diretamente nem digita peso (spec 009 §3).
- Campos da API em `snake_case`, sem conversão (`CONVENCOES.md` §8). Textos de interface em português com acentos.
- Sessão por cookie `HttpOnly`; nenhuma credencial em JavaScript (ADR-0004).
- Placas e dados de motorista são dados pessoais: mostrar só o necessário; CPF mascarado fora do administrador (RNF-013, spec 007 §4.2).
- O totem nunca mostra dados do cadastro e não revela se placa ou CPF existem (RN-021).
- Pendente: tipo e resolução das câmeras (Q-06); tamanho de tela do totem.

## Brand Commitments

- Nome exibido: **EasyScale** (título do `README.md`). Sem logotipo definido.
- Voz: frases curtas e diretas, em português, sem jargão técnico para o motorista.

## Evidence on Hand

- Nenhuma imagem real de câmera ou placa no repositório: o acervo fica fora (Q-09). Telas usam dados simulados tipados pelos contratos (S-6), marcados como simulados quando visíveis.
- Sem logotipo, fotos ou depoimentos. Não inventar.

## Product Principles

1. Falha é estado de primeira classe: cada falha tem nome, cor e lugar fixos, e nunca se parece com sucesso.
2. Em dúvida, a tela diz "desconhecido", nunca um valor provável.
3. O modo `REAL`/`SIMULADO` e a frescura dos dados estão sempre à vista.
4. Toda ação pede motivo e mostra o que ela faz antes de ser enviada; o resultado físico chega pelos eventos, não pelo clique.
5. Densidade para quem opera o dia todo; simplicidade extrema no totem.

## Accessibility & Inclusion

- Estados nunca só por cor: sempre texto e forma juntos (daltonismo, monitores ruins).
- Contraste WCAG AA no mínimo; texto de estado legível a 60 cm de relance.
- Totem: alvos de toque grandes, teclado na tela, uso com uma mão.
