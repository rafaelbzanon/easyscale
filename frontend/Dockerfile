# Imagem do frontend — spec specs/features/026-docker-frontend/spec.md (FE-401).
# Contexto de build: esta pasta (`docker build -t pesagem-frontend frontend/`).

# Estágio de build: só aqui existe Node. Não vai para a imagem final (ADR-0007).
FROM node:22.22.2-alpine AS build
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY . .
RUN npm run build

# Imagem final: o dist/ e o Caddy. Sem Node em execução.
FROM caddy:2.11.6-alpine
# Os arquivos do Vite têm hash no nome: podem ficar em cache para sempre. O index.html
# não, senão uma versão nova da tela apontaria para arquivos que não existem mais.
# Um /assets/ que não existe cai no index.html e, por isso, não ganha o cache longo.
# O destino de /api vem de PESAGEM_GERAL_URL_BACKEND, sem valor padrão (spec 016 §7).
# Sem `encode` em /api, para não segurar o fluxo de eventos (ADR-0005).
COPY <<'EOF2' /etc/caddy/Caddyfile
{
	admin off
}

:8080 {
	handle /api/* {
		reverse_proxy {$PESAGEM_GERAL_URL_BACKEND} {
			flush_interval -1
		}
	}
	handle {
		root * /srv
		encode zstd gzip
		header ?Cache-Control no-cache
		@com_hash {
			path /assets/*
			file {
				root /srv
				try_files {path}
			}
		}
		header @com_hash Cache-Control "public, max-age=31536000, immutable"
		try_files {path} /index.html
		file_server
	}
}
EOF2
COPY --from=build /app/dist /srv

# Sem privilégios. A porta 8080 não exige root.
RUN adduser -S -u 10001 pesagem && chown pesagem /data /config
USER pesagem
EXPOSE 8080
