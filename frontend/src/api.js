const API = import.meta.env.VITE_API_URL || "";

export async function createSession() {
  const response = await fetch(`${API}/api/sessions`, { method: "POST" });
  if (!response.ok) throw new Error("Could not create a session");
  return response.json();
}

export async function uploadFiles(sessionId, files) {
  const body = new FormData();
  body.append("session_id", sessionId);
  for (const file of files) body.append("files", file);
  const response = await fetch(`${API}/api/upload`, { method: "POST", body });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Upload failed");
  return data;
}

export async function chat(sessionId, message) {
  const response = await fetch(`${API}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Chat failed");
  return data;
}

export async function getKpis(sessionId) {
  const response = await fetch(
    `${API}/api/kpis/${encodeURIComponent(sessionId)}`
  );
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Could not load dashboard KPIs");
  }
  return data;
}
