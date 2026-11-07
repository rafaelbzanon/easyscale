import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { Rotas } from "./rotas";
import "./estilos/global.css";

const raiz = document.getElementById("raiz");
if (!raiz) throw new Error("Elemento #raiz ausente no index.html.");

createRoot(raiz).render(
  <StrictMode>
    <BrowserRouter>
      <Rotas />
    </BrowserRouter>
  </StrictMode>,
);
