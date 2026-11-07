import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// shortcut: só o que este arquivo usa do Node, sem @types/node; trocar se a config crescer.
declare const process: { env: Record<string, string | undefined> };

export default defineConfig(({ command, mode }) => {
  const urlBackend = process.env["PESAGEM_GERAL_URL_BACKEND"];
  // Spec 016 §7: sem URL padrão inventada; só o servidor de desenvolvimento precisa dela.
  if (command === "serve" && mode !== "test" && !urlBackend) {
    throw new Error(
      "Defina PESAGEM_GERAL_URL_BACKEND com a URL do backend para usar o npm run dev.",
    );
  }
  return {
    plugins: [react(), tailwindcss()],
    server: urlBackend ? { proxy: { "/api": { target: urlBackend } } } : {},
    test: {
      environment: "jsdom",
      setupFiles: ["./src/configuracao-testes.ts"],
    },
  };
});
