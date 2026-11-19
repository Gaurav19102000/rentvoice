const BASE = import.meta.env.VITE_API_URL || "";

async function request(path, { method = "GET", body, headers = {} } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d) => d.msg.replace("Value error, ", "")).join(". ")
      : data.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  config: () => request("/api/config"),
  createRequest: (body) => request("/api/requests", { method: "POST", body }),
  getRequest: (id) => request(`/api/requests/${id}`),
  callVariables: (id) => request(`/api/requests/${id}/call-variables`),
  attachWebCall: (id, call_id) => request(`/api/requests/${id}/web-call`, { method: "POST", body: { call_id } }),
  retryCall: (id) => request(`/api/requests/${id}/call`, { method: "POST" }),
  simulate: (id, prefs) => request(`/api/dev/simulate/${id}`, { method: "POST", body: prefs }),
  getChat: (t) => request(`/api/chat/${t}`),
  sendChat: (t, content) => request(`/api/chat/${t}/messages`, { method: "POST", body: { content } }),
  select: (t, property_id) => request(`/api/chat/${t}/select`, { method: "POST", body: { property_id } }),
  admin: (token) => {
    const h = { "x-admin-token": token };
    return {
      properties: () => request("/api/admin/properties", { headers: h }),
      requests: () => request("/api/admin/requests", { headers: h }),
      create: (body) => request("/api/admin/properties", { method: "POST", body, headers: h }),
      verify: (id) => request(`/api/admin/properties/${id}/verify`, { method: "POST", headers: h }),
      toggle: (id) => request(`/api/admin/properties/${id}/toggle`, { method: "POST", headers: h }),
    };
  },
};

export const rupees = (n) => `₹${Number(n).toLocaleString("en-IN")}`;
