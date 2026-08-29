# ---- Build stage ----------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Left empty on purpose. Vite inlines VITE_* at build time, so baking a host in
# here would pin the bundle to one deployment. With it empty, the client falls
# back to `window.location.origin` and talks to whatever origin served it —
# which nginx below proxies through to the backend.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ---- Runtime stage --------------------------------------------------------
FROM nginx:1.27-alpine

# Serving through nginx rather than `serve` gives us the /api reverse proxy, so
# the browser sees one origin and no CORS preflight is involved at all.
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
