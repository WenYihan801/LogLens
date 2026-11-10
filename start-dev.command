#!/bin/zsh
# Start LogLens in development mode (hot reload). Double-click; close the window or press Ctrl+C to stop.
cd "$(dirname "$0")" || exit 1
[[ -x /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
[[ -x /usr/local/bin/brew ]] && eval "$(/usr/local/bin/brew shellenv)"
command -v brew >/dev/null && [[ -d "$(brew --prefix)/opt/node@22/bin" ]] && export PATH="$(brew --prefix)/opt/node@22/bin:$PATH"
[[ -d backend/.venv && -d frontend/node_modules ]] || { echo "请先双击 setup-mac.command 完成初始化。"; read -k1; exit 1; }

docker info >/dev/null 2>&1 || { open -a Docker; echo "等待 Docker…"; for i in {1..60}; do docker info >/dev/null 2>&1 && break; sleep 3; done; }
make db-up >/dev/null && for i in {1..40}; do docker compose exec -T db pg_isready -q && break; sleep 1; done
make migrate >/dev/null 2>&1

make dev-backend &
API_PID=$!
trap 'kill $API_PID 2>/dev/null; exit' INT TERM EXIT
(for i in {1..30}; do curl -fs http://localhost:5173 >/dev/null 2>&1 && open http://localhost:5173 && break; sleep 1; done) &
echo "API: http://localhost:8000/docs   Web: http://localhost:5173   (Ctrl+C 停止)"
make dev-frontend
