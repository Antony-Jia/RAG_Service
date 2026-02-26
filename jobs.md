下面给你一套**可以马上开 repo 搭骨架**的开发方案，目标是：

* **同一套 `kb_core` 业务逻辑**复用到服务端与本地（exe）；
* 本地 exe **既提供 API，又能独立托管管理端页面**（脱离 Electron 也能用浏览器打开）；
* 先把 **RAG 检索闭环**跑通（ingest → chunk → embed → index → retrieve → citations）。

我会按：**目录结构 → 本地工程（含管理端 + Electron 集成）→ 服务端预留 → core Ports 接口清单 → 数据模型 → 最小 API → 实现顺序** 给出一套可执行的骨架定义。

---

## 1) Monorepo 目录结构（3 层 + 一个前端 + Electron 集成）

推荐单仓库，Python 部分用 `packages/`（可发布/可依赖），应用用 `apps/`。

```
repo/
  packages/
    kb_core/                         # 纯业务逻辑 + Ports + 数据模型
      pyproject.toml
      src/kb_core/
        models/                      # Document/Chunk/Citation/Collection/Job
        ports/                       # 接口定义（Store/Index/Embedder/Parser...）
        pipelines/                   # ingest / retrieve 流程（只用 ports）
        utils/
      tests/

  apps/
    kb_desktop_daemon/               # 本地daemon：API + 静态UI托管 + SQLite + 本地向量索引
      pyproject.toml
      src/kb_desktop_daemon/
        http/                        # FastAPI 路由（/api/* + 静态文件）
        adapters/                    # sqlite_store, hnsw_vector, openai_embedder, parsers...
        config/
        static/                      # 管理端 build 输出（由 kb_admin_ui 构建产物拷贝/嵌入）
        main.py                      # 入口：启动、端口发现、token
      build/
        pyinstaller.spec             # exe 打包配置
      tests/

    kb_admin_ui/                     # 管理端前端（独立于 Electron，可被 daemon 托管）
      package.json
      src/
      build/                         # 前端构建输出（最终拷贝到 kb_desktop_daemon/static）
      vite.config.ts (或 CRA)

    kb_server/                       # 服务端预留：FastAPI + Postgres + 多租户/鉴权/队列
      pyproject.toml
      src/kb_server/
        http/
        adapters/                    # pg_store, pgvector_index, auth, tenants...
        migrations/
      docker/

  integrations/
    openanywork_plugin/              # Electron/TS 集成示例（可选，先占位）
      README.md
      src/
        spawnDaemon.ts               # 启动/healthcheck/端口发现/token
        client.ts                    # 调用本地API
        ui/                          # 如果你要在 Electron 内嵌一个 WebView 指向 localhost

  scripts/
    dev.ps1 / dev.sh                 # 一键启动：daemon + ui(热更新)
    build_desktop.ps1 / build.sh     # 构建 UI → 拷贝 static → 打包 exe

  README.md
```

### 为什么要把管理端独立成 `kb_admin_ui`

你要求“脱离 Electron 也能独立使用”，那就让它是一个独立 Web 应用（React/Vite），但交付时由本地 daemon 托管静态文件。这样：

* 浏览器直接打开：`http://127.0.0.1:<port>/`
* Electron 内也可以直接嵌：WebView 指向同一地址（或打开外部浏览器）

---

## 2) 本地工程方案（kb_desktop_daemon + kb_admin_ui + Electron 可集成）

### 2.1 本地 daemon 的运行形态（强烈建议这样做）

* `kb_desktop_daemon.exe` 启动后：

  * 绑定 `127.0.0.1`（绝不监听 0.0.0.0）
  * 端口：优先随机端口（避免冲突）
  * 生成 `token`（本机访问控制），写到：

    * stdout 第一行 JSON（给 Electron 读）
    * 或者写到 `~/.openanywork/kb/daemon.json`（给浏览器/脚本读）
  * 托管：

    * `/` 管理端静态页面
    * `/api/*` JSON API
    * `/healthz`、`/capabilities`

