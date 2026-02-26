# KB Desktop Daemon — Electron 集成开发者手册

> **适用版本**: kb-desktop-daemon v0.1.0  
> **面向读者**: 负责将 `kb-desktop-daemon` 嵌入 Electron 主进程的前端/桌面开发者

---

## 目录

1. [架构概览](#1-架构概览)
2. [发布产物说明](#2-发布产物说明)
3. [环境配置（.env）](#3-环境配置env)
4. [数据目录与数据库](#4-数据目录与数据库)
5. [在 Electron 中启动 Daemon](#5-在-electron-中启动-daemon)
6. [获取运行时端口与 Token](#6-获取运行时端口与-token)
7. [认证机制](#7-认证机制)
8. [REST API 完整参考](#8-rest-api-完整参考)
9. [任务（Job）生命周期](#9-任务job生命周期)
10. [完整 Electron 集成示例](#10-完整-electron-集成示例)
11. [常见问题与注意事项](#11-常见问题与注意事项)

---

## 1. 架构概览

```
Electron 主进程
  └─ spawn  kb-desktop-daemon.exe
               │  stdout → JSON 启动信息（port / token）
               │  .env   → 配置来源（可由 Electron 动态生成）
               ▼
         FastAPI / uvicorn HTTP Server
               │  127.0.0.1:<随机端口>
               ▼
    ┌──────────────────────────────┐
    │  SQLite  (kb.sqlite3)        │  文档、分块、任务元数据
    │  ChromaDB (chroma/)          │  向量索引
    │  Blob Store (blobs/)         │  原始文件二进制
    └──────────────────────────────┘
               │
         LLM / Embedding
         ollama 或 OpenAI 兼容接口
```

Daemon 是一个**本地 HTTP 服务**，Electron 渲染进程通过 `fetch` / `axios` 调用其 REST API 即可，**无需任何 IPC 桥接**。

---

## 2. 发布产物说明

构建命令（在项目根目录执行）：

```powershell
# 1. 编译前端 UI 并复制到 daemon static 目录
.\scripts\build_desktop.ps1

# 2. 打包 daemon exe（onedir 模式）
pyinstaller -y apps/kb_desktop_daemon/build/pyinstaller.spec
```

产物结构：

```
dist/
└── kb-desktop-daemon/          ← 整个目录需随 Electron 一起发布
    ├── kb-desktop-daemon.exe   ← 主入口可执行文件
    ├── _internal/              ← Python 运行时与依赖（PyInstaller onedir）
    └── kb_desktop_daemon/
        └── static/             ← 内嵌的管理 UI（React 构建产物）
```

> **重要**：必须将 `kb-desktop-daemon/` **整个目录**打包进 Electron asar/resources，
> 不可只打包单个 `.exe`，否则运行时找不到依赖。

在 `electron-builder` 中的典型配置：

```json
{
  "extraResources": [
    {
      "from": "dist/kb-desktop-daemon",
      "to": "kb-desktop-daemon",
      "filter": ["**/*"]
    }
  ]
}
```

运行时在主进程中解析可执行文件路径：

```js
const path = require('path');
const { app } = require('electron');

function getDaemonExePath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'kb-desktop-daemon', 'kb-desktop-daemon.exe');
  }
  // 开发模式：直接使用 dist 目录
  return path.join(__dirname, '../../dist/kb-desktop-daemon/kb-desktop-daemon.exe');
}
```

---

## 3. 环境配置（.env）

Daemon 启动时会自动从**工作目录**中加载 `.env` 文件。Electron 主进程应在 `spawn` 前将 `.env` 写入 Daemon 的工作目录（或通过 `env` 参数传入环境变量）。

### 完整配置项说明

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `APP_HOST` | `127.0.0.1` | 监听地址，本地部署保持默认即可 |
| `APP_PORT` | `0` | 监听端口；`0` 表示自动选择空闲端口（**推荐**） |
| `APP_DATA_DIR` | `./data` | 数据目录（SQLite / ChromaDB / Blobs），**最重要的配置项** |
| `AUTH_TOKEN` | _(空)_ | 固定 Bearer Token；留空则每次启动随机生成 |
| `LLM_PROVIDER` | `ollama` | LLM 后端，可选 `ollama` \| `open_compat` |
| `EMBEDDING_PROVIDER` | `ollama` | Embedding 后端，可选 `ollama` \| `open_compat` |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama 服务地址 |
| `OLLAMA_LLM_MODEL` | `qwen2.5:7b-instruct` | Ollama LLM 模型名 |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama Embedding 模型名 |
| `OPEN_COMPAT_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址 |
| `OPEN_COMPAT_API_KEY` | `YOUR_KEY` | API Key |
| `OPEN_COMPAT_LLM_MODEL` | `gpt-4o-mini` | OpenAI 兼容 LLM 模型名 |
| `OPEN_COMPAT_EMBED_MODEL` | `text-embedding-3-small` | OpenAI 兼容 Embedding 模型名 |
| `RETRIEVE_TOP_K` | `10` | 默认检索返回条数 |
| `CHUNK_SIZE` | `800` | 文档分块大小（字符数） |
| `CHUNK_OVERLAP` | `120` | 分块重叠大小（字符数） |
| `DAEMON_STATE_DIR` | `~/.openwork/kb` | daemon 运行时状态文件目录 |

### 由 Electron 动态生成 .env 示例

```js
const fs = require('fs');
const path = require('path');

function writeDaemonEnv(dataDir, options = {}) {
  const lines = [
    `APP_HOST=127.0.0.1`,
    `APP_PORT=0`,
    `APP_DATA_DIR=${dataDir}`,
    `AUTH_TOKEN=${options.authToken || ''}`,
    `LLM_PROVIDER=${options.llmProvider || 'ollama'}`,
    `EMBEDDING_PROVIDER=${options.embeddingProvider || 'ollama'}`,
    `OLLAMA_BASE_URL=${options.ollamaBaseUrl || 'http://127.0.0.1:11434'}`,
    `OLLAMA_LLM_MODEL=${options.ollamaLlmModel || 'qwen2.5:7b-instruct'}`,
    `OLLAMA_EMBED_MODEL=${options.ollamaEmbedModel || 'nomic-embed-text'}`,
  ];
  fs.writeFileSync(path.join(dataDir, '.env'), lines.join('\n'), 'utf-8');
}
```

---

## 4. 数据目录与数据库

数据目录由 `APP_DATA_DIR` 控制（绝对路径或相对于工作目录的路径），**建议配置为绝对路径**以避免因工作目录变化导致数据丢失。

```
<APP_DATA_DIR>/
├── kb.sqlite3      ← SQLite：集合/文档/分块/任务元数据
├── chroma/         ← ChromaDB 向量索引
└── blobs/          ← 原始文件二进制（PDF、DOCX、TXT 等）
```

### 推荐数据目录位置

| 场景 | 推荐路径（Node.js） |
|---|---|
| 用户数据（跨版本保留） | `app.getPath('userData') + '/kb-data'` |
| 可移动项目目录 | 用户自选目录（通过 `dialog.showOpenDialog`） |
| 开发调试 | `path.join(__dirname, '../../data')` |

```js
const { app } = require('electron');
const dataDir = path.join(app.getPath('userData'), 'kb-data');
```

### 数据目录迁移

若需要让用户迁移数据目录，只需：

1. 停止 Daemon 进程
2. 将旧 `<APP_DATA_DIR>/` 整个目录复制/移动到新路径
3. 更新 `.env` 中的 `APP_DATA_DIR`
4. 重启 Daemon

---

## 5. 在 Electron 中启动 Daemon

Daemon 是一个**控制台进程**，在主进程中使用 `child_process.spawn` 启动。

```js
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let daemonProcess = null;
let daemonInfo = null; // { port, token, base_url }

async function startDaemon(dataDir) {
  const exePath = getDaemonExePath();    // 见第 2 节
  const envFilePath = path.join(dataDir, '.env');

  // 确保数据目录存在
  fs.mkdirSync(dataDir, { recursive: true });

  // 写入配置（如需动态配置）
  writeDaemonEnv(dataDir);              // 见第 3 节

  return new Promise((resolve, reject) => {
    daemonProcess = spawn(exePath, [], {
      cwd: dataDir,        // 工作目录设为数据目录，确保 .env 被正确读取
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,   // Windows 下隐藏控制台窗口
    });

    let stdout = '';

    daemonProcess.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
      // Daemon 启动后会输出一行 JSON
      const newlineIdx = stdout.indexOf('\n');
      if (newlineIdx !== -1) {
        const line = stdout.slice(0, newlineIdx).trim();
        try {
          daemonInfo = JSON.parse(line);
          resolve(daemonInfo);
        } catch (e) {
          reject(new Error('Daemon 启动输出解析失败: ' + line));
        }
      }
    });

    daemonProcess.stderr.on('data', (data) => {
      console.error('[daemon stderr]', data.toString());
    });

    daemonProcess.on('error', reject);

    daemonProcess.on('exit', (code) => {
      console.warn('[daemon] 进程退出，退出码:', code);
      daemonProcess = null;
      daemonInfo = null;
    });

    // 启动超时保护
    setTimeout(() => reject(new Error('Daemon 启动超时')), 15000);
  });
}

function stopDaemon() {
  if (daemonProcess) {
    daemonProcess.kill();
    daemonProcess = null;
    daemonInfo = null;
  }
}
```

### 生命周期挂钩

```js
app.whenReady().then(async () => {
  try {
    daemonInfo = await startDaemon(path.join(app.getPath('userData'), 'kb-data'));
    console.log('Daemon 已启动:', daemonInfo.base_url);
    createWindow();
  } catch (err) {
    console.error('Daemon 启动失败:', err);
    app.quit();
  }
});

app.on('will-quit', () => {
  stopDaemon();
});
```

---

## 6. 获取运行时端口与 Token

Daemon 成功启动后，会通过两种方式暴露运行时信息：

### 方式一：stdout 首行 JSON（推荐）

Daemon 启动后立即向 stdout 输出一行 JSON，这是 Electron 获取端口和 Token 的**最快方式**：

```json
{"port": 54321, "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "base_url": "http://127.0.0.1:54321"}
```

上面第 5 节的 `startDaemon` 示例已经处理了该逻辑，`daemonInfo` 即为该对象。

### 方式二：状态文件（持久化）

Daemon 同时将运行时信息写入状态文件（路径由 `DAEMON_STATE_DIR` 控制，默认 `~/.openwork/kb/daemon.json`）：

```json
{
  "port": 54321,
  "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "base_url": "http://127.0.0.1:54321"
}
```

可用于进程崩溃后恢复连接，或在 Daemon 独立运行时由外部进程读取。

```js
const os = require('os');

function readDaemonState() {
  const statePath = path.join(os.homedir(), '.openwork', 'kb', 'daemon.json');
  if (!fs.existsSync(statePath)) return null;
  return JSON.parse(fs.readFileSync(statePath, 'utf-8'));
}
```

### 方式三：本地 Session 接口

若仅能访问 HTTP（例如从渲染进程），可调用无需鉴权的 Session 接口（**仅 localhost 可访问**）：

```
GET http://127.0.0.1:<port>/api/v1/session
```

```js
const res = await fetch(`http://127.0.0.1:${port}/api/v1/session`);
const { token } = await res.json();
```

---

## 7. 认证机制

所有 `/api/v1/*` 接口均需要 `Authorization` 请求头，格式为：

```
Authorization: Bearer <token>
```

> 例外：`GET /healthz` 和 `GET /api/v1/session` 不需要鉴权。

建议在 Electron 主进程通过 IPC 将 `{ baseUrl, token }` 传递给渲染进程，再由渲染进程在所有 API 请求中携带。

```js
// 主进程（main.js）
ipcMain.handle('get-daemon-info', () => daemonInfo);

// 渲染进程（preload.js）
contextBridge.exposeInMainWorld('daemon', {
  getInfo: () => ipcRenderer.invoke('get-daemon-info'),
});

// 渲染进程（app.js）
const { baseUrl, token } = await window.daemon.getInfo();

async function apiFetch(path, options = {}) {
  return fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
}
```

---

## 8. REST API 完整参考

**Base URL**: `http://127.0.0.1:<port>`

所有请求体和响应体均为 JSON，`/api/v1/ingest/upload` 使用 `multipart/form-data`。

---

### 8.1 健康检查

#### `GET /healthz`

无需鉴权。可用于轮询等待 Daemon 就绪。

**响应 200**
```json
{ "status": "ok" }
```

**用途**: 在 `startDaemon` 解析到端口后，建议继续轮询此接口直到返回 200，再初始化渲染进程。

---

### 8.2 能力查询

#### `GET /api/v1/capabilities`

查询当前 Daemon 支持的解析器、Provider 和特性开关。

**响应 200**
```json
{
  "parsers": ["text", "pdf", "docx"],
  "providers": {
    "llm": ["ollama", "open_compat"],
    "embedding": ["ollama", "open_compat"]
  },
  "features": {
    "retrieve": true,
    "ingest_upload": true,
    "metadata_filter_equals": true,
    "list_collection_documents": true,
    "view_document_original": true,
    "view_document_chunks": true
  }
}
```

---

### 8.3 知识库集合（Collection）

集合是文档的逻辑分组，每个文档必须归属于一个集合。

#### `POST /api/v1/collections` — 创建集合

**请求体**
```json
{
  "name": "我的项目文档",
  "description": "可选描述",
  "settings": {}
}
```

**响应 200**
```json
{
  "id": "uuid-string",
  "name": "我的项目文档",
  "description": "可选描述",
  "settings": {},
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

#### `GET /api/v1/collections` — 列出集合

**Query 参数**

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `limit` | int | 50 | 最多返回条数（1–500） |
| `offset` | int | 0 | 分页偏移 |

**响应 200** — 集合对象数组

---

#### `GET /api/v1/collections/{collection_id}` — 获取单个集合

**响应 200** — 集合对象，404 表示不存在

---

#### `DELETE /api/v1/collections/{collection_id}` — 删除集合

**响应 200**
```json
{ "ok": true }
```

---

#### `GET /api/v1/collections/{collection_id}/documents` — 列出集合内文档

**Query 参数**

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `limit` | int | 200 | 最多返回条数（1–2000） |
| `offset` | int | 0 | 分页偏移 |

**响应 200**
```json
{
  "collection": { "id": "...", "name": "..." },
  "documents": [
    {
      "id": "uuid",
      "collection_id": "...",
      "filename": "report.pdf",
      "mime": "application/pdf",
      "metadata": {},
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "limit": 200,
  "offset": 0
}
```

---

### 8.4 文档管理

#### `POST /api/v1/ingest/upload` — 上传并导入文档

使用 `multipart/form-data`，**不可**设置 `Content-Type: application/json`。

**表单字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | ✅ | 要上传的文件（支持 `.txt` `.pdf` `.docx`） |
| `collection_id` | string | ✅ | 目标集合 ID |
| `options` | string (JSON) | ❌ | 导入选项（见下方） |

**`options` JSON 字段**（均为可选，不传则使用 `.env` 中配置的默认值）

```json
{
  "chunk_size": 800,
  "chunk_overlap": 120,
  "parser_name": "pdf",
  "metadata": { "source": "internal", "year": 2024 }
}
```

**响应 200**（导入任务已加入队列，异步执行）
```json
{
  "job_id": "uuid-of-the-job",
  "document_id": "uuid-of-the-document"
}
```

**JavaScript 示例**
```js
async function uploadDocument(collectionId, file) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('collection_id', collectionId);
  formData.append('options', JSON.stringify({ chunk_size: 800 }));

  const res = await fetch(`${baseUrl}/api/v1/ingest/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  });
  return res.json(); // { job_id, document_id }
}
```

---

#### `DELETE /api/v1/documents/{document_id}` — 删除文档

异步任务，从向量库和数据库中彻底移除文档及其所有分块。

**响应 200**
```json
{ "job_id": "uuid-of-the-delete-job" }
```

---

#### `GET /api/v1/documents/{document_id}/original` — 查看文档解析原文

**响应 200**
```json
{
  "document": { "id": "...", "filename": "..." },
  "text": "文档解析后的纯文本内容...",
  "parse_metadata": {}
}
```

---

#### `GET /api/v1/documents/{document_id}/chunks` — 查看文档分块

**Query 参数**: `limit`（默认 200）、`offset`（默认 0）

**响应 200**
```json
{
  "document": { "id": "...", "filename": "..." },
  "chunks": [
    { "id": "...", "document_id": "...", "text": "...", "index": 0 }
  ],
  "limit": 200,
  "offset": 0
}
```

---

### 8.5 检索（RAG 核心）

#### `POST /api/v1/retrieve` — 语义检索

**请求体**
```json
{
  "query": "如何申请年假？",
  "collection_ids": ["collection-uuid-1", "collection-uuid-2"],
  "top_k": 10,
  "filters": { "year": 2024 },
  "include_chunks": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `query` | string | ✅ | 检索问题 |
| `collection_ids` | string[] | ✅ | 目标集合 ID 列表（可多集合检索） |
| `top_k` | int | ❌ | 返回最多匹配条数，默认取 `RETRIEVE_TOP_K` |
| `filters` | object | ❌ | 元数据等值过滤（key-value 对），null 表示不过滤 |
| `include_chunks` | bool | ❌ | 是否在结果中包含分块文本，默认 `true` |

**响应 200**
```json
{
  "chunks": [
    {
      "chunk": { "id": "...", "text": "...", "document_id": "..." },
      "document": { "id": "...", "filename": "..." },
      "score": 0.87
    }
  ]
}
```

---

### 8.6 任务（Job）查询

上传和删除操作均为**异步任务**，可通过以下接口轮询状态。

#### `GET /api/v1/jobs` — 列出任务

**Query 参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| `status` | string | 过滤状态：`queued` \| `running` \| `done` \| `failed` |
| `limit` | int | 默认 50，最大 500 |
| `offset` | int | 默认 0 |

---

#### `GET /api/v1/jobs/{job_id}` — 获取任务详情

**响应 200**
```json
{
  "id": "uuid",
  "type": "ingest",
  "status": "done",
  "progress": 100,
  "error": null,
  "payload": { "collection_id": "...", "document_id": "...", "filename": "report.pdf" },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:01Z"
}
```

**`status` 枚举值**

| 值 | 含义 |
|---|---|
| `queued` | 等待执行 |
| `running` | 正在执行 |
| `done` | 成功完成 |
| `failed` | 执行失败（查看 `error` 字段） |

---

## 9. 任务（Job）生命周期

上传/删除文档后应**轮询任务状态**以确认完成，建议间隔 1–2 秒。

```js
async function waitForJob(jobId, { interval = 1500, timeout = 120000 } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const res = await apiFetch(`/api/v1/jobs/${jobId}`);
    const job = await res.json();

    if (job.status === 'done') return job;
    if (job.status === 'failed') throw new Error(`任务失败: ${job.error}`);

    await new Promise(r => setTimeout(r, interval));
  }
  throw new Error('任务等待超时');
}

// 使用示例
const { job_id, document_id } = await uploadDocument(collectionId, file);
await waitForJob(job_id);
console.log('文档已成功导入，document_id:', document_id);
```

---

## 10. 完整 Electron 集成示例

下面是一个简洁的完整集成流程（`main.js`）：

```js
const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let daemonProcess = null;
let daemonInfo = null;

// ── 路径 ────────────────────────────────────────────────────────────────────
function getDaemonExePath() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'kb-desktop-daemon', 'kb-desktop-daemon.exe')
    : path.join(__dirname, '../dist/kb-desktop-daemon/kb-desktop-daemon.exe');
}

function getDataDir() {
  return path.join(app.getPath('userData'), 'kb-data');
}

// ── 启动 Daemon ──────────────────────────────────────────────────────────────
async function startDaemon() {
  const dataDir = getDataDir();
  fs.mkdirSync(dataDir, { recursive: true });

  // 如果不存在 .env，则创建默认配置
  const envPath = path.join(dataDir, '.env');
  if (!fs.existsSync(envPath)) {
    fs.writeFileSync(envPath, [
      `APP_HOST=127.0.0.1`,
      `APP_PORT=0`,
      `APP_DATA_DIR=${dataDir}`,
      `AUTH_TOKEN=`,
      `LLM_PROVIDER=ollama`,
      `EMBEDDING_PROVIDER=ollama`,
      `OLLAMA_BASE_URL=http://127.0.0.1:11434`,
      `OLLAMA_LLM_MODEL=qwen2.5:7b-instruct`,
      `OLLAMA_EMBED_MODEL=nomic-embed-text`,
    ].join('\n'), 'utf-8');
  }

  return new Promise((resolve, reject) => {
    daemonProcess = spawn(getDaemonExePath(), [], {
      cwd: dataDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });

    let buf = '';
    daemonProcess.stdout.on('data', (chunk) => {
      buf += chunk.toString();
      const nl = buf.indexOf('\n');
      if (nl !== -1) {
        try {
          daemonInfo = JSON.parse(buf.slice(0, nl).trim());
          resolve(daemonInfo);
        } catch (e) {
          reject(e);
        }
      }
    });

    daemonProcess.on('error', reject);
    setTimeout(() => reject(new Error('Daemon 启动超时')), 15000);
  });
}

// ── 等待 Daemon 就绪 ─────────────────────────────────────────────────────────
async function waitDaemonReady(baseUrl, retries = 20) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`${baseUrl}/healthz`);
      if (res.ok) return;
    } catch (_) {}
    await new Promise(r => setTimeout(r, 500));
  }
  throw new Error('Daemon 健康检查失败');
}

// ── IPC ──────────────────────────────────────────────────────────────────────
ipcMain.handle('daemon:info', () => daemonInfo);

// ── 主流程 ───────────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  daemonInfo = await startDaemon();
  await waitDaemonReady(daemonInfo.base_url);

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: { preload: path.join(__dirname, 'preload.js') },
  });
  win.loadURL('http://localhost:5173'); // 或 loadFile('index.html')
});

app.on('will-quit', () => {
  daemonProcess?.kill();
});
```

---

## 11. 常见问题与注意事项

### Q1: 端口每次启动都不同，如何管理？

`APP_PORT=0` 会自动选择空闲端口，这是**推荐做法**，避免端口冲突。端口在每次进程启动时通过 stdout JSON 或状态文件获取，Electron 主进程应在启动后缓存 `daemonInfo` 并通过 IPC 下发给渲染进程。

若需要固定端口，在 `.env` 中设置 `APP_PORT=54321`。

---

### Q2: Windows 下 .js 文件 MIME 类型错误

在某些 Windows 环境中，注册表可能将 `.js` 映射为 `text/plain`，导致浏览器报错 `Failed to load module script`。Daemon 内部已通过 `mimetypes.add_type` 修复，无需额外处理。

---

### Q3: Auth Token 如何持久化？

若希望 Token 跨重启保持不变（方便调试或外部工具集成），在 `.env` 中设置：

```
AUTH_TOKEN=your_fixed_token_here
```

否则每次启动会随机生成新 Token，**Electron 每次重启时均需重新从 stdout 获取**。

---

### Q4: 如何让用户自定义数据目录？

1. 通过 `dialog.showOpenDialog({ properties: ['openDirectory'] })` 让用户选择目录
2. 更新 `.env` 文件中的 `APP_DATA_DIR` 为用户选择的绝对路径
3. 重启 Daemon

---

### Q5: Daemon 意外退出如何处理？

```js
daemonProcess.on('exit', (code, signal) => {
  console.warn(`Daemon 退出 code=${code} signal=${signal}`);
  // 通知渲染进程
  BrowserWindow.getAllWindows().forEach(w =>
    w.webContents.send('daemon:exit', { code, signal })
  );
  // 可选：自动重启
  // startDaemon().catch(console.error);
});
```

---

### Q6: 支持哪些文档格式？

通过 `/api/v1/capabilities` 动态查询，当前版本支持：

| 格式 | MIME 类型 | 说明 |
|---|---|---|
| `.txt` | `text/plain` | 纯文本 |
| `.pdf` | `application/pdf` | PDF 文档 |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Word 文档 |

---

### Q7: 可以同时使用多个数据目录吗？

当前版本每个 Daemon 实例只对应一个数据目录。若需要支持多个独立知识库，需启动**多个 Daemon 实例**，分别使用不同的 `APP_DATA_DIR` 和端口。

---

*文档生成日期: 2025年2月*
