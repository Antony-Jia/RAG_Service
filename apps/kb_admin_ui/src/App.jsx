import { useCallback, useEffect, useState } from "react";

async function getSessionToken() {
  const response = await fetch("/api/v1/session");
  if (!response.ok) throw new Error("无法获取会话 token");
  const data = await response.json();
  return data.token;
}

async function apiFetch(path, token, options = {}) {
  const headers = {
    Authorization: `Bearer ${token}`,
    ...(options.headers || {}),
  };
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

const NAV = [
  { key: "collections", label: "Collections", icon: "🗂️" },
  { key: "ingest", label: "Ingest", icon: "📤" },
  { key: "documents", label: "Documents", icon: "📄" },
  { key: "search", label: "Search", icon: "🔍" },
  { key: "jobs", label: "Jobs", icon: "⚙️" },
];

function StatusBadge({ status }) {
  const cls = { queued: "badge-blue", running: "badge-yellow", done: "badge-green", failed: "badge-red" };
  return <span className={`badge ${cls[status] || "badge-grey"}`}>{status}</span>;
}

function Toast({ message, type, onClose }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [message, onClose]);
  if (!message) return null;
  return (
    <div className={`toast toast-${type}`}>
      <span>{message}</span>
      <button className="toast-close" onClick={onClose}>×</button>
    </div>
  );
}

