export class KBDaemonClient {
  constructor(private readonly baseUrl: string, private readonly token: string) {}

  private async request(path: string, options: RequestInit = {}) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${this.token}`,
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      throw new Error(`Request failed: ${res.status} ${await res.text()}`);
    }
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  }

  healthz() {
    return fetch(`${this.baseUrl}/healthz`).then((r) => r.json());
  }

  listCollections() {
    return this.request("/api/v1/collections");
  }

  retrieve(payload: {
    query: string;
    collection_ids: string[];
    top_k?: number;
    include_chunks?: boolean;
  }) {
    return this.request("/api/v1/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
}
