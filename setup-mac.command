#!/bin/zsh
# LogLens one-time setup for macOS. Double-click in Finder (or run ./setup-mac.command).
# Safe to run again: each step skips what is already done. Never uses sudo.
cd "$(dirname "$0")" || exit 1
autoload -U colors && colors
ok()   { print -P "%F{green}✔%f $1"; }
warn() { print -P "%F{yellow}!%f $1"; }
fail() { print -P "%F{red}✘ $1%f"; echo; read -k1 "?按任意键关闭 / Press any key to close"; exit 1; }

echo "=== LogLens setup: $(pwd) ==="
# Files unpacked from a zip can end up readable only by you; Docker containers need to read them.
chmod -R u+rwX,go+rX . && chmod +x backend/docker-entrypoint.sh backend/db/init-test-db.sh *.command

# ---- Homebrew on PATH (Apple Silicon / Intel)
[[ -x /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
[[ -x /usr/local/bin/brew ]] && eval "$(/usr/local/bin/brew shellenv)"
command -v brew >/dev/null && [[ -d "$(brew --prefix 2>/dev/null)/opt/node@22/bin" ]] && export PATH="$(brew --prefix)/opt/node@22/bin:$PATH"

missing=()
# Any Python >= 3.11 works (Homebrew or the python.org installer).
PY=""
for c in python3.12 python3.13 python3.11 python3; do
  p=$(command -v $c) || continue
  $p -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null && { PY=$p; break; }
done
[[ -n "$PY" ]] || missing+=("Python 3.11+  →  brew install python@3.12   或   https://www.python.org/downloads/macos/")
command -v node >/dev/null && [[ $(node -p 'process.versions.node.split(".")[0]') -ge 20 ]] || missing+=("Node.js 20+  →  brew install node@22   或   https://nodejs.org (LTS 安装包)")
command -v docker >/dev/null || missing+=("Docker Desktop  →  https://www.docker.com/products/docker-desktop/ （Apple 芯片版）")
if (( ${#missing} )); then
  warn "还缺少以下工具，请先安装，然后重新双击本脚本："
  for m in $missing; do echo "   • $m"; done
  fail "Setup stopped: missing tools"
fi
ok "Python $($PY -V | cut -d' ' -f2), Node $(node -v), $(docker --version | cut -d, -f1)"

docker info >/dev/null 2>&1 || { open -a Docker 2>/dev/null; warn "正在启动 Docker Desktop，等待引擎就绪…"; for i in {1..60}; do docker info >/dev/null 2>&1 && break; sleep 3; done; }
docker info >/dev/null 2>&1 || fail "Docker 引擎没有启动。请打开 Docker Desktop，等左下角显示 Engine running 后重试。"
ok "Docker engine running"

[[ -f .env ]] || cp .env.example .env
make venv PYTHON="$PY" || fail "Python 依赖安装失败（见上方输出）"
ok "backend/.venv ready"
make frontend-install || fail "npm ci 失败（见上方输出）"
ok "frontend/node_modules ready"

make db-up || fail "PostgreSQL 容器启动失败。若提示 5432 端口被占用，把 .env 里的 DB_HOST_PORT 和 DATABASE_URL 端口改成 5433 再试。"
echo "等待数据库就绪…"
for i in {1..40}; do docker compose exec -T db pg_isready -q && break; sleep 1; done
make migrate || fail "数据库迁移失败"
ok "database migrated"
make seed && ok "synthetic samples loaded"

echo
ok "全部完成！现在双击 start-dev.command 启动 LogLens（或在 VS Code 按 F5 选 Full stack）。"
read -k1 "?按任意键关闭 / Press any key to close"
