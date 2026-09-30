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
  const targets={[beachName]:{href:"#collect",label:"Plaj verilerini aç"},
    "nws-weather":{href:"#collect/weather",label:"Hava verilerini aç"},
    "south-walton-restaurants":{href:"#collect/restaurants",label:"Restoran verilerini aç"}};
  return Object.hasOwn(targets,name)?targets[name]:null;
}

export function collectionTabs(selected="beaches") {
  if(typeof selected==="boolean") selected=selected?"weather":"beaches";
  return `<nav class="filter-row" aria-label="Veri türü">${[["beaches","#collect","Plaj erişimleri"],["weather","#collect/weather","Hava"],["restaurants","#collect/restaurants","Restoranlar"]].map(([id,href,label])=>`<a class="tab ${selected===id?"active":""}" href="${href}" ${selected===id?'aria-current="page"':""}>${label}</a>`).join("")}</nav>`;
}