### 2.2 管理端 UI 如何打包进 exe（满足你“独立使用”）

* `kb_admin_ui` 构建：`pnpm build` → 输出到 `apps/kb_admin_ui/build/`
* 构建脚本把 build 目录复制到：

  * `apps/kb_desktop_daemon/src/kb_desktop_daemon/static/`
* daemon 用 FastAPI `StaticFiles` 挂载：

  * `GET /` → `index.html`
  * `GET /assets/*` → 静态资源
  * React Router 的 history 模式：所有未知路径 fallback 到 `index.html`

### 2.3 Electron 集成点（你先预留就行）

Electron 插件只需要做 3 件事：

1. spawn `kb_desktop_daemon.exe`
2. 读取 stdout JSON 拿到 `{port, token, base_url}`
3. 内嵌或外部打开 `base_url`；调用 `/api/*` 时带 `Authorization: Bearer <token>`

> 这样即使没有 Electron，用户也能手动启动 exe 并在浏览器打开管理端；有 Electron 时则体验更顺滑。

---

## 3) 服务端工程（kb_server）先预留什么

现在不急做，但建议你在骨架中提前锁定“复用方式”：

* `kb_server` 与 `kb_desktop_daemon` 使用同一套：

  * `kb_core.models`
  * `kb_core.pipelines`
  * `kb_core.ports`
* 只替换 adapters：

  * desktop：SQLite + 本地向量索引
  * server：Postgres(+pgvector) +（可选）队列/对象存储 + 多租户鉴权

---

## 4) `kb_core` Ports 接口清单（先跑通 RAG 所需的最小集合）

先给 MVP 必需的 Ports（后续 KG / MinerU 都是往这里加）。

```python
# kb_core/ports/store.py
class DocumentStore(Protocol):
    def create_document(self, doc: Document) -> Document: ...
    def get_document(self, document_id: str) -> Document | None: ...
    def list_documents(self, collection_id: str, limit: int, offset: int) -> list[Document]: ...
    def delete_document(self, document_id: str) -> None: ...

class ChunkStore(Protocol):
    def upsert_chunks(self, chunks: list[Chunk]) -> None: ...
    def get_chunks(self, chunk_ids: list[str]) -> list[Chunk]: ...
    def delete_chunks_by_document(self, document_id: str) -> None: ...

class CollectionStore(Protocol):
    def create_collection(self, c: Collection) -> Collection: ...
    def get_collection(self, collection_id: str) -> Collection | None: ...
    def list_collections(self, limit: int, offset: int) -> list[Collection]: ...
    def delete_collection(self, collection_id: str) -> None: ...

class JobStore(Protocol):
    def create_job(self, job: Job) -> Job: ...
    def update_job(self, job_id: str, patch: JobPatch) -> Job: ...
    def get_job(self, job_id: str) -> Job | None: ...
    def list_jobs(self, limit: int, offset: int, status: JobStatus | None) -> list[Job]: ...


# kb_core/ports/vector.py
class VectorIndex(Protocol):
    def upsert(self, items: list[VectorItem]) -> None: ...
    def query(self, vector: list[float], top_k: int, filter: MetadataFilter | None) -> list[VectorHit]: ...
    def delete_by_document(self, document_id: str) -> None: ...


# kb_core/ports/embedder.py
class Embedder(Protocol):
    @property
    def dim(self) -> int: ...
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


# kb_core/ports/parser.py
class Parser(Protocol):
    def can_parse(self, mime: str, ext: str) -> bool: ...
    def parse(self, blob: BlobRef, opts: ParseOptions) -> ParsedDocument: ...


# kb_core/ports/blob.py  (MVP 可先用本地文件系统实现)
class BlobStore(Protocol):
    def put(self, data: bytes, *, name: str, mime: str) -> BlobRef: ...
    def get(self, ref: BlobRef) -> bytes: ...
```

