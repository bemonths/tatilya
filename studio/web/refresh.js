import {esc} from "./api.js";

export const STEP_LABELS={waiting:"sırada",running:"çalışıyor",done:"tamamlandı",failed:"hata",canceled:"iptal edildi",interrupted:"yarıda kaldı",skipped:"atlandı"};
export const BATCH_LABELS={running:"Sürüyor",done:"Tamamlandı",failed:"Bir kısmı tamamlanamadı",canceled:"Durduruldu",interrupted:"Yarıda kaldı"};

/** Seconds as "~3 sa 20 dk" (our estimate); unknown stays visibly unknown. */
export function duration(seconds) {
  if(seconds==null) return "bilinmiyor";
  const minutes=Math.max(1,Math.round(seconds/60));
  if(minutes<60) return `~${minutes} dk`;
  const hours=Math.floor(minutes/60), rest=minutes%60;
  return `~${hours} sa${rest?` ${rest} dk`:""}`;
}

export function trDate(value) {
  if(!value) return "—";
  const [year,month,day]=String(value).slice(0,10).split("-").map(Number);
  return new Date(Date.UTC(year,month-1,day)).toLocaleDateString("tr-TR",{day:"numeric",month:"long",year:"numeric",timeZone:"UTC"});
}

function dueTag(item) {
  if(item.interval_months==null) return '<span class="tag">aralık tanımlı değil</span>';
  if(item.due) return `<span class="tag warm">zamanı geldi</span>${item.last_done_on?"":"<small>hiç çekilmedi</small>"}`;
  return `<span class="tag green">güncel</span><small>sonraki: ${esc(trDate(item.next_due_on))}</small>`;
}

/** The home screen's "Güncelleme zamanı gelenler" section: every collector, its last successful run, the suggested interval and
 * whether it is due; one button starts the due ones in order (after the app's own backup); a running batch can be stopped. */
export function refreshSection(refresh, busy=false) {
  if(!refresh) return "";
  const batch=refresh.batch, running=batch?.status==="running";
  const due=refresh.items.filter(i=>i.due);
  const rows=refresh.items.map(i=>`<tr class="${i.due?"due-row":""}"><td>${esc(i.source_name)}<small>${esc(i.connector)}</small></td>
    <td>${i.last_done_on?esc(trDate(i.last_done_on)):'<span class="muted">başarılı çekim yok</span>'}</td>
    <td>${i.interval_months==null?'<span class="muted">—</span>':`${i.interval_months} ay`}</td><td>${dueTag(i)}</td>
    <td>${i.due?esc(duration(i.estimate_seconds)):'<span class="muted">—</span>'}</td></tr>`).join("");
  const plan=running||batch?`<div class="refresh-batch"><strong>Son toplu çalıştırma: ${esc(BATCH_LABELS[batch.status] || batch.status)}</strong>
    <small>${esc(trDate(batch.created_at))}${batch.backup_file?` · yedek: ${esc(batch.backup_file)}`:""}${batch.message?` · ${esc(batch.message)}`:""}</small>
    <ol>${batch.plan.map(step=>`<li>${esc(step.source_name)} · ${esc(STEP_LABELS[step.status] || step.status)}${step.message?` <small>(${esc(step.message)})</small>`:""}</li>`).join("")}</ol>
    ${running?`<button data-action="refresh-cancel" data-batch="${esc(batch.id)}">Toplu çalıştırmayı durdur</button>`:""}</div>`:"";
  const partial=refresh.estimate_seconds!=null && !refresh.estimate_complete;
  const estimate=due.length?`${due.length} toplayıcı · tahmini süre ${esc(duration(refresh.estimate_seconds))}${partial?" (bazılarının süresi bilinmiyor; yalnız bilinenler toplandı)":""}`:"Zamanı gelen toplayıcı yok.";
  return `<section class="library refresh-section" aria-label="Güncelleme zamanı gelenler"><div class="library-title"><h2>Güncelleme zamanı gelenler</h2><small>${esc(refresh.note)}</small></div>
    <div class="table-scroll"><table class="lodging-table"><thead><tr><th>TOPLAYICI</th><th>SON BAŞARILI ÇEKİM</th><th>ÖNERİLEN ARALIK</th><th>DURUM</th><th>TAHMİNİ SÜRE</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="refresh-actions"><button class="primary" data-action="refresh-start" ${!due.length || running || busy?"disabled":""}>Zamanı gelenleri başlat</button>
    <span>${estimate}</span></div><p class="source-stamp">Başlatınca önce uygulama kendi veritabanı yedeğini alır (data/backups, "toplu" önekli; son 6 yedek saklanır), sonra zamanı gelen toplayıcılar sırayla (konaklama → kiralama şirketleri; restoran dizini → işletme siteleri) normal iş akışıyla çalışır. Süre tahmini son çekimlere göre bizim tahminimizdir. Bir site doğrulama isterse çekimin sonunda 15 dakika beklenir.</p>${plan}</section>`;
}
