import {esc} from "./api.js";

// GÖREV-18 (Adım 4): before a Claude job starts the screen shows what it will cost and asks for "Başlat": how many calls, roughly how
// many tokens are read and written (from the size of the task texts; written: the median of the step's earlier calls, or the output guess
// of Settings), which model each step runs with, and whether a limit of Settings → Claude is over. Over a limit there is no "Başlat".
// The job card and the run then show the estimate beside the actual; an actual over 1.5 × the estimate is a red warning.

/** "85 bin", "1,2 milyon" (the server's single.thousands). */
export function tokens(value) {
  const n=Math.max(0,Math.round(Number(value)||0));
  if(n>=1_000_000) return `${(n/1_000_000).toFixed(1).replace(".",",").replace(",0","")} milyon`;
  return n>=1000?`${Math.round(n/1000)} bin`:String(n);
}

function modelText(row) {
  if(row.modeller?.length) {
    const names=[...new Set(row.modeller.map(m=>`${m.model_adi} · ${m.efor_adi}`))];
    return names.join("; ");
  }
  return row.model_adi?`${row.model_adi} · ${row.efor_adi}`:"—";
}

/** The estimate with its lines and the buttons; `id` names the box (one per screen). */
export function estimateBox(estimate, {id="estimate", startLabel="Başlat"}={}) {
  if(!estimate) return "";
  const rows=estimate.satirlar.map(row=>`<tr><td>${esc(row.baslik)}</td><td>${row.cagri}</td><td>${esc(tokens(row.okunan))}</td><td>${esc(tokens(row.yazilan))}</td>
    <td><strong>${esc(tokens(row.toplam))}</strong></td><td>${esc(modelText(row))}</td></tr>`).join("");
  const total=estimate.toplam;
  const over=(estimate.asiyor||[]).map(text=>`<li class="problem-error">${esc(text)}</li>`).join("");
  return `<section class="estimate-box" id="${esc(id)}" role="dialog" aria-label="Başlamadan önce tahmin"><h3>Başlamadan önce: tahmin</h3>
    <p class="estimate-line">${esc(estimate.metin)}</p>
    <div class="table-scroll"><table class="reference-table estimate-table"><thead><tr><th>KISIM</th><th>ÇAĞRI</th><th>OKUNACAK</th><th>YAZILACAK</th><th>TOPLAM</th><th>MODEL · EFOR</th></tr></thead>
      <tbody>${rows}</tbody>${estimate.satirlar.length>1?`<tfoot><tr><td>Toplam</td><td>${total.cagri}</td><td>${esc(tokens(total.okunan))}</td><td>${esc(tokens(total.yazilan))}</td><td><strong>${esc(tokens(total.toplam))}</strong></td><td></td></tr></tfoot>`:""}</table></div>
    <p class="muted form-note">Kabaca bir tahmindir: okunan, istemin boyutundan; yazılan, adımın önceki çalışmalarının ortancasından (yoksa Ayarlar'daki varsayımdan). Geçersiz bir cevap bir kez daha istenirse çağrı sayısı artar. Sınırlar: tek çağrı ${esc(tokens(estimate.sinirlar.cagri))}, iş başına ${esc(tokens(estimate.sinirlar.is))} token (Ayarlar → Claude).</p>
    ${over?`<ul class="problem-list">${over}</ul><p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>Tahmin bir sınırı aşıyor; iş başlatılmaz.</span></p>`:""}
    <div class="decision-actions">${estimate.baslatilabilir?`<button class="primary" data-estimate-start>${esc(startLabel)}</button>`:""}<button class="quiet" data-estimate-cancel>Vazgeç</button></div></section>`;
}

/** "tahmin 90 bin, gerçek 85 bin token" and the red warning, from a spending record ({tahmin, gercek, karsilastirma}). */
export function spendingLine(spending) {
  if(!spending) return "";
  const comparison=spending.karsilastirma;
  const actual=spending.gercek;
  const estimate=typeof spending.tahmin==="number"?spending.tahmin:spending.tahmin?.toplam;
  if(!actual && estimate==null) return "";
  const parts=[];
  if(estimate!=null) parts.push(`tahmin ${tokens(estimate)}`);
  if(actual) parts.push(`gerçek ${tokens(actual.toplam)} token (${actual.cagri} çağrı)`);
  const warning=comparison?.fazla?`<p class="spend-over" role="alert"><span class="tag error">Beklenenden fazla</span> ${esc(comparison.uyari)}</p>`:"";
  return `<p class="spend-line ${comparison?.fazla?"over":""}"><span class="tag">Harcama</span> ${esc(parts.join(" · "))}</p>${warning}`;
}
