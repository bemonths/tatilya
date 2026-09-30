/** Registry metadata controls readiness; domain screens remain explicit. */
export function connectorState(source) {
  const ready=source.connector != null;
  const method=source.connector?.method || source.method || "Belirlenecek";
  return {
    ready,
    label: !source.enabled?"Arşivde":ready?"Toplayıcı hazır":"Bağlantı bekliyor",
    method: ready?`${method === "Belirlenecek"?"Toplayıcı":method} · bağlı`:method,
  };
}

export function jobResultTarget(job, beachConnectorName="south-walton-beaches") {
  if(!job.result) return null;
  if(job.kind === "source_collection") {
    return domainTarget(job.result.connector_name, beachConnectorName);
  }
  return job.kind === "catalog_audit"?{href:"#quality",label:"Kontrol raporunu aç"}:null;
}

export function domainTarget(name, beachName="south-walton-beaches") {
  if(name === beachName) return {href:"#collect",label:"Plaj verilerini aç"};
  if(name === "nws-weather") return {href:"#collect/weather",label:"Hava verilerini aç"};
  return null;
}

export function collectionTabs(weather=false) {
  return `<nav class="filter-row" aria-label="Veri türü"><a class="tab ${!weather?"active":""}" href="#collect" ${!weather?'aria-current="page"':""}>Plaj erişimleri</a><a class="tab ${weather?"active":""}" href="#collect/weather" ${weather?'aria-current="page"':""}>Hava</a></nav>`;
}