### MVP 里先不强推的 Ports（后续再加）

* `TextIndex`（BM25/FTS hybrid）——先纯向量检索闭环更快
* `Reranker`（cross-encoder / LLM rerank）
* `GraphStore`（知识图谱）
* `EventBus/Queue`（分布式任务）

---

## 5) 数据模型（Document / Chunk / Citation / Collection / Job）

我给你一套**足够用、又不把自己锁死**的模型。建议用 Pydantic v2（序列化/校验舒服），但核心层尽量不绑 FastAPI。

### 5.1 Collection

* 表示一个知识库空间（本地单用户也建议保留 collection 概念，未来迁移到 server 更平滑）

字段建议：

* `id`, `name`, `description`
* `created_at`, `updated_at`
* `settings`（json：chunk_size、overlap、embedder 等）

### 5.2 Document

* 描述“一个原始文档实体”

字段建议：

* `id`, `collection_id`
* `title`, `source_type`（upload/url/manual）
* `source_uri`（可空）
* `mime`, `size_bytes`
* `hash`（用于去重）
* `blob_ref`（原文存储引用）
* `status`（pending/ingested/failed/deleted）
* `metadata`（json：tags、author、time、custom props）
* `created_at`, `updated_at`

### 5.3 Chunk

* 检索的最小单元

字段建议：

* `id`, `collection_id`, `document_id`
* `text`
* `token_count`（可选）
* `order`（在文档中的顺序）
* `metadata`（json：heading_path、page_start/page_end、table_id、section 等）
* `embedding_ref`（可选：如果向量不存 DB）
* `created_at`

### 5.4 Citation

* 返回给用户的“可定位引用”
* 典型包含：`document_id`、`chunk_id`、`page`、`start_char/end_char`、`snippet`

### 5.5 Job

* ingest/reindex/delete 都走 job，UI 才能展示进度

字段建议：

* `id`, `type`（INGEST/DELETE/REINDEX）
* `status`（QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED）
* `progress`（0-100）
* `message`（错误信息/阶段信息）
* `payload`（json：document_id/collection_id/options）
* `created_at`, `started_at`, `finished_at`

---

## 6) 最小 API（先跑通 ingest / retrieve / delete / jobs）

统一走 `/api/v1/*`，这样本地和服务端可以一致。

### 基础

* `GET /healthz` → `{status:"ok"}`
* `GET /api/v1/capabilities` → 声明支持的 parser、embedder、filter、hybrid 等（用于 Electron/管理端自适应）

### Collections（管理端必备）

* `POST /api/v1/collections`
* `GET /api/v1/collections`
* `GET /api/v1/collections/{id}`
* `DELETE /api/v1/collections/{id}`

### Ingest（闭环入口）

两种形式都建议做，但 MVP 先做 upload：

1. 上传文件：

* `POST /api/v1/ingest/upload` (multipart/form-data)

  * file
  * `collection_id`
  * `options`（json：parser、chunk_size、overlap、language…）
  * 返回：`{job_id, document_id}`

2. URL 拉取（可后补）：

* `POST /api/v1/ingest/url`

  * `{collection_id, url, options}`
  * 返回 `{job_id, document_id}`

### Retrieve（闭环出口）

* `POST /api/v1/retrieve`

  * 请求：

    * `query: str`
    * `collection_ids: [str]`
    * `top_k: int`（默认 10）
    * `filters`（可选，先做最简单：metadata equals）
    * `include_chunks: bool`（返回全文片段）
  * 响应：

    * `hits: [{chunk_id, score, text?, citation, document}]`

> 注意：这一步你先只做“召回 + citations”，不要把“最终回答生成”塞进知识库服务；LLM 生成放在 DeepResearch / OpenAnyWork 的上层 Agent。

### Delete（最小一致性）

* `DELETE /api/v1/documents/{document_id}`

  * 返回 `{job_id}` 或直接同步删（但我建议也走 job）

