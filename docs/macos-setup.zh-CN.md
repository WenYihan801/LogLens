# LogLens 开发指南：macOS + VS Code

本指南替代 SRS 第 9 章的 Windows + WSL 2 方案。macOS 本身就是类 Unix 系统，**不需要 WSL**；所有命令都在 macOS 自带的「终端」或 VS Code 集成终端（zsh）里运行。Apple Silicon（M1–M4）和 Intel Mac 都适用。

---

## 1. 一次性安装工具（约 20–30 分钟）

### 1.1 Xcode Command Line Tools（git、make、编译器）

```bash
xcode-select --install
```

### 1.2 Homebrew

到 <https://brew.sh> 复制安装命令执行。安装结束时终端会提示把 brew 加入 PATH，**照着执行那两行**（Apple Silicon 通常是）：

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 1.3 Git、Python 3.12、Node.js 22

```bash
brew install git python@3.12 node@22
# node@22 是 "keg-only"，需要手动加入 PATH：
echo 'export PATH="$(brew --prefix node@22)/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

python3.12 --version   # Python 3.12.x
node --version         # v22.x
git --version
```

> 已经用 nvm / pyenv 管理版本也可以，项目根目录的 `.nvmrc`（22）和 `.python-version`（3.12）会被它们识别。

配置 Git 身份（提交记录会显示在 GitHub 上）：

```bash
git config --global user.name  "你的名字"
git config --global user.email "你的 GitHub 邮箱"
git config --global init.defaultBranch main
```

### 1.4 Docker Desktop for Mac

1. 到 <https://www.docker.com/products/docker-desktop/> 下载对应芯片版本（Apple Silicon / Intel）。个人使用免费。
2. 打开 Docker Desktop，等待左下角显示 *Engine running*。
3. 验证：

```bash
docker run --rm hello-world
docker compose version
```

> 也可以用更轻量的 **OrbStack**（<https://orbstack.dev>），命令完全兼容。

### 1.5 VS Code

1. 安装 VS Code：<https://code.visualstudio.com>（或 `brew install --cask visual-studio-code`）。
2. 打开 VS Code → `⌘⇧P` → 输入 **Shell Command: Install 'code' command in PATH** → 回车。之后就能在终端用 `code .` 打开文件夹。

---

## 2. 获取项目并打开

```bash
mkdir -p ~/Projects && cd ~/Projects
# 方式 A：解压我提供的 LogLens.zip 到这里
# 方式 B：从你自己的 GitHub 仓库克隆
cd LogLens
code .
```

VS Code 右下角会弹出 **“此工作区有推荐扩展”** → 点 *Install All*。推荐列表在 `.vscode/extensions.json`：

| 扩展 | 用途 |
|---|---|
| Python / Pylance / Python Debugger | 后端补全、跳转、调试 |
| Ruff | Python 格式化与 lint（保存时自动执行） |
| ESLint / Prettier | 前端 lint 与格式化 |
| Tailwind CSS IntelliSense | Tailwind 类名补全 |
| Vitest / Playwright | 在侧边栏直接运行前端单元测试和 E2E 测试 |
| Container Tools | 查看容器、日志 |
| SQLTools + PostgreSQL driver | 在 VS Code 里直接查询数据库 |
| REST Client | 打开根目录 `api.http`，点击 *Send Request* 调用 API |

---

## 3. 初始化项目（一次）

