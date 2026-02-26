# RAG Service Monorepo

可复用的 Python 知识库引擎 monorepo，包含两个宿主应用：
- `kb_desktop_daemon`: 完整的本地可运行宿主（SQLite + ChromaDB + 本地 API + 静态 UI）
- `kb_server`: 用于未来 Postgres + pgvector 部署的可运行骨架

## 项目结构
- `packages/kb_core`: 模型、端口、管道、服务
- `apps/kb_desktop_daemon`: FastAPI 守护进程 + 适配器 + 任务工作器 + 静态托管
- `apps/kb_admin_ui`: React/Vite 管理后台 UI
- `apps/kb_server`: 服务端骨架
- `integrations/openanywork_plugin`: 插件集成示例
- `shared/openapi`: API 合约草稿

## 快速开始
1. `uv sync --all-packages --group dev`
2. UI 开发（可选）：
   - `cd apps/kb_admin_ui`
   - `npm install`
   - `npm run dev`
3. 运行桌面守护进程：
   - `uv run --package kb-desktop-daemon kb-desktop-daemon`

守护进程在 stdout 输出运行时 JSON：
```json
{"port": 8899, "token": "...", "base_url": "http://127.0.0.1:8899"}
```
同时保存到 `~/.openwork/kb/daemon.json`。

## 认证
所有 `/api/*` 路由需要：
- `Authorization: Bearer <token>`

## 环境配置
复制 `.env.example` 到 `.env` 并调整提供商：
- `LLM_PROVIDER=ollama|open_compat`
- `EMBEDDING_PROVIDER=ollama|open_compat`

## 桌面端构建
- `scripts/build_desktop.ps1` (Windows)
- `scripts/build_desktop.sh` (Unix)

构建流程：
1. 构建 `kb_admin_ui`
2. 将构建产物复制到 daemon 的 `static/` 目录
3. 通过 PyInstaller 打包 daemon 可执行文件（包含占位 spec 文件）

## 测试
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy packages apps`

## 项目状态
- 桌面端路径已实现 MVP 的文档摄取/检索/任务流程。
- 服务端路径已预置脚手架，包含针对 Postgres/pgvector、认证、租户和队列的 TODO 适配器。