### Jobs（UI 必备）

* `GET /api/v1/jobs?status=&limit=&offset=`
* `GET /api/v1/jobs/{job_id}`

### 鉴权（本地最小安全）

* 所有 `/api/*` 要求 `Authorization: Bearer <token>`
* 管理端页面加载后，token 通过：

  * 方式 A：daemon 启动时把 token 写到本机配置文件，管理端从 `/api/v1/session` 获取（只允许 localhost 且带一次性 nonce）
  * 方式 B：管理端访问 URL 带 `?t=...`（不太安全，但本机可接受，建议短期有效）

MVP 推荐：**daemon 首次启动生成 token → 写入本地文件 → 管理端通过一个仅限 localhost 的 `/api/v1/session` 取 token**。

---

## 7) 本地存储/向量索引的 MVP 选型（为了“最快闭环”且易打包）

你要尽快看到效果，我建议本地先用：

* **SQLite**：存 collections / documents / chunks / jobs / metadata
* **本地向量索引**：实现一个 `VectorIndex` adapter，优先选：

  * `hnswlib`（简单、快、可落盘、依赖相对可控）
  * 或者你已有偏好的本地向量库（后面可替换，Ports 已隔离）

向量落盘方式建议：

* index 文件：`data/index/<collection_id>.bin`
* metadata 映射：SQLite 里维护 `chunk_id -> internal_vector_id`
* 删除 document：删除其 chunk 映射 + `VectorIndex.delete_by_document()`（可做惰性删除，后续 reindex 压缩）

> 服务端那边未来换成 pgvector，只要实现 `VectorIndex` adapter 即可。

---

## 8) 开发顺序（一天内能跑通闭环的路线）

### Step 0：初始化工程与脚手架

* monorepo + `pyproject.toml`（建议 uv/poetry 任意）
* 统一 lint/test：ruff + mypy + pytest
* 约定：所有 ID 用 `uuid7` 或 `uuid4`

### Step 1：先做 kb_core（模型 + ports + pipelines）

* models：Collection/Document/Chunk/Citation/Job
* ports：Store/VectorIndex/Embedder/Parser
* pipeline：

  * `ingest_document()`：parse → chunk → embed → upsert store/index → job 更新
  * `retrieve()`：embed_query → vector.query → join chunk/doc → build citations

### Step 2：做 kb_desktop_daemon adapters（能跑起来）

* sqlite adapters：collections/documents/chunks/jobs
* embedder：先做 OpenAI（最快见效），并预留本地 embedding
* parser：先做基础（txt/md/pdf 简版）
* vector：hnswlib（或你的替代）

### Step 3：做 HTTP API（最小）

* `/healthz` `/capabilities`
* `/api/v1/collections`
* `/api/v1/ingest/upload` → 创建 job → 后台线程/async task 执行 pipeline
* `/api/v1/retrieve`
* `/api/v1/jobs`

### Step 4：做 kb_admin_ui（最小可用 3 页）

1. Collections：创建/选择
2. Ingest：上传文件，显示 job 状态
3. Search：输入 query，展示 hits（含 citation：doc title + page + snippet）

### Step 5：打包流程（先能打出 exe）

* build UI → copy 到 daemon/static
* pyinstaller 打包 daemon.exe（包含 static 目录）
* 运行 exe 后浏览器访问 `http://127.0.0.1:<port>/`

### Step 6：Electron 集成（不阻塞闭环）

* Electron 插件 spawn exe → 打开 localhost 管理端 / 或内嵌
* 业务指令检索直接调用 `/api/v1/retrieve`

---

## 9) 你开 repo 后我建议你先写下的“契约文件”（强约束复用）

在 `shared/openapi/` 放一个简化的 OpenAPI（哪怕先手写 YAML），把：

* models schema
* endpoints（ingest/retrieve/jobs）
  固定下来。这样你未来做 `kb_server` 时几乎就是复制路由骨架 + 换 adapters。