在 VS Code 集成终端（`` ⌃` ``）中执行：

```bash
make setup
```

它会：
1. 由 `.env.example` 生成 `.env`（**请打开改掉 `POSTGRES_PASSWORD`，两处保持一致**：`POSTGRES_PASSWORD` 和 `DATABASE_URL` 里的密码）；
2. 创建 `backend/.venv` 并安装 Python 依赖；
3. 在 `frontend/` 执行 `npm ci`。

然后让 VS Code 使用虚拟环境：`⌘⇧P` → **Python: Select Interpreter** → 选 `./backend/.venv/bin/python`（`.vscode/settings.json` 已默认指向它，一般会自动选中）。

`make help` 可以查看所有命令。

---

## 4. 运行方式

### 方式一：开发模式（推荐日常使用，支持热更新）

数据库在 Docker 里，后端和前端在 Mac 本机运行：

```bash
make db-up        # 启动 PostgreSQL 容器（第一次会拉取镜像）
make migrate      # 执行 Alembic 迁移，建好 7 张表
make seed         # （可选）导入 4 份合成样本日志
```

打开两个终端标签：

```bash
make dev-backend   # FastAPI  → http://localhost:8000/docs  （Swagger 接口文档）
make dev-frontend  # Vite     → http://localhost:5173        （打开这个）
```

Vite 已配置把 `/api` 代理到 `localhost:8000`，所以开发时不需要处理 CORS。

**用 VS Code 调试**：左侧「运行和调试」(`⌘⇧D`) 选择 **Full stack (API + Vite)** → F5。它会自动启动数据库并迁移，然后同时启动带断点调试的 FastAPI 和 Vite。在 `backend/app/services/detection/engine.py` 打个断点，再在网页里加载样本，就能单步看检测算法。

### 方式二：完整 Docker（一键启动，接近生产）

```bash
make up            # = docker compose up --build -d
open http://localhost:8080
make logs          # 查看日志
make down          # 停止（数据库数据保留在 Docker volume 中）
```

### 方式三：公网只读 Demo 预览

```bash
make demo          # 自动导入样本 + DEMO_READ_ONLY=true
```

页面顶部会出现只读横幅；上传、删除、修改告警在**服务端**被拒绝（HTTP 403 `DEMO_READ_ONLY`）。

---

## 5. 测试

| 命令 | 内容 | 依赖 |
|---|---|---|
| `make test-backend` | 100 个 pytest（解析器、规则、API、只读模式），使用临时 SQLite | 无 |
| `make test-backend-pg` | 同一套测试跑在 PostgreSQL `loglens_test` 库上 | `make db-up` |
| `make test-frontend` | 23 个 Vitest 组件/页面测试 | 无 |
| `make e2e` | Playwright：导入样本 → 告警 → 证据 → 改状态 → 备注 → 导出 | 应用运行在 :5173 |
| `make lint` | Ruff + ESLint + TypeScript 类型检查 | 无 |
| `make perf` | 20,000 行导入耗时与 Dashboard 响应时间（NFR-01/02） | `make db-up` |

第一次运行 E2E 前需要下载浏览器：`cd frontend && npx playwright install chromium`。

VS Code 中也可以直接在「测试」侧边栏（烧杯图标）运行/调试单个 pytest 或 Vitest 用例。

---

## 6. 连接数据库查看数据

- **VS Code SQLTools**：侧边栏数据库图标 → *LogLens (Docker)* → 输入 `.env` 里的密码。
- **终端**：`make db-shell`，然后例如：

```sql
SELECT rule_code, threshold, window_seconds, severity FROM detection_rules;
SELECT severity, status, count(*) FROM security_alerts GROUP BY 1, 2;
```

---

## 7. 推送到 GitHub

```bash
cd ~/Projects/LogLens
git init && git add . && git commit -m "feat: LogLens v1.0"
# 在 GitHub 新建空仓库 LogLens 后：
git remote add origin git@github.com:<你的用户名>/LogLens.git
git push -u origin main
```

`.github/workflows/ci.yml` 会自动运行：后端 lint + 迁移检查 + PostgreSQL 测试、前端 lint/类型/测试/构建、Playwright E2E、Docker Compose 冒烟测试与只读模式验证。

> SSH key：`ssh-keygen -t ed25519 -C "你的邮箱"`，然后 `pbcopy < ~/.ssh/id_ed25519.pub`，粘贴到 GitHub → Settings → SSH and GPG keys。

---

## 8. Mac 常见问题

| 现象 | 原因与解决 |
|---|---|
| `make db-up` 报 `port 5432 is already allocated` | Mac 上已装了 Postgres.app 或 `brew services` 的 PostgreSQL。在 `.env` 设置 `DB_HOST_PORT=5433`，并把 `DATABASE_URL` 中的端口也改成 `5433`。 |
| 8000 / 8080 端口被占用 | 修改 `.env` 中 `API_HOST_PORT` / `WEB_HOST_PORT`。`lsof -i :8000` 可查看占用进程。 |
| `password authentication failed` | 改过 `POSTGRES_PASSWORD` 但数据库 volume 是旧密码创建的。执行 `make db-reset`（⚠️ 会清空本地数据库）。 |
| `python3.12: command not found` | Homebrew 未加入 PATH，重做 1.2 节最后两行，或重开终端。 |
| `node: command not found` 或版本不对 | node@22 是 keg-only，重做 1.3 节的 PATH 设置。 |
| `docker: Cannot connect to the Docker daemon` | Docker Desktop 没有启动，打开它等待 *Engine running*。 |
| VS Code 中 import 标红 | 解释器没选 `backend/.venv`，见第 3 节。 |
| Apple Silicon 镜像问题 | 本项目所用镜像均为多架构（含 arm64），无需 `--platform`。 |
| 下载的 `.log` 文件无法上传 | 若是 `.gz` 压缩日志，先 `gunzip`。系统会拒绝二进制和非 UTF-8 文件，并给出原因。 |
| SSH 日志时间差了几个小时 | 经典 syslog 格式没有时区。在 `.env` 设置 `SSH_LOG_TIMEZONE=Asia/Singapore`（或日志所在服务器的时区），然后重新导入。 |

---

## 9. 与原 Windows 方案的差异总结

| 原方案（SRS v1.0） | macOS 方案（v1.1） |
|---|---|
| WSL 2 + Ubuntu 提供 Linux 环境 | macOS 原生 zsh，无需 WSL |
| 项目放在 `~/projects`（WSL 文件系统） | 项目放在 `~/Projects`（任意本地目录即可） |
| VS Code + WSL 扩展 | VS Code 直接打开本地文件夹 |
| Docker Desktop（WSL 2 backend） | Docker Desktop for Mac 或 OrbStack |
| `apt` 安装依赖 | Homebrew 安装依赖 |
| NVIDIA GPU 留给后续 AI 项目 | Docker 中不可用 Apple GPU；V1.0 不需要 GPU，后续 AI 项目可用原生 Ollama/MLX |

其余内容（技术栈、架构、数据库、API、规则、测试、部署）完全不变。
