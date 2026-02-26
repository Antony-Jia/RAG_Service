import { useEffect, useMemo, useState } from "react";

async function getSessionToken() {
  const response = await fetch("/api/v1/session");
  if (!response.ok) throw new Error("无法获取会话 token");
  const data = await response.json();
  return data.token;
}

async function apiFetch(path, token, options = {}) {
  const headers = {
    "Authorization": `Bearer ${token}`,
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

export default function App() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [collections, setCollections] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [hits, setHits] = useState([]);

  const [collectionName, setCollectionName] = useState("Default KB");
  const [collectionId, setCollectionId] = useState("");

  const [uploadFile, setUploadFile] = useState(null);
  const [query, setQuery] = useState("");

  async function refreshCollections(currentToken) {
    const data = await apiFetch("/api/v1/collections", currentToken);
    setCollections(data || []);
    if (!collectionId && data?.length) {
      setCollectionId(data[0].id);
    }
  }

  async function refreshJobs(currentToken) {
    const data = await apiFetch("/api/v1/jobs?limit=30", currentToken);
    setJobs(data || []);
  }

  useEffect(() => {
    (async () => {
      try {
        const sessionToken = await getSessionToken();
        setToken(sessionToken);
        await refreshCollections(sessionToken);
        await refreshJobs(sessionToken);
      } catch (e) {
        setError(String(e));
      }
    })();
  }, []);

  const selectedCollection = useMemo(
    () => collections.find((c) => c.id === collectionId),
    [collections, collectionId]
  );

  async function createCollection() {
    setError("");
    setSuccess("");
    try {
      const created = await apiFetch("/api/v1/collections", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: collectionName }),
      });
      await refreshCollections(token);
      setCollectionId(created.id);
      setSuccess(`Collection 已创建: ${created.name}`);
    } catch (e) {
      setError(String(e));
    }
  }

  async function ingestFile() {
    if (!uploadFile || !collectionId) return;
    setError("");
    setSuccess("");
    try {
      const form = new FormData();
      form.append("file", uploadFile);
      form.append("collection_id", collectionId);
      form.append("options", JSON.stringify({}));

      const result = await apiFetch("/api/v1/ingest/upload", token, {
        method: "POST",
        body: form,
      });
      setSuccess(`已提交 ingest job: ${result.job_id}`);
      await refreshJobs(token);
    } catch (e) {
      setError(String(e));
    }
  }

  async function runRetrieve() {
    if (!query || !collectionId) return;
    setError("");
    setSuccess("");
    try {
      const result = await apiFetch("/api/v1/retrieve", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          collection_ids: [collectionId],
          top_k: 10,
          include_chunks: true,
        }),
      });
      setHits(result.hits || []);
      setSuccess(`检索完成，命中 ${result.hits?.length || 0} 条`);
    } catch (e) {
      setError(String(e));
    }
  }

  async function deleteDocument(documentId) {
    setError("");
    setSuccess("");
    try {
      const result = await apiFetch(`/api/v1/documents/${documentId}`, token, {
        method: "DELETE",
      });
      setSuccess(`删除任务已提交: ${result.job_id}`);
      await refreshJobs(token);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="app">
      <h1>Knowledge Base Admin</h1>
      <p className="subtitle">Desktop Daemon 管理端，支持 ingest / retrieve / jobs。</p>
      {error ? <p className="error">{error}</p> : null}
      {success ? <p className="success">{success}</p> : null}

      <div className="grid">
        <section className="card">
          <h3>1) Collections</h3>
          <div className="row">
            <label>Collection Name</label>
            <input value={collectionName} onChange={(e) => setCollectionName(e.target.value)} />
            <button onClick={createCollection}>Create Collection</button>
          </div>
          <div className="row">
            <label>Active Collection</label>
            <select value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
              <option value="">请选择</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.id.slice(0, 8)})</option>
              ))}
            </select>
          </div>
          <div className="list">
            {collections.map((c) => (
              <div className="item" key={c.id}>
                <strong>{c.name}</strong>
                <small>{c.id}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3>2) Ingest Upload</h3>
          <div className="row">
            <label>Upload File (txt/md/pdf/docx)</label>
            <input type="file" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} />
            <button onClick={ingestFile} disabled={!selectedCollection || !uploadFile}>Submit Ingest</button>
          </div>
        </section>

        <section className="card">
          <h3>3) Search</h3>
          <div className="row">
            <label>Query</label>
            <textarea rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />
            <button className="secondary" onClick={runRetrieve} disabled={!query || !selectedCollection}>Retrieve</button>
          </div>
          <div className="list">
            {hits.map((h) => (
              <div className="item" key={h.chunk_id}>
                <strong>Score: {h.score.toFixed(4)}</strong>
                <small>Doc: {h.document?.title} ({h.document?.id})</small>
                <small>Citation: {h.citation?.snippet}</small>
                <button onClick={() => deleteDocument(h.document?.id)}>Delete Document</button>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3>Jobs</h3>
          <button onClick={() => refreshJobs(token)}>Refresh Jobs</button>
          <div className="list" style={{ marginTop: 10 }}>
            {jobs.map((j) => (
              <div className="item" key={j.id}>
                <strong>{j.type}</strong> <span className="status">{j.status}</span>
                <small>{j.id}</small>
                <small>progress={j.progress}</small>
                {j.message ? <small>{j.message}</small> : null}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
