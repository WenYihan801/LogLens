# 作品集与简历材料（第 6 周任务）

> 原则（SRS §13.2）：只写真实完成并验证过的内容。下面的数字都来自本仓库的测试与 `make perf`；在你自己的 Mac 上跑一次 `make perf`，用你机器的结果替换。

## 简历描述（英文）

**LogLens — Lightweight Log Analysis & Security Event Detection Platform**  ·  Python, FastAPI, React, TypeScript, PostgreSQL, Docker

- Designed and built a full-stack log analysis platform (FastAPI + SQLAlchemy 2 + Alembic, React + TypeScript + Recharts, PostgreSQL) structured as a modular monolith with separate router, service, parser and detection layers.
- Implemented fault-tolerant parsing and normalisation for Nginx access logs and SSH auth logs (IPv4/IPv6, ISO 8601 and syslog timestamps, UTC storage); malformed lines are recorded with line-level error codes without aborting the import.
- Built a configurable sliding-window rule engine detecting SSH brute force, HTTP 404 bursts and sensitive-path probing, with evidence links for every alert and idempotent re-runs via deterministic dedup keys.
- Developed an alert investigation workflow — dashboard, server-side filtering and pagination, evidence view, status triage, notes, CSV/JSON export with CSV formula-injection protection.
- Wrote 100 backend tests (run on SQLite and PostgreSQL), 23 frontend tests and Playwright end-to-end tests; CI checks lint, types, migration drift and a Docker Compose smoke test. A 20,000-line import completes in about 2.3 s.
- Containerised the stack with Docker Compose and added a server-enforced read-only demo mode with synthetic datasets.

## 面试可讲的技术难点

1. **滑动窗口与“一次攻击一条告警”**：单纯滑动窗口会在持续攻击时每个事件都触发一次。设计“episode”：达到阈值开启，与上一次事件间隔 ≤ 窗口则延续，超过窗口关闭。边界用 `≤`（含 300 s），并用 300 s / 301 s 两个测试固定。
2. **检测幂等**：`dedup_key = 数据集:规则:IP:首个证据事件 ID`。重跑时更新已存在告警（保留状态和备注）、插入新告警、删除不再成立的告警——而不是“全删重建”导致调查记录丢失。
3. **SSH 双重计数**：OpenSSH 对同一次尝试会同时记录 `Invalid user X` 和 `Failed password for invalid user X`，只统计 FAILURE 才不会把 20 次尝试算成 40 次。
4. **不能只看扩展名**：二进制嗅探（NUL/控制字符比例）、严格 UTF-8、前 50 行格式匹配率 ≥ 20%，否则返回带建议类型的 `FORMAT_MISMATCH`。
5. **只读模式在服务端强制**：HTTP 中间件拦截所有写方法，前端只是锦上添花；测试直接调用 7 种写接口验证 403 且数据不变。
6. **不可信输入**：日志内容在 React 中只作为文本节点渲染，ESLint 规则禁止 `dangerouslySetInnerHTML`；CSV 导出对 `= + - @` 开头的单元格加 `'` 前缀；样本里专门放了一条公式注入 payload。
7. **时间与时区**：经典 syslog 没有年份和时区，通过 `SSH_LOG_YEAR` / `SSH_LOG_TIMEZONE` 显式配置；数据库统一 UTC，前端按浏览器时区显示。

## 演示视频脚本（约 3 分钟，SRS §13.3）

1. 首页空状态：一句话介绍项目定位。
2. Datasets → 加载 “Nginx – scanner activity”：展示 961 行 / 958 成功 / 3 失败 / 2 告警；打开详情看失败行的错误码和原因。
3. 再加载 “SSH – brute force”。
4. Dashboard：切换数据集，统计和图表随之更新。
5. Alerts → 打开 203.0.113.99 的 SSH 暴力破解告警：讲规则（≥5 次 / 300 秒）、命中 40 次、“可疑行为而非已确认攻击”。
6. 点击证据行查看原始日志——强调可追溯性。
7. 改为 ACKNOWLEDGED、添加备注、导出 JSON。
8. 终端展示 `docker compose up --build` 和 `make demo` 的只读横幅；最后展示 GitHub README 和 CI 绿勾。
