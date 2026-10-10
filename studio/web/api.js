let selectedDestination=null;
let revision=0;
export function setDestination(id) { selectedDestination=id; return ++revision; }
export function destinationRevision() { return revision; }
export function destinationPath(path) {
  return selectedDestination ? `${path}${path.includes('?')?'&':'?'}destination_id=${encodeURIComponent(selectedDestination)}` : path;
}
export class StaleDestinationResponse extends Error { constructor(){super('');this.stale=true;} }
export async function api(path, options = {}) {
  const requestRevision=revision;
  if(options.body && ["sources","jobs","evidence-packs","claude/title-runs"].includes(path) && selectedDestination) {
    options={...options,body:JSON.stringify({...JSON.parse(options.body),destination_id:selectedDestination})};
  }
  const response = await fetch(`/api/${destinationPath(path)}`, {
    ...options,
    headers: {"Content-Type": "application/json", "X-Studio-Request": "1", ...options.headers}
  });
  const body = await response.json();
  if(requestRevision!==revision) throw new StaleDestinationResponse();
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Alanları kontrol edin. Adres https:// ile başlamalı ve seçilen değerler geçerli olmalı.";
    const error=new Error(detail);error.status=response.status;throw error;
  }
  return body;
}

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
}

export function host(url) { try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; } }
export function date(value) { return value ? new Date(value).toLocaleString("tr-TR", {day:"numeric", month:"short", hour:"2-digit", minute:"2-digit"}) : "—"; }

// GÖREV-14: the shutdown watchdog closes the server when the window is gone; the window says it is alive every 10 s.
export function startHeartbeat(interval=10000) {
  const beat=()=>fetch("/api/heartbeat",{method:"POST",headers:{"X-Studio-Request":"1"}}).catch(()=>{});
  beat();
  return setInterval(beat,interval);
}
