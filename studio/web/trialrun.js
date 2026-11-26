import {api, esc, date} from "./api.js";

// HEDEF-01: Veri → Okuma denemeleri → "Deneme çekimi". Every collector once, small (two listings of each rental company and one week),
// on the real sites and with the workers, in the program's own copy of the database: the result never mixes with the real data.
// The table says per collector whether it was read, and per rental company through which worker (doğrudan, proxy N, programın
// tarayıcısı, eklenti) and the error.

const STATE_TAGS={done:"green",failed:"warm",canceled:"warm",interrupted:"warm",skipped:"warm"};
const COMPANY_TAGS={done:"green"};

function seconds(value) {
  if(value==null) return "—";
  return value<90?`${value} sn`:`${Math.round(value/60)} dk`;
}

/** The rental companies of a trial: read or not, through which worker, the error. */
export function companyTable(rows) {
  if(!rows?.length) return "";
  return `<div class="table-scroll"><table class="reference-table trial-companies"><thead><tr><th>ŞİRKET</th><th>SONUÇ</th><th>İLAN / EŞLENEN / FİYAT</th><th>İŞÇİ</th><th>NOT</th></tr></thead><tbody>
    ${rows.map(r=>`<tr><td><strong>${esc(r.sirket)}</strong><small class="source-host">${esc(r.alan_adi)}</small></td><td><span class="tag ${COMPANY_TAGS[r.durum] ?? "warm"}">${esc(r.durum_metni)}</span></td>
      <td>${esc(r.ilan ?? 0)} / ${esc(r.eslenen ?? 0)} / ${esc(r.fiyat ?? 0)}</td><td>${esc((r.isciler||[]).join(", ") || "—")}</td><td>${esc(r.mesaj || "")}</td></tr>`).join("")}
    </tbody></table></div>`;
}

/** The trial section: what it does, the button, the running job's line and the last result table. */
export function trialSection(view, {message=""}={}) {
  const last=view?.son, running=view?.calisan;
  const limits=view?.sinirlar||{};
  const rows=(last?.toplayicilar||[]).map(r=>`<tr><td><strong>${esc(r.kaynak)}</strong><small class="source-host">${esc(r.toplayici)}</small></td>
    <td><span class="tag ${STATE_TAGS[r.durum] ?? ""}">${esc(r.durum_metni || r.durum)}</span></td><td>${esc(r.kayit ?? "—")}</td><td>${esc(seconds(r.sure_s))}</td><td>${esc(r.mesaj || "")}</td></tr>`).join("");
  const agency=(last?.toplayicilar||[]).find(r=>r.sirketler?.length);
  const events=(agency?.olaylar||[]).map(e=>`<li>${esc(e.metin)}</li>`).join("");
  const table=last?`<h3>Son deneme çekimi</h3><p class="muted">${esc(date(last.baslangic))} – ${esc(date(last.bitis))} · kopya: data/${esc(last.klasor)}</p>
    <div class="table-scroll"><table class="reference-table trial-table"><thead><tr><th>TOPLAYICI</th><th>SONUÇ</th><th>KAYIT</th><th>SÜRE</th><th>NOT</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${agency?`<h3>Kiralama şirketleri</h3>${companyTable(agency.sirketler)}`:""}${events?`<details><summary>Sitenin korunması ve işçi olayları</summary><ul>${events}</ul></details>`:""}`
    :'<p class="muted">Henüz deneme çekimi yapılmadı.</p>';
  return `<section class="info-card trial-run" id="deneme-cekimi"><span class="eyebrow">DENEME ÇEKİMİ</span><h2 style="margin-top:12px">Deneme çekimi</h2>
    <p>Bütün toplayıcıları gerçek sitelerde, işçilerle ve küçük ölçekte bir kez çalıştırır: her kiralama şirketinden ${esc(limits.listings ?? 2)} ilan ve tek hafta, Book>Direct'ten tek hafta ve ${esc(limits.calendars ?? 5)} fiyat takvimi, ${esc(limits.restaurants ?? 3)} restoranın sitesi; öbür toplayıcılar zaten küçüktür, tamamı çalışır. Çekim programın aldığı veritabanı kopyasında yapılır; sonuç gerçek veriye karışmaz. Uzun çekimden önce her parçanın çalıştığını gösterir.</p>
    <div class="decision-actions"><button type="button" class="primary" id="trial-run-start"${running?" disabled":""}>Deneme çekimini başlat</button>
    ${running?`<small class="muted">Sürüyor: ${esc(running.message || "")} (İşler panelinde)</small>`:'<small class="muted">Chrome ve eklenti açık olmalı; doğrulama çıkarsa en sonda 15 dakika beklenir.</small>'}</div>
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
    ${table}
  </section>`;
}

export class TrialRunSection {
  constructor(container) {this.container=container;this.view=null;this.message="";}
  async load(message="") {
    try {this.view=await api("deneme-cekimi");this.message=message;this.draw();}
    catch(error) {if(!error.stale) this.container.textContent=error.message;}
  }
  draw() {
    this.container.innerHTML=trialSection(this.view,{message:this.message});
    this.container.querySelector("#trial-run-start")?.addEventListener("click",()=>this.start());
  }
  async start() {
    try {await api("deneme-cekimi",{method:"POST",body:"{}"});await this.load("Deneme çekimi başladı; ilerlemesi İşler panelinde.");}
    catch(error) {if(error.stale) return;this.message=error.message;this.draw();}
  }
}