function CollectionsPage({ token, collections, onRefresh, notify }) {
  const [name, setName] = useState("Default KB");
  const [creating, setCreating] = useState(false);

  async function create() {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await apiFetch("/api/v1/collections", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      });
      notify("Collection 创建成功", "success");
      await onRefresh();
    } catch (e) {
      notify(String(e), "error");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Collections</h2>
        <div className="toolbar">
          <input
            className="input-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Collection name"
          />
          <button className="btn btn-primary" onClick={create} disabled={creating}>
            {creating ? "Creating..." : "+ New Collection"}
          </button>
        </div>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>ID</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          {collections.length === 0 ? (
            <tr><td colSpan={3} className="empty">暂无 Collections</td></tr>
          ) : (
            collections.map((c) => (
              <tr key={c.id}>
                <td><strong>{c.name}</strong></td>
                <td className="monospace">{c.id}</td>
                <td>{c.description || "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function IngestPage({ token, collections, onRefreshJobs, notify }) {
  const [collectionId, setCollectionId] = useState("");
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!collectionId && collections.length) setCollectionId(collections[0].id);
  }, [collections, collectionId]);

  async function submit() {
    if (!file || !collectionId) return;
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("collection_id", collectionId);
      form.append("options", "{}");
      const r = await apiFetch("/api/v1/ingest/upload", token, { method: "POST", body: form });
      notify(`Ingest 已提交: ${r.job_id}`, "success");
      await onRefreshJobs();
      setFile(null);
    } catch (e) {
      notify(String(e), "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header"><h2>Ingest Document</h2></div>
      <div className="form-card">
        <div className="form-row">
          <label>Target Collection</label>
          <select className="select-md" value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
            <option value="">— 请选择 —</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>Upload File (txt / md / pdf / docx)</label>
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          {file && <span className="file-hint">{file.name}</span>}
        </div>
        <button
          className="btn btn-primary btn-lg"
          onClick={submit}
          disabled={!file || !collectionId || submitting}
        >
          {submitting ? "Submitting..." : "Submit Ingest Job"}
        </button>
      </div>
    </div>
  );
}

function DocumentPreviewModal({ state, onClose }) {
  if (!state.open) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{state.title}</h3>
          <button className="btn btn-outline btn-sm" onClick={onClose}>Close</button>
        </div>
        {state.type === "original" ? (
          <pre className="modal-pre">{state.text || "无原文内容"}</pre>
        ) : (
          <div className="chunk-list">
            {(state.chunks || []).length === 0 ? (
              <p className="empty">暂无分块</p>
            ) : (
              state.chunks.map((chunk) => (
                <div className="chunk-card" key={chunk.id}>
                  <div className="chunk-meta">
                    <span>#{chunk.order}</span>
                    <span>{chunk.id.slice(0, 8)}…</span>
                    <span>{chunk.token_count || 0} tokens</span>
                  </div>
                  <p>{chunk.text}</p>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentsPage({ token, collections, notify }) {
  const [collectionId, setCollectionId] = useState("");
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState({
    open: false,
    title: "",
    type: "original",
    text: "",
    chunks: [],
  });

  useEffect(() => {
    if (!collectionId && collections.length) setCollectionId(collections[0].id);
  }, [collections, collectionId]);

  const refreshDocuments = useCallback(async () => {
    if (!collectionId) {
      setDocuments([]);
      return;
    }
    setLoading(true);
    try {
      const r = await apiFetch(`/api/v1/collections/${collectionId}/documents?limit=500&offset=0`, token);
      setDocuments(r.documents || []);
    } catch (e) {
      notify(String(e), "error");
    } finally {
      setLoading(false);
    }
  }, [collectionId, notify, token]);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  async function viewOriginal(docId) {
    if (!docId) return;
    try {
      const r = await apiFetch(`/api/v1/documents/${docId}/original`, token);
      setPreview({
        open: true,
        title: `原文 - ${r.document?.title || docId}`,
        type: "original",
        text: r.text || "",
        chunks: [],
      });
    } catch (e) {
      notify(String(e), "error");
    }
  }

  async function viewChunks(docId) {
    if (!docId) return;
    try {
      const r = await apiFetch(`/api/v1/documents/${docId}/chunks?limit=500&offset=0`, token);
      setPreview({
        open: true,
        title: `分块 - ${r.document?.title || docId}`,
        type: "chunks",
        text: "",
        chunks: r.chunks || [],
      });
    } catch (e) {
      notify(String(e), "error");
    }
  }

  async function deleteDoc(docId) {
    if (!docId) return;
    try {
      await apiFetch(`/api/v1/documents/${docId}`, token, { method: "DELETE" });
      notify("删除任务已提交", "success");
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (e) {
      notify(String(e), "error");
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Documents</h2>
        <div className="toolbar">
          <select className="select-md compact-select" value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
            <option value="">— 请选择 Collection —</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <button className="btn btn-outline" onClick={refreshDocuments} disabled={loading}>
            {loading ? "Loading..." : "↻ Refresh"}
          </button>
        </div>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>ID</th>
            <th>Status</th>
            <th>Mime</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {documents.length === 0 ? (
            <tr><td colSpan={5} className="empty">当前 Collection 暂无文档</td></tr>
          ) : (
            documents.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.title}</td>
                <td className="monospace">{doc.id.slice(0, 8)}…</td>
                <td>{doc.status}</td>
                <td className="monospace">{doc.mime}</td>
                <td>
                  <div className="action-group">
                    <button className="btn btn-outline btn-sm" onClick={() => viewOriginal(doc.id)}>
                      原文
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => viewChunks(doc.id)}>
                      分块
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => deleteDoc(doc.id)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      <DocumentPreviewModal
        state={preview}
        onClose={() => setPreview((prev) => ({ ...prev, open: false }))}
      />
    </div>
  );
}

function SearchPage({ token, collections, notify }) {
  const [collectionId, setCollectionId] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState([]);
  const [searching, setSearching] = useState(false);
  const [preview, setPreview] = useState({
    open: false,
    title: "",
    type: "original",
    text: "",
    chunks: [],
  });

  useEffect(() => {
    if (!collectionId && collections.length) setCollectionId(collections[0].id);
  }, [collections, collectionId]);

  async function search() {
    if (!query.trim() || !collectionId) return;
    setSearching(true);
    try {
      const r = await apiFetch("/api/v1/retrieve", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, collection_ids: [collectionId], top_k: 10, include_chunks: true }),
      });
      setHits(r.hits || []);
      notify(`检索完成，命中 ${r.hits?.length || 0} 条`, "success");
    } catch (e) {
      notify(String(e), "error");
    } finally {
      setSearching(false);
    }
  }

  async function deleteDoc(docId) {
    try {
      await apiFetch(`/api/v1/documents/${docId}`, token, { method: "DELETE" });
      notify("删除任务已提交", "success");
      setHits((prev) => prev.filter((h) => h.document?.id !== docId));
    } catch (e) {
      notify(String(e), "error");
    }
  }

  async function viewOriginal(docId) {
    if (!docId) return;
    try {
      const r = await apiFetch(`/api/v1/documents/${docId}/original`, token);
      setPreview({
        open: true,
        title: `原文 - ${r.document?.title || docId}`,
        type: "original",
        text: r.text || "",
        chunks: [],
      });
    } catch (e) {
      notify(String(e), "error");
    }
  }

  async function viewChunks(docId) {
    if (!docId) return;
    try {
      const r = await apiFetch(`/api/v1/documents/${docId}/chunks?limit=500&offset=0`, token);
      setPreview({
        open: true,
        title: `分块 - ${r.document?.title || docId}`,
        type: "chunks",
        text: "",
        chunks: r.chunks || [],
      });
    } catch (e) {
      notify(String(e), "error");
    }
  }

  return (
    <div className="page">
      <div className="page-header"><h2>Search / Retrieve</h2></div>
      <div className="form-card">
        <div className="form-row">
          <label>Collection</label>
          <select className="select-md" value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
            <option value="">— 请选择 —</option>
            {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div className="form-row">
          <label>Query</label>
          <textarea
            className="textarea-md"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入检索内容..."
          />
        </div>
        <button
          className="btn btn-secondary btn-lg"
          onClick={search}
          disabled={!query.trim() || !collectionId || searching}
        >
          {searching ? "Searching..." : "Retrieve"}
        </button>
      </div>
      {hits.length > 0 && (
        <table className="data-table" style={{ marginTop: 24 }}>
          <thead>
            <tr>
              <th>#</th>
              <th>Score</th>
              <th>Document</th>
              <th>Snippet</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {hits.map((h, i) => (
              <tr key={h.chunk_id}>
                <td>{i + 1}</td>
                <td className="monospace">{h.score.toFixed(4)}</td>
                <td>{h.document?.title || h.document?.id?.slice(0, 8)}</td>
                <td className="snippet">{h.citation?.snippet}</td>
                <td>
                  <div className="action-group">
                    <button className="btn btn-outline btn-sm" onClick={() => viewOriginal(h.document?.id)}>
                      原文
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={() => viewChunks(h.document?.id)}>
                      分块
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => deleteDoc(h.document?.id)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <DocumentPreviewModal
        state={preview}
        onClose={() => setPreview((prev) => ({ ...prev, open: false }))}
      />
    </div>
  );
}

function JobsPage({ jobs, onRefresh }) {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Jobs</h2>
        <button className="btn btn-outline" onClick={onRefresh}>↻ Refresh</button>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {jobs.length === 0 ? (
            <tr><td colSpan={5} className="empty">暂无 Jobs</td></tr>
          ) : (
            jobs.map((j) => (
              <tr key={j.id}>
                <td className="monospace">{j.id.slice(0, 8)}…</td>
                <td>{j.type}</td>
                <td><StatusBadge status={j.status} /></td>
                <td>
                  <div className="progress-wrap">
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${j.progress || 0}%` }} />
                    </div>
                    <span className="progress-text">{j.progress || 0}%</span>
                  </div>
                </td>
                <td>{j.message || "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState("");
  const [collections, setCollections] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [activeNav, setActiveNav] = useState("collections");
  const [toast, setToast] = useState({ message: "", type: "success" });
  const [loading, setLoading] = useState(true);

  const notify = useCallback((message, type = "success") => setToast({ message, type }), []);

  const refreshCollections = useCallback(async (t) => {
    const data = await apiFetch("/api/v1/collections", t || token);
    setCollections(data || []);
  }, [token]);

  const refreshJobs = useCallback(async (t) => {
    const data = await apiFetch("/api/v1/jobs?limit=30", t || token);
    setJobs(data || []);
  }, [token]);

  useEffect(() => {
    (async () => {
      try {
        const t = await getSessionToken();
        setToken(t);
        await Promise.all([refreshCollections(t), refreshJobs(t)]);
      } catch (e) {
        notify(String(e), "error");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Connecting to KB Daemon...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-icon">🧠</span>
          <span className="brand-name">KB Admin</span>
        </div>
        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <button
              key={item.key}
              className={`nav-item${activeNav === item.key ? " active" : ""}`}
              onClick={() => setActiveNav(item.key)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" />
          <span>Daemon connected</span>
        </div>
      </aside>

      <main className="main-content">
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast({ message: "", type: "success" })}
        />
        {activeNav === "collections" && (
          <CollectionsPage
            token={token}
            collections={collections}
            onRefresh={() => refreshCollections()}
            notify={notify}
          />
        )}
        {activeNav === "ingest" && (
          <IngestPage
            token={token}
            collections={collections}
            onRefreshJobs={() => refreshJobs()}
            notify={notify}
          />
        )}
        {activeNav === "documents" && (
          <DocumentsPage token={token} collections={collections} notify={notify} />
        )}
        {activeNav === "search" && (
          <SearchPage token={token} collections={collections} notify={notify} />
        )}
        {activeNav === "jobs" && (
          <JobsPage jobs={jobs} onRefresh={() => refreshJobs()} />
        )}
      </main>
    </div>
  );
}
