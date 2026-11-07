import { useCallback, useEffect, useRef, useState } from "react";
import { obterEstadoOperacao, URL_EVENTOS_OPERACAO } from "../../api/operacao";
import { useInformarDispositivos } from "../../componentes/contexto-modo";
import type { EstadoOperacao, Pesagem } from "../../tipos/operacao";
import { aplicarEvento, TIPOS_EVENTO, type EventoOperacao } from "./aplicar-evento";

// shortcut: espera fixa só antes do primeiro estado; depois vale o limite_sem_heartbeat_ms do backend.
const ESPERA_SEM_ESTADO_MS = 5000;

/**
 * Canal SSE + estado (spec 009 §6.2, spec 022 §3.1). Abre o canal, depois busca o estado; os
 * eventos que chegam antes do GET ficam numa fila e são reaplicados por cima dele.
 */
export function useCanalOperacao() {
  const [estado, setEstado] = useState<EstadoOperacao | null>(null);
  const [sincronizado, setSincronizado] = useState(false);
  const [canalFechado, setCanalFechado] = useState(false);
  const [ultimaMensagemEm, setUltimaMensagemEm] = useState(0);
  const [agora, setAgora] = useState(() => Date.now());
  const [conexao, setConexao] = useState(0);
  const limite = useRef<number | null>(null);

  useEffect(() => {
    let ativo = true;
    let sincronizando = true;
    const fila: EventoOperacao[] = [];
    const canal = new EventSource(URL_EVENTOS_OPERACAO);
    // Último sinal de vida: abertura desta conexão, mensagem recebida ou estado sincronizado.
    let ultimoSinal = Date.now();

    const aplicar = (base: EstadoOperacao, eventos: EventoOperacao[]) => {
      try {
        return eventos.reduce(aplicarEvento, base);
      } catch {
        // Evento fora do formato do contrato: descarta e ressincroniza (spec 022 §3.1 item 6).
        sincronizar();
        return base;
      }
    };
    function sincronizar() {
      sincronizando = true;
      setSincronizado(false);
      obterEstadoOperacao().then(
        (s) => {
          if (!ativo) return;
          limite.current = s.tempo_real.limite_sem_heartbeat_ms;
          ultimoSinal = Date.now();
          setEstado(aplicar(s, fila.splice(0)));
          sincronizando = false;
          setSincronizado(true);
          setUltimaMensagemEm(Date.now());
        },
        // Fica bloqueada; um 401 já levou ao login pelo cliente (spec 016).
        () => undefined,
      );
    }

    canal.onopen = () => {
      setCanalFechado(false);
      sincronizar();
    };
    canal.onerror = () => {
      setSincronizado(false);
      sincronizando = true;
      if (canal.readyState === EventSource.CLOSED) {
        // Fechado de vez: o GET mostra se a sessão acabou (401 leva ao login). O relógio abaixo
        // reabre o canal.
        setCanalFechado(true);
        sincronizar();
      }
    };
    for (const tipo of TIPOS_EVENTO) {
      canal.addEventListener(tipo, (m: MessageEvent<string>) => {
        ultimoSinal = Date.now();
        setUltimaMensagemEm(ultimoSinal);
        let dados: unknown;
        try {
          dados = JSON.parse(m.data);
        } catch {
          sincronizar();
          return;
        }
        const evento = { tipo, dados } as EventoOperacao;
        if (sincronizando) fila.push(evento);
        else setEstado((e) => e && aplicar(e, [evento]));
      });
    }
    const relogio = setInterval(() => {
      const agora = Date.now();
      setAgora(agora);
      // Sem sinal além do limite, reabre o canal: uma conexão pendurada num proxy não avisa erro,
      // e um canal fechado de vez não tenta sozinho (spec 022 §3.1 item 5).
      if (agora - ultimoSinal > (limite.current ?? ESPERA_SEM_ESTADO_MS)) setConexao((c) => c + 1);
    }, 1000);
    return () => {
      ativo = false;
      canal.close();
      clearInterval(relogio);
    };
  }, [conexao]);

  const desatualizada =
    !sincronizado ||
    canalFechado ||
    estado === null ||
    agora - ultimaMensagemEm > estado.tempo_real.limite_sem_heartbeat_ms;
  // Desatualizada, o modo do cabeçalho fica DESCONHECIDO até o GET de ressincronização (spec 016 §6.4).
  useInformarDispositivos(desatualizada ? null : estado.dispositivos);

  const aplicarPesagem = useCallback((p: Pesagem) => {
    setEstado((e) => e && aplicarEvento(e, { tipo: "pesagem", dados: p }));
  }, []);
  const reconectar = useCallback(() => {
    setCanalFechado(false);
    setConexao((c) => c + 1);
  }, []);

  return { estado, sincronizado, desatualizada, canalFechado, agora, aplicarPesagem, reconectar };
}
