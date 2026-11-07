import { Route, Routes } from "react-router";
import { LayoutBase } from "./componentes/LayoutBase";
import { LayoutTotem } from "./componentes/LayoutTotem";
import { PaginaAgendamentos } from "./paginas/agendamentos/PaginaAgendamentos";
import { PaginaCadastros } from "./paginas/cadastros/PaginaCadastros";
import { PaginaDispositivos } from "./paginas/dispositivos/PaginaDispositivos";
import { PaginaDiagnostico } from "./paginas/diagnostico/PaginaDiagnostico";
import { PaginaHistorico } from "./paginas/historico/PaginaHistorico";
import { PaginaInicio } from "./paginas/PaginaInicio";
import { PaginaLogin } from "./paginas/PaginaLogin";
import { PaginaNaoEncontrada } from "./paginas/PaginaNaoEncontrada";
import { PaginaAutoatendimento } from "./paginas/totem/PaginaAutoatendimento";
import { PaginaOperacao } from "./paginas/operacao/PaginaOperacao";
import { PaginaUsuarios } from "./paginas/PaginaUsuarios";

export function Rotas() {
  return (
    <Routes>
      <Route path="/login" element={<PaginaLogin />} />
      <Route path="/autoatendimento" element={<LayoutTotem />}>
        <Route index element={<PaginaAutoatendimento />} />
      </Route>
      <Route element={<LayoutBase />}>
        <Route index element={<PaginaInicio />} />
        <Route path="operacao" element={<PaginaOperacao />} />
        <Route path="diagnostico" element={<PaginaDiagnostico />} />
        <Route path="dispositivos" element={<PaginaDispositivos />} />
        <Route path="usuarios" element={<PaginaUsuarios />} />
        <Route path="agendamentos" element={<PaginaAgendamentos />} />
        <Route path="historico" element={<PaginaHistorico />} />
        <Route path="cadastros" element={<PaginaCadastros />} />
        <Route path="*" element={<PaginaNaoEncontrada />} />
      </Route>
    </Routes>
  );
}
