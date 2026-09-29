/** Registry metadata controls readiness; domain screens remain explicit. */
export function connectorState(source) {
  const ready=source.connector != null;
  const method=source.method || "Belirlenecek";
  return {
    ready,
    label: !source.enabled?"Arşivde":ready?"Toplayıcı hazır":"Bağlantı bekliyor",
    method: ready?`${method === "Belirlenecek"?"Toplayıcı":method} · bağlı`:method,
  };
}

export function jobResultTarget(job, beachConnectorName) {
  if(!job.result) return null;
  if(job.kind === "source_collection") {
    return job.result.connector_name === beachConnectorName
      ? {href:"#collect",label:"Toplanan verileri aç"} : null;
  }
  return job.kind === "catalog_audit"?{href:"#quality",label:"Kontrol raporunu aç"}:null;
}
