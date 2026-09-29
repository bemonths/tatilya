export async function api(path, options = {}) {
  const response = await fetch(`/api/${path}`, {
    ...options,
    headers: {"Content-Type": "application/json", "X-Studio-Request": "1", ...options.headers}
  });
  const body = await response.json();
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Alanları kontrol edin. Adres https:// ile başlamalı ve seçilen değerler geçerli olmalı.";
    throw new Error(detail);
  }
  return body;
}

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
}

export function host(url) { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; } }
export function date(value) { return value ? new Date(value).toLocaleString("tr-TR", {day:"numeric", month:"short", hour:"2-digit", minute:"2-digit"}) : "—"; }
