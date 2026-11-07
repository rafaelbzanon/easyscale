"""Orquestração da operação (spec 015, `orquestracao-operacao`).

Coordena domínio, LPR, dispositivos e persistência. Única camada que aciona
cancela e aceita peso; na dúvida, não autoriza, não aciona e não registra
(`AGENTS.md` §7, RNF-009).
"""
