import {api, esc, date, destinationPath} from "./api.js";
import {stepHref} from "./layers.js";
import {nextTask, packHead} from "./workflow.js";
import {costLine, estimateBox, runningPanel, spentLine, chainTable, staleBox, errorBox, decisionCard, versionsCard, logCard, bindStep} from "./claude-step.js";
import {toneChoice, planView, compareView, versionView} from "./text.js";
import {regionOptions, warnings, markList} from "./videos.js";

// GÖREV-21: the screens of a video's eight steps. Every screen has the same order (after Rota Stüdyo's step screens): the "Sıradaki iş"
// line with the status; the staleness or error box; the step's run card with the estimate above its button; while Claude works the
// running panel (spending so far, "İptal"); the output in readable Turkish; for 3 and 4 the link table; for 1, 3 and 5 the one approval
// component (Onayla, Düzeltme iste, Reddet); "Sürümler" and the status log at the bottom.

const DESCRIPTIONS={
  baslik:"Videonun başlığı, izleyicinin sorusu ve vaadi. Başlık konu bankasından seçilir ya da siz yazarsınız; bu adım onaylanmadan sonraki adımlar başlamaz.",
  paket:"Onaylanan başlığın içerik planından kurulan kanıt paketi ve yazar özeti. Claude çalışmaz; bitince adım tamamlanır.",
  plan:"Videonun planı: bölümler, her bölümün tek fikri, kelime bütçesi ve kanıtları. Claude yazar ve eleştirir; plan onaylanmadan yazım başlamaz.",
  yazim:"İngilizce metin ve cümle cümle Türkçesi. Tonları burada seçersiniz; her ton onaylanan planla ayrı yazılır.",
  kontrol:"Programın denetimi, işletme adı denetimi ve tonların karşılaştırması. Onaylarken hangi tonla devam edileceğini seçersiniz.",
  yayin:"YouTube'a yüklerken kullanılacak paket: bölüm başlıkları, açıklamanın ilk iki satırı, üç arama sorgusu, etiketler, kapak yazısı ve kapak fikri. Onaylı metinden tek Claude çağrısıyla yazılır.",
  kurgu:"Kurgu paketi: Kurgu Motoru'na verilecek paket (metin, cümle numaraları ve zamanları, yer adları, rakamlar, veri kartlarının değerleri). Ses olmadan da kurulur. Claude çağrısı yok.",
  ses:"Seslendirme: onaylı metin sese uygun düz İngilizce dosyalara yazılır; sesi yükler, cümlelerle eşleştirirsiniz. Claude çağrısı yok.",
};

function lines(text) {return esc(text || "—");}

/** 1 · Başlık ve vaat: the chosen title in readable Turkish (Turkish large, English small and pale). */
export function titleCard(choice) {
  if(!choice) return "";
  const plan=(choice.icerik_plani || []).map(p=>`<li><strong>${esc(p.bolum)}</strong> — ${esc(p.ne_anlatir)}</li>`).join("");
  return `<section class="library title-card"><div class="library-title"><h2>Başlık ve vaat</h2><small>${esc(choice.bolge || "")}${choice.aile?` · ${esc(choice.aile)}`:""}</small></div>
    <div class="title-card-body"><p class="title-tr-big">${esc(choice.baslik_tr)}</p><p class="title-en-small" lang="en">${esc(choice.baslik_en)}</p>
    ${choice.kullanici_duzenledi?`<p class="muted">Kullanıcı düzenledi · önerilen: ${esc(choice.onerilen_tr)} <span lang="en">(${esc(choice.onerilen_en)})</span></p>`:""}
    ${markList(choice.isaretler)}
    <h3>İzleyicinin sorusu</h3><p>${lines(choice.izleyici_sorusu)}</p>
    <h3>Vaat</h3><p>${lines(choice.vaat)}</p>
    <h3>Neden bu başlık</h3><p>${lines(choice.neden_onerildi)}</p>
    <h3>İçerik planı (başlık önerisindeki ilk plan)</h3>${plan?`<ol class="plan-list">${plan}</ol>`:"<p>—</p>"}
    <h3>Eksik veri</h3>${(choice.eksik_veri || []).length?`<ul>${choice.eksik_veri.map(m=>`<li>${esc(m)}</li>`).join("")}</ul>`:"<p>Yok.</p>"}
    ${choice.kapak_fikri?`<h3>Kapak fikri</h3><p>${esc(choice.kapak_fikri)}</p>`:""}</div></section>`;
}

/** 1 · Başlık ve vaat, no title yet: the free candidates of the topic bank and the user's own title. */
export function titleChooser(view, form, cost, pending, busy) {
  const candidates=view.adaylar || [];
  const list=candidates.length?`<ul class="bank-pick">${candidates.map(c=>`<li><div><span class="title-tr-big small">${esc(c.baslik_tr)}</span><span class="title-en-small" lang="en">${esc(c.baslik_en)}</span>
      <span class="candidate-tags"><span class="tag">${esc(c.aile || "—")}</span><span class="tag">${esc(c.bolge || "—")}</span>${c.bu_video?'<span class="tag green">bu video için değerlendirildi</span>':""}</span></div>
      <div class="bank-pick-actions"><button type="button" class="primary" data-use-candidate="${esc(c.calisma)}:${c.sira}" ${busy?"disabled":""}>Bu başlığı kullan</button>
        <a class="source-link" href="#konu/calisma/${encodeURIComponent(c.calisma)}">Ayrıntısı (Konu bankası)</a></div></li>`).join("")}</ul>`
    :'<p class="muted run-empty">Konu bankasında kullanılmamış aday yok. <a href="#konu">Konu bankası</a> ekranından “Öneri al” ile öneri alabilir ya da aşağıya kendi başlığınızı yazabilirsiniz.</p>';
  const own=view.secenekler?.available?`<section class="library evidence-form" id="own-title"><div class="library-title"><h2>Kendi başlığını yaz</h2><small>Claude kanalın ölçüleriyle değerlendirir; adayları bu ekranda görünür</small></div>
      ${warnings(view.secenekler)}
      <div class="toolbar video-form"><label class="grow">Başlık ya da fikir <input id="own-title-text" maxlength="500" value="${esc(form.baslik)}" placeholder="Örn. Rosemary Beach'e köpeğimizle gitsek nasıl olur?"></label>
      <label>Bölge <select id="own-title-region">${regionOptions(view.secenekler,form.bolge)}</select></label>
      <label class="grow">Not <input id="own-title-note" maxlength="4000" value="${esc(form.not)}" placeholder="İsteğe bağlı"></label></div>
      <div class="run-card-foot">${costLine(cost)}<button type="button" class="primary" id="own-title-start" ${busy?"disabled":""}>Claude değerlendirsin</button></div>
      ${pending || ""}</section>`:"";
  const runs=(view.degerlendirmeler || []).length?`<section class="library"><div class="library-title"><h2>Bu video için değerlendirmeler</h2><small>${view.degerlendirmeler.length} çalışma</small></div>
    <ul class="version-list">${view.degerlendirmeler.map(r=>`<li><time>${esc(date(r.created_at))}</time> <a href="#konu/calisma/${encodeURIComponent(r.id)}">“${esc(r.baslik || "—")}”</a>
      <span class="tag ${r.status==="error"?"warm":""}">${esc(r.adaysiz?(r.bilgi || "veriyle dolmuyor"):r.status_label)}</span> ${r.aday_sayisi} aday${r.duzeltme_notu?`<small class="source-host">Düzeltme notu: ${esc(r.duzeltme_notu)}</small>`:""}${r.error && !r.canceled?`<small class="source-host">${esc(r.error)}</small>`:""}</li>`).join("")}</ul></section>`:"";
  return `<section class="library"><div class="library-title"><h2>Konu bankasından seç</h2><small>${candidates.length} kullanılmamış aday</small></div>${list}</section>${own}${runs}`;
}

export function packCard(view, busy) {
  const step=view.adim, has=view.surumler?.length;
  const pack=view.surumler?.[0];
  return `<section class="library run-card"><div class="library-title"><h2>${has?"Veri paketini yeniden üret":"Veri paketini üret"}</h2><small>Claude çalışmaz · token harcamaz</small></div>
    <div class="run-card-body"><p class="muted">Paket, onaylanan başlığın içerik planındaki bölümlerin sırasıyla kurulur; her bölümde dayandığı satırlar ve blokları bulunur.${view.paket?.metin?` ${esc(view.paket.metin)}`:""}</p>
    <div class="run-card-foot"><button type="button" class="primary" id="pack-build" ${view.eylemler.run && !busy?"":"disabled"}>${has?"Veri paketini yeniden üret":"Veri paketini üret"}</button>
      ${pack?`<a class="source-link" href="/api/${destinationPath(`evidence-packs/${pack.paket}/yazar-ozeti`)}" download>Yazar özeti ↓</a><a class="source-link" href="/api/${destinationPath(`evidence-packs/${pack.paket}/markdown`)}" download>Tam paket ↓</a>`:""}</div>
    ${step.status==="waiting"?'<p class="stage-note">Önce 1 · Başlık ve vaat adımı onaylanmalı.</p>':""}</div></section>
    ${pack?`<section class="library pack-head"><div class="library-title"><h2>Paketin başı</h2><small>yazar özeti · paket ${esc(pack.paket.slice(0,8))} · ${esc(date(pack.zaman))}</small></div><pre class="path pack-head-text" id="pack-head-text">Yükleniyor…</pre></section>`:""}`;
}

/** The run card of 3 · Plan: the estimate above "Planı çıkar". */
export function planCard(view, cost, pending, busy) {
  const step=view.adim, has=Boolean(view.calisma?.plan);
  const blocked=view.mesgul && !view.is?view.mesgul:"";
  const label=has?"Planı yeniden çıkar":"Planı çıkar";
  return `<section class="library run-card"><div class="library-title"><h2>${label}</h2><small>2 çağrı: planlayıcı ve plan eleştirmeni</small></div>
    <div class="run-card-body"><p class="muted">Claude planı veri paketinden yazar, ikinci bir çağrı eleştirir. Plan hazır olunca burada onayınızı bekler; onaylanmadan yazım başlamaz.${has?" Yeniden çıkarırsanız eski plan Sürümler'de kalır.":""}</p>
    ${blocked?`<p class="stage-note" role="status">${esc(blocked)}</p>`:""}
    <div class="run-card-foot">${costLine(cost)}<button type="button" class="${has?"":"primary"}" id="plan-start" ${view.eylemler.run && !busy && !blocked && !view.is?"":"disabled"}>${label}</button>
      ${view.eylemler.resume?'<button type="button" class="primary" data-resume>Kaldığı yerden sürdür</button>':""}</div>
    ${step.status==="waiting"?'<p class="stage-note">Önce 2 · Veri paketi adımı bitmeli.</p>':""}${pending || ""}</div></section>`;
}

/** The run card of 4 · Yazım: the tones are chosen here; the estimate above "Yazımı başlat". */
export function writingCard(view, chosen, cost, pending, busy) {
  const step=view.adim, run=view.calisma;
  const written=new Set((run?.surumler || []).map(v=>v.tone_file));
  const has=written.size>0;
  const blocked=view.mesgul && !view.is?view.mesgul:"";
  const label=view.duzeltme_notu?"Düzeltme notuyla yeniden yaz":has?"Baştan yaz":"Yazımı başlat";
  const more=has && !view.duzeltme_notu?(view.tonlar || []).filter(t=>!written.has(t.dosya)):[];
  const can=view.eylemler.run && !busy && !blocked && !view.is && chosen.length;
  return `<section class="library run-card text-write"><div class="library-title"><h2>${label}</h2><small>her ton için: bölümler, birleştirme, giriş ve kapanış, son okuma, program denetimi, çeviri</small></div>
    <div class="run-card-body text-write-body">${toneChoice(view.tonlar || [], chosen)}
    ${view.duzeltme_notu?`<p class="stage-note correction-note"><span class="note-mark">✎</span><span><strong>Kullanıcının düzeltme notu</strong> (5 · Kontrol ve ton seçimi adımından): ${esc(view.duzeltme_notu)} Bu not yeniden yazımda Claude'a malzeme olarak verilir.</span></p>`:""}
    ${blocked?`<p class="stage-note" role="status">${esc(blocked)}</p>`:""}
    <div class="run-card-foot">${costLine(cost)}<button type="button" class="${has && !view.duzeltme_notu?"":"primary"}" id="writing-start" ${can?"":"disabled"}>${label}</button>
      ${view.eylemler.resume?'<button type="button" class="primary" data-resume>Kaldığı yerden sürdür</button>':""}
      ${more.length && run?.eylemler?.ton_ekle && !view.is?`<span class="add-tone"><select id="add-tone-select" aria-label="Eklenecek ton">${more.map(t=>`<option value="${esc(t.dosya)}">${esc(t.ad)}</option>`).join("")}</select><button type="button" id="add-tone" data-run="${esc(run.id)}">Bu tonla da yaz</button></span>`:""}</div>
    ${step.status==="waiting"?'<p class="stage-note">Plan onaylanmadan yazım başlamaz: önce 3 · Plan adımında planı onaylayın.</p>':""}${pending || ""}</div></section>`;
}

export function versionList(view, videoId) {
  const versions=view.calisma?.surumler || [];
  if(!versions.length) return "";
  return `<section class="library"><div class="library-title"><h2>Yazılan metinler</h2><small>${versions.length} ton</small></div>
    <div class="table-scroll"><table class="reference-table"><thead><tr><th>TON</th><th>SÜRÜM</th><th>UZUNLUK</th><th>DENETİM</th><th></th></tr></thead><tbody>
    ${versions.map(v=>`<tr><td><strong>${esc(v.tone_name)}</strong>${v.secili?' <span class="tag green">seçili ton</span>':""}</td><td>${v.number}. sürüm<small class="source-host">${esc(date(v.created_at))}</small></td>
      <td>${Number(v.words).toLocaleString("tr")} kelime · ~${String(v.dakika).replace(".",",")} dk</td><td><span class="mark-count red">${v.red} kırmızı</span> · <span class="mark-count yellow">${v.yellow} sarı</span></td>
      <td><a class="source-link" href="${stepHref(videoId,"yazim","surum",v.id)}">Metni oku</a></td></tr>`).join("")}</tbody></table></div></section>`;
}

/** 5 · Kontrol ve ton seçimi: the program's check per tone (business names first) above the comparison. */
export function checkCards(view) {
  const tones=view.tonlar || [];
  if(!tones.length) return '<p class="muted">Henüz yazılmış metin yok.</p>';
  return `<section class="library check-cards"><div class="library-title"><h2>Programın denetimi</h2><small>kırmızı: düzeltilmeli · sarı: göz atılmalı</small></div>
    <div class="check-grid">${tones.map(t=>`<article class="check-card ${t.secili?"chosen":""}"><h3>${esc(t.tone_name)} <small>${t.number}. sürüm</small>${t.secili?' <span class="tag green">seçili ton</span>':""}</h3>
      <p><span class="mark-count red">${t.red} kırmızı</span> · <span class="mark-count yellow">${t.yellow} sarı</span> · ${Number(t.words).toLocaleString("tr")} kelime · ~${String(t.dakika).replace(".",",")} dk</p>
      <p><span class="tag ${t.isletme_adi?"error":"green"}">İşletme adı denetimi: ${t.isletme_adi?`${t.isletme_adi} bulgu`:"bulgu yok"}</span></p>
      ${(t.bulgular || []).length?`<ul class="finding-groups">${t.bulgular.map(g=>`<li><strong>${esc(g.ad)}</strong> — ${g.kirmizi?`<span class="mark-count red">${g.kirmizi} kırmızı</span> `:""}${g.sari?`<span class="mark-count yellow">${g.sari} sarı</span>`:""}
        <ul>${g.ornekler.map(o=>`<li class="${o.seviye==="kirmizi"?"mark-red":"mark-yellow"}">${o.no?`${o.no}. cümle: `:""}${esc(o.metin)}</li>`).join("")}</ul></li>`).join("")}</ul>`:'<p class="muted">Denetim bulgusu yok.</p>'}</article>`).join("")}</div></section>`;
}

/** The tone the video goes on with, chosen next to "Onayla" in the approval component. */
export function toneRadios(view, chosen) {
  const tones=view.tonlar || [];
  return `<fieldset class="tone-choice go-on-tone"><legend>Devam edilecek ton (Onayla ile birlikte seçilir)</legend>${tones.map(t=>`<label class="tone-option"><input type="radio" name="go-on-tone" value="${esc(t.id)}" ${t.id===chosen?"checked":""}>
    <span><strong>${esc(t.tone_name)}</strong> <small>${t.number}. sürüm · ${t.red} kırmızı · ${t.yellow} sarı</small></span></label>`).join("")}</fieldset>`;
}

const clock=seconds=>{const s=Math.round(seconds || 0), m=Math.floor(s/60);return `${String(m).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;};

/** The run card of 6 · Yayın paketi (HEDEF-04 A-6): one Claude call; the estimate above "Yayın paketini çıkar". */
export function publishCard(view, cost, pending, busy) {
  const step=view.adim, has=Boolean(view.yayin?.paket);
  const label=has?"Yayın paketini yeniden çıkar":"Yayın paketini çıkar";
  return `<section class="library run-card"><div class="library-title"><h2>${label}</h2><small>1 çağrı · onaylı metinden</small></div>
    <div class="run-card-body"><p class="muted">Claude onaylı İngilizce metinden bölüm başlıklarını, açıklamanın ilk iki satırını, üç arama sorgusunu, etiketleri, kapak yazısını ve kapak fikrini yazar; program bölümleri denetler ve dosyaya yazar. Bölüm zamanları metnin kelime sayısından tahminidir (dakikada 150 kelime); ses gelince kesinleşecek.${has?" Yeniden çıkarırsanız eski paket Sürümler'de kalır.":""}</p>
    <div class="run-card-foot">${costLine(cost)}<button type="button" class="${has?"":"primary"}" id="publish-start" ${view.eylemler.run && !busy && !view.is?"":"disabled"}>${label}</button></div>
    ${step.status==="waiting"?'<p class="stage-note">Önce 5 · Kontrol ve ton seçimi onaylanmalı.</p>':""}${pending || ""}</div></section>`;
}

/** 6 · Yayın paketi: the package (English as it goes to YouTube, Turkish under it); the times are marked as estimates. */
export function publishView(found) {
  const data=found?.paket;
  if(!data) return "";
  const pair=item=>`${esc(item?.en || "")}<br><small class="muted">${esc(item?.tr || "")}</small>`;
  const problems=(found.sorunlar || []).map(p=>`<li>${p.seviye==="hata"?"Hata":"Uyarı"}: ${esc(p.metin)}</li>`).join("");
  const spent=found.harcama?.karsilastirma?.metin;
  return `<section class="library publish-view"><div class="library-title"><h2>Yayın paketi</h2><small>${esc(found.durum_adi || "")} · <span class="tag warm">zamanlar tahmini</span></small></div>
    ${found.duzeltme_notu?`<p class="stage-note correction-note"><span class="note-mark">✎</span><span><strong>Kullanıcının düzeltme notu</strong> (bu paket bu notla yazıldı): ${esc(found.duzeltme_notu)}</span></p>`:""}
    <h3>Bölüm başlıkları</h3><p class="muted">${esc(found.tahmini || "")}${found.zaman?` Metin ${esc(found.zaman.kelime)} kelime, tahmini süre ${clock(found.zaman.sure_s)}.`:""}</p>
    <table class="data-table"><thead><tr><th>Zaman (tahmini)</th><th>Bölüm</th></tr></thead><tbody>${(data.bolumler || []).map(c=>`<tr><td>~${esc(c.zaman)}</td><td>${pair({en:c.baslik_en,tr:c.baslik_tr})}</td></tr>`).join("")}</tbody></table>
    <h3>Açıklamanın ilk iki satırı</h3><ol>${(data.aciklama_ilk_iki_satir || []).map(l=>`<li>${pair(l)}</li>`).join("")}</ol>
    <h3>Hedeflenen arama sorguları</h3><ol>${(data.arama_sorgulari || []).map(q=>`<li>${pair(q)}</li>`).join("")}</ol>
    <h3>Etiketler</h3><p>${(data.etiketler || []).map(t=>`<span class="tag">${esc(t)}</span>`).join(" ")}</p>
    <h3>Kapak</h3><p><strong>Kapak yazısı:</strong> ${pair(data.kapak_yazisi)}</p><p><strong>Kapak fikri:</strong> ${esc(data.kapak_fikri || "")}</p>
    ${problems?`<h3>Programın denetimi</h3><ul>${problems}</ul>`:'<p class="muted">Programın denetimi: bölümler uygun (ilki 00:00, en az 3, her biri en az 10 sn, artan sıra).</p>'}
    ${(data.notlar || []).length?`<h3>Claude'un notları</h3><ul>${data.notlar.map(n=>`<li>${esc(n)}</li>`).join("")}</ul>`:""}
    ${spent?`<p class="muted">Harcama: ${esc(spent)}</p>`:""}${found.dosya?`<p class="muted">Dosya: <code>${esc(found.dosya)}</code></p>`:""}</section>`;
}

/** 7 · Seslendirme (HEDEF-04 A-7): the text files, "Sesi yükle", "Sesi cümlelerle eşleştir" and the paths' settings. */
export function voiceView(view, busy) {
  const s=view.ses || {}, m=s.metin, a=s.ses, e=s.eslesme, st=view.adim.status, free=!busy && !view.is;
  const on=c=>c && free?"":"disabled";
  const sec=n=>n==null?"—":`${Number(n).toFixed(1)} sn`;
  const text=m?`<p>${m.parca_sayisi} parça · ${m.cumle_sayisi} cümle · ${m.karakter} karakter. Sesi bu dosyalarla, sırayla üretin.</p>
    <p class="muted">Klasör: <code>${esc(m.klasor)}</code> <button type="button" data-voice-folder="metin">Klasörü aç</button></p>
    <ul>${m.dosyalar.map(f=>`<li><code>${esc(f.yol)}</code> <small>${f.karakter} karakter · cümle ${f.ilk}–${f.son}</small></li>`).join("")}</ul>
    <p class="muted">Cümle → parça eşlemesi: <code>${esc(m.eslesme_dosyasi)}</code></p>`:'<p class="muted">Metin henüz hazırlanmadı.</p>';
  const audio=a?`<table class="data-table"><thead><tr><th>Dosya</th><th>Süre</th></tr></thead><tbody>${a.dosyalar.map(f=>`<tr><td>${esc(f.ad)}</td><td>${sec(f.sure_s)}</td></tr>`).join("")}</tbody></table>
    <p class="muted">Toplam ${sec(a.toplam_s)} · klasör <code>${esc(a.klasor)}</code> <button type="button" data-voice-folder="ses">Klasörü aç</button></p>
    ${(a.sorunlar || []).length?`<ul>${a.sorunlar.map(p=>`<li>Hata: ${esc(p)}</li>`).join("")}</ul>`:""}`:'<p class="muted">Ses henüz yüklenmedi.</p>';
  const found=e?`<p><strong>${e.eslesen}/${e.cumle_sayisi} cümle eşleşti</strong> · eşleşmeyen ${e.eslesmeyen} cümle · ${e.kelime_sayisi} kelime</p>
    <table class="data-table"><thead><tr><th>Cümle</th><th>Başlangıç</th><th>Bitiş</th></tr></thead><tbody>${(e.ilk_cumleler || []).map(c=>`<tr><td>${c.no}</td><td>${sec(c.baslangic)}</td><td>${sec(c.bitis)}</td></tr>`).join("")}</tbody></table>
    <p class="muted">Bütün cümleler: <code>${esc(e.dosya)}</code></p>`:"";
  const cfg=(s.ayarlar || {}).settings || {}, def=(s.ayarlar || {}).varsayilan || {};
  const field=(k,t)=>`<label>${t} <input name="${k}" value="${esc(cfg[k] || "")}" placeholder="${esc(def[k] || "")}"></label>`;
  return `<section class="library"><div class="library-title"><h2>Seslendirme metni</h2><small>düz İngilizce · parça başına en çok 4.500 karakter</small></div>${text}
    ${view.eylemler.run && m?`<button type="button" id="voice-text" ${on(true)}>Metni yeniden hazırla</button>`:""}</section>
    <section class="library"><div class="library-title"><h2>Ses</h2><small>mp3 ya da wav · tek dosya ya da _01, _02… parçalar</small></div>
    <p class="muted">Birden çok parça yüklerseniz metin parçalarıyla aynı sayıda ve sırada olmalı (seslendirme_01 → ..._01).</p>
    <label class="button-like">Sesi yükle <input type="file" id="voice-files" accept=".mp3,.wav,audio/mpeg,audio/wav" multiple ${on(m)}></label>${audio}</section>
    <section class="library"><div class="library-title"><h2>Eşleştirme</h2><small>Kurgu Motoru'nun hizalaması</small></div>
    <button type="button" class="primary" id="voice-match" ${on(st==="audio_ready" || st==="done")}>Sesi cümlelerle eşleştir</button>${found}</section>
    <details class="library"><summary>Ses ayarları</summary><form id="voice-settings">${field("ffprobe_path","ffprobe yolu")}${field("kurgu_motoru_path","Kurgu Motoru klasörü")}${field("kurgu_python_path","Motorun Python'u")}
    <button type="submit">Kaydet</button></form></details>`;
}

/** 8 · Kurgu paketi (HEDEF-04 A-8): what the package holds, the card suggestions, "Kurguya gönder" and the motor's output. */
export function kurguView(view, busy) {
  const k=view.kurgu || {}, p=k.paket, g=k.gonderim, st=view.adim.status, free=!busy && !view.is;
  const on=c=>c && free?"":"disabled";
  const o=(p || {}).ozet || {};
  const voice=o.zamanlar?"Ses ve cümle zamanları pakette.":o.ses?"Ses pakette; cümle zamanlarını Kurgu Motoru kendi hizalar (bütün cümleler eşleşmedi).":"Ses yok: paket sessiz kuruldu, zamanlar boş. Ses 7 · Seslendirme'de eşleşince “Paketi yeniden kur”.";
  const pack=p?`<p><strong>${o.cumle} cümle</strong> · ${o.bolum} bölüm · ${o.kayit} veri kaydı (${o.kaynak} kaynak) · ${o.yer} yer adı · ${o.rakam} rakam (${o.kaynakli_rakam} kaynaklı) · ${o.sahne} kart önerisi</p>
    <p>${esc(voice)}</p>${k.ses_degisti?'<p class="error">Ses paket kurulduktan sonra değişti; “Paketi yeniden kur”.</p>':""}
    <p class="muted">Kanal (motorun stili): <code>${esc(o.kanal || "")}</code> · kart ve geçiş sesi eklenmez.</p>
    <p class="muted">Klasör: <code>${esc(p.yol)}</code> <button type="button" id="kurgu-folder">Klasörü aç</button></p>
    <p class="muted">Dosyalar: ${(p.dosyalar || []).map(f=>`<code>${esc(f)}</code>`).join(" ")}</p>
    ${(p.kartlar || []).length?`<table class="data-table"><thead><tr><th>Cümle</th><th>Kart</th><th>Neden</th></tr></thead><tbody>${p.kartlar.map(c=>`<tr><td>${esc(c.cumle)} <small>${esc(c.metin)}</small></td><td>${esc(c.kart)}</td><td>${esc(c.gerekce || "")}</td></tr>`).join("")}</tbody></table>`:""}`
    :'<p class="muted">Paket henüz kurulmadı.</p>';
  const sent=g?`<p><strong>${g.basarili?"Gönderildi":"Gönderim hata verdi"}</strong> · ${esc(g.zaman || "")}${g.proje?` · proje <code>${esc(g.proje)}</code>`:""}</p>
    ${g.proje_klasoru?`<p class="muted">Motordaki proje: <code>${esc(g.proje_klasoru)}</code></p>`:""}
    ${(g.adimlar || []).map(a=>`<details ${a.kod?"open":""}><summary>${esc(a.komut)} · çıkış kodu ${a.kod}</summary><pre class="log">${esc(a.cikti || "")}</pre></details>`).join("")}`:"";
  return `<section class="library"><div class="library-title"><h2>Kurgu paketi</h2><small>kurgu-paket/1 · ses olmadan da kurulur</small></div>${pack}
    ${view.eylemler.run?`<button type="button" id="kurgu-build" ${on(true)}>Paketi yeniden kur</button>`:""}</section>
    <section class="library"><div class="library-title"><h2>Kurguya gönder</h2><small>Kurgu Motoru: paket dogrula + ice-al</small></div>
    <p class="muted">Paket motorun klasörüne kopyalanır, motor önce denetler, sonra projeyi kurar. Kurgu (stok görüntü, kartların yeri, altyazı) motorda yapılır. Motorun yeri: Ayarlar → Kurgu Motoru.</p>
    <button type="button" class="primary" id="kurgu-send" ${on(p && st!=="waiting")}>Kurguya gönder</button>${sent}</section>`;
}

export function plannedBody(view) {
  return `<section class="planned-hero"><span class="tag planned">Sonraki görevde gelecek</span><h2>${esc(view.adim.title)}</h2><p>${esc(view.aciklama || "")}</p>
    <p class="muted">Bu adım henüz kurulmadı; şimdilik yapılacak iş yok.</p></section>`;
}

export class StepScreen {
  constructor() {this.reset();this.sequence=0;this.lang="tr";}
  reset() {this.view=null;this.key="";this.pending=null;this.message="";this.busy=false;this.cost={};this.chosen=null;this.form={baslik:"",bolge:"",not:""};this.tone=null;this.jobKey="";this.note="";}
  invalidate() {this.sequence++;}
  job() {return this.view?.is?(this.ctx.jobs().find(j=>j.id===this.view.is) || null):null;}
  href(...rest) {return stepHref(this.ctx.route.videoId, this.ctx.route.step, ...rest);}

  async render(main, ctx) {
    this.main=main;this.ctx=ctx;
    const {videoId, step}=ctx.route;
    const key=`${videoId}:${step}`;
    if(key!==this.key) {this.reset();this.key=key;}
    const ticket=++this.sequence;
    if(!this.view) main.innerHTML=ctx.heading(ctx.stepTitle || "Adım","")+'<p class="loading" role="status">Yükleniyor…</p>';
    try {
      const view=await api(`videos/${encodeURIComponent(videoId)}/adimlar/${encodeURIComponent(step)}`);
      if(ticket!==this.sequence) return;
      this.view=view;
      if(step==="yazim" && this.chosen===null) this.chosen=(view.tonlar || []).filter(t=>t.varsayilan).map(t=>t.dosya);
      if(step==="kontrol" && !this.tone) this.tone=view.secim?.version_id || (view.tonlar || [])[0]?.id || null;
      await this.draw(ticket);
      this.loadCost(ticket);
    } catch(error) {
      if(error.stale || ticket!==this.sequence) return;
      main.innerHTML=ctx.heading("Adım açılamadı","")+`<section class="quality-result empty"><h2>${esc(error.message)}</h2><a class="return-link" href="#videolar">← Videolar</a></section>`;
    }
  }
  rerender() {if(this.main && this.ctx) return this.render(this.main,this.ctx);}

  /** The job panel changed: a job of this step started or ended → the screen is read again; else only its running panel moves. */
  jobsChanged() {
    if(!this.view || !this.main?.isConnected) return;
    const job=this.job();
    const claude=this.ctx.jobs().filter(j=>["claude_run","claude_metin"].includes(j.kind)).map(j=>`${j.id}:${j.status}`).join(",");
    if(claude!==this.jobKey) {this.jobKey=claude;this.rerender();return;}
    const panel=this.main.querySelector("[data-run-panel]");
    if(panel && job) {panel.outerHTML=runningPanel(job);bindStep(this.main,this.handlers());}
  }

  /** The estimate above the start button of 3 · Plan and 4 · Yazım, asked as soon as the step can run. */
  async loadCost(ticket) {
    const {videoId, step}=this.ctx.route, view=this.view;
    if(!view.eylemler.run || view.is || this.pending || !["plan","yazim","yayin"].includes(step) || view.adim.status==="waiting") return;
    if(step==="yazim" && !(this.chosen || []).length) {this.cost={hint:"Ton seçince hesaplanır."};this.paintCost();return;}
    this.cost={loading:true};this.paintCost();
    try {
      const estimate=step==="yayin"?await api(`videos/${encodeURIComponent(videoId)}/yayin/tahmin`,{method:"POST",body:"{}"}):step==="plan"?await api(`videos/${encodeURIComponent(videoId)}/plan/tahmin`,{method:"POST",body:"{}"})
        :await api(`videos/${encodeURIComponent(videoId)}/yazim/tahmin`,{method:"POST",body:JSON.stringify({tonlar:this.chosen})});
      if(ticket!==this.sequence) return;
      this.cost={estimate};
    } catch(error) {if(error.stale || ticket!==this.sequence) return;this.cost={error:error.message};}
    this.paintCost();
  }
  paintCost() {
    const slot=this.main?.querySelector("[data-cost-line], .cost-error");
    if(slot) slot.outerHTML=costLine(this.cost);
  }

  pendingBox() {return this.pending?estimateBox(this.pending.estimate,{id:"step-estimate",startLabel:this.pending.label}):"";}

  async draw(ticket) {
    const {ctx, view}=this, step=view.adim, id=ctx.route.videoId;
    const head=ctx.heading(`${step.number} · ${step.title}`, DESCRIPTIONS[step.id] || "")+`<div id="next-task-slot">${nextTask(step)}</div>`;
    const job=this.job();
    const common=`${staleBox(step,view.eylemler)}${errorBox(step)}${this.message?`<p class="stage-note" role="status">${esc(this.message)}</p>`:""}`;
    const foot=`${versionsCard(view.surumler, item=>this.versionLink(item))}${logCard(view.gunluk)}`;
    let body="";
    if(step.planned) body=plannedBody(view);
    else if(step.id==="baslik") {
      const decision=decisionCard(step,view.eylemler,{description:"Başlık ve vaat uygunsa onaylayın", note:this.note, pending:this.pendingBox(), busy:this.busy,
        help:"Düzeltme iste: notunuz, adayın çalışması yeniden çalıştırılırken Claude'a “kullanıcının düzeltme notu” olarak verilir; yeni adaylar bu ekranda görünür. Reddet: başlık seçimi kalkar, aday konu bankasına döner ve adım hazır olur."});
      body=view.secim?`${runningPanel(job)}${titleCard(view.secim)}${decision}`
        :`${runningPanel(job)}${view.eylemler.run?titleChooser(view,this.form,this.cost,this.pendingBox(),this.busy):""}`;
    } else if(step.id==="paket") body=packCard(view,this.busy);
    else if(step.id==="plan") {
      const run=view.calisma;
      const decision=decisionCard(step,view.eylemler,{description:"Plan onaylanmadan yazım başlamaz", note:this.note, pending:run?.plan?this.pendingBox():"", busy:this.busy,
        help:"Düzeltme iste: plan, notunuz ve bu plan Claude'a malzeme olarak verilerek yeniden yazılır (2 çağrı; tahmini önce gösterilir). Reddet: adım hazır durumuna döner."});
      body=`${planCard(view,this.cost,run?.plan?"":this.pendingBox(),this.busy)}${runningPanel(job)}
        ${run?`${chainTable(run.halkalar && {...run.halkalar,halkalar:run.halkalar.halkalar.filter(r=>r.grup==="plan")},{title:"Planın halkaları"})}${spentLine(run.harcama)}`:""}
        ${run?.plan_notu?`<p class="stage-note correction-note"><span class="note-mark">✎</span><span><strong>Kullanıcının düzeltme notu</strong> (bu plan bu notla yazıldı): ${esc(run.plan_notu)}</span></p>`:""}
        ${run?.plan?planView(run):""}${decision}`;
    } else if(step.id==="yazim") {
      if(ctx.route.view==="surum" && ctx.route.id) {
        const version=await api(`metin/surumler/${encodeURIComponent(ctx.route.id)}`);
        if(ticket!==this.sequence) return;
        this.main.innerHTML=head+`<a class="return-link" href="${this.href()}">← 4 · Yazım</a>${versionView(version,this.href())}`;
        return;
      }
      const run=view.calisma;
      body=`${writingCard(view,this.chosen || [],this.cost,this.pendingBox(),this.busy)}${runningPanel(job)}
        ${run?`${chainTable(run.halkalar && {...run.halkalar,halkalar:run.halkalar.halkalar.filter(r=>r.grup!=="plan")},{title:"Yazımın halkaları"})}${spentLine(run.harcama)}`:""}
        ${versionList(view,id)}`;
    } else if(step.id==="yayin") {
      const found=view.yayin;
      const decision=decisionCard(step,view.eylemler,{description:"Yayın paketi uygunsa onaylayın", note:this.note, pending:found?.paket?this.pendingBox():"", busy:this.busy,
        help:"Düzeltme iste: notunuz ve bu paket Claude'a malzeme olarak verilerek paket yeniden yazılır (1 çağrı; tahmini önce gösterilir). Reddet: adım hazır durumuna döner; paket Sürümler'de kalır."});
      body=`${publishCard(view,this.cost,found?.paket?"":this.pendingBox(),this.busy)}${runningPanel(job)}${publishView(found)}${decision}`;
    } else if(step.id==="ses") {
      body=voiceView(view,this.busy);
    } else if(step.id==="kurgu") {
      body=kurguView(view,this.busy);
    } else if(step.id==="kontrol") {
      let compare=null;
      if((view.tonlar || []).length) {
        compare=await api(`videos/${encodeURIComponent(id)}/metin/karsilastirma${view.calisma?`?calisma=${encodeURIComponent(view.calisma)}`:""}`);
        if(ticket!==this.sequence) return;
      }
      const decision=decisionCard(step,view.eylemler,{description:"Onaylarken devam edilecek tonu seçin", note:this.note, extra:toneRadios(view,this.tone), busy:this.busy,
        approveLabel:"Onayla ve bu tonla devam et",
        help:"Düzeltme iste: notunuz 4 · Yazım adımını hazır yapar ve yeniden yazımda Claude'a “kullanıcının düzeltme notu” olarak verilir (harcama tahmini orada, “Yazımı başlat” düğmesinin üstünde). Reddet: adım hazır durumuna döner."});
      body=`${view.eylemler.reopen?'<section class="library run-card"><div class="run-card-body"><div class="run-card-foot"><button type="button" class="primary" id="check-reopen">Kontrolü yeniden aç</button><span class="muted">Karşılaştırma ve karar yeniden açılır; metni değiştirmek için 4 · Yazım adımına gidin.</span></div></div></section>':""}
        ${view.not && step.status!=="approved"?`<p class="stage-note"><span class="note-mark">✎</span><span>Son not: ${esc(view.not)}</span></p>`:""}
        ${(view.tonlar || []).length?checkCards(view):'<p class="muted">Henüz yazılmış metin yok.</p>'}
        ${compare?`<section class="library"><div class="library-title"><h2>Tonların karşılaştırması</h2><small>${compare.sutunlar.length} ton yan yana</small></div><div class="compare-wrap">${compareView(compare,this.lang,v=>stepHref(id,"yazim","surum",v))}</div></section>`:""}
        ${decision}`;
    }
    this.main.innerHTML=head+common+body+foot;
    this.bind();
  }

  versionLink(item) {
    const id=this.ctx.route.videoId;
    if(item.surum) return stepHref(id,"yazim","surum",item.surum);
    if(item.paket) return `/api/${destinationPath(`evidence-packs/${item.paket}/yazar-ozeti`)}`;
    return "";
  }

  handlers() {
    return {decide:(kind,note)=>this.decide(kind,note), clearStale:note=>this.call(`adimlar/${this.ctx.route.step}/etkilemiyor`,{not:note},"Eskime kaldırıldı; adım önceki durumuna döndü."),
      cancel:jobId=>this.cancel(jobId)};
  }

  path(rest) {return `videos/${encodeURIComponent(this.ctx.route.videoId)}/${rest}`;}

  bind() {
    const root=this.main, step=this.view.adim.id;
    bindStep(root,this.handlers());
    root.querySelector("#decision-note")?.addEventListener("input",event=>{this.note=event.target.value;});
    root.querySelector("[data-estimate-start]")?.addEventListener("click",()=>{const job=this.pending;this.pending=null;job.start();});
    root.querySelector("[data-estimate-cancel]")?.addEventListener("click",()=>{this.pending=null;this.message="Vazgeçildi; Claude çalıştırılmadı.";this.rerender();});
    root.querySelector("[data-resume]")?.addEventListener("click",()=>this.call(`adimlar/${step}/surdur`,{},"Çalışma kaldığı yerden sürüyor."));
    root.querySelectorAll("[data-lang]").forEach(button=>button.addEventListener("click",()=>{this.lang=button.dataset.lang;this.rerender();}));
    root.querySelectorAll('input[name="go-on-tone"]').forEach(radio=>radio.addEventListener("change",()=>{this.tone=radio.value;}));
    if(step==="baslik") {
      root.querySelectorAll("[data-use-candidate]").forEach(button=>button.addEventListener("click",()=>{
        const [calisma,aday]=button.dataset.useCandidate.split(":");
        this.call("baslik/aday",{calisma,aday:Number(aday)},"Başlık seçildi; onayınızı bekliyor.");
      }));
      root.querySelector("#own-title-text")?.addEventListener("input",event=>{this.form.baslik=event.target.value;});
      root.querySelector("#own-title-region")?.addEventListener("change",event=>{this.form.bolge=event.target.value;});
      root.querySelector("#own-title-note")?.addEventListener("input",event=>{this.form.not=event.target.value;});
      root.querySelector("#own-title-start")?.addEventListener("click",()=>{
        if(!this.form.baslik.trim()) {this.message="Önce başlığı ya da fikri yazın.";this.rerender();return;}
        if(!this.form.bolge) {this.message="Önce bölge seçin.";this.rerender();return;}
        const body={bolge:this.form.bolge,baslik:this.form.baslik,not:this.form.not};
        this.ask(()=>api(this.path("baslik/degerlendir/tahmin"),{method:"POST",body:JSON.stringify(body)}),"Claude değerlendirsin: başlat",
          ()=>this.call("baslik/degerlendir",body,"Claude başlığınızı değerlendiriyor; adaylar bu ekranda görünecek."));
      });
    }
    if(step==="paket") {
      root.querySelector("#pack-build")?.addEventListener("click",()=>this.call("evidence-pack",{},"Veri paketi üretildi."));
      const pack=this.view.surumler?.[0], slot=root.querySelector("#pack-head-text");
      if(pack && slot) fetch(`/api/${destinationPath(`evidence-packs/${encodeURIComponent(pack.paket)}/yazar-ozeti`)}`).then(r=>r.ok?r.text():Promise.reject(new Error("Paket okunamadı.")))
        .then(text=>{if(slot.isConnected) slot.textContent=packHead(text);}).catch(error=>{if(slot.isConnected) slot.textContent=error.message;});
    }
    if(step==="plan") root.querySelector("#plan-start")?.addEventListener("click",()=>{
      if(this.view.calisma?.plan && globalThis.confirm && !globalThis.confirm("Plan yeniden çıkarılsın mı? Eski plan Sürümler'de kalır; onaylıysa onayı kalkar.")) return;
      this.ask(()=>api(this.path("plan/tahmin"),{method:"POST",body:"{}"}),"Planı çıkar: başlat",()=>this.call("plan",{},"Plan yazılıyor; harcama aşağıda."));
    });
    if(step==="yazim") {
      root.querySelectorAll("[data-tone]").forEach(box=>box.addEventListener("change",()=>{
        this.chosen=[...root.querySelectorAll("[data-tone]:checked")].map(b=>b.dataset.tone);
        const start=root.querySelector("#writing-start");
        if(start) start.disabled=!this.chosen.length || !this.view.eylemler.run || Boolean(this.view.is);
        this.loadCost(this.sequence);
      }));
      root.querySelector("#writing-start")?.addEventListener("click",()=>{
        const tonlar=[...this.chosen];
        this.ask(()=>api(this.path("yazim/tahmin"),{method:"POST",body:JSON.stringify({tonlar})}),"Yazımı başlat: başlat",
          ()=>this.call("yazim",{tonlar},"Yazım başladı; halka tablosu aşağıda."));
      });
      root.querySelector("#add-tone")?.addEventListener("click",event=>{
        const run=event.currentTarget.dataset.run, ton=root.querySelector("#add-tone-select").value;
        this.ask(()=>api(`metin/calismalar/${encodeURIComponent(run)}/ton/tahmin`,{method:"POST",body:JSON.stringify({ton})}),"Bu tonla da yaz: başlat",
          ()=>this.act(()=>api(`metin/calismalar/${encodeURIComponent(run)}/ton`,{method:"POST",body:JSON.stringify({ton})}),"Aynı planla bir ton daha yazılıyor."));
      });
    }
    if(step==="yayin") root.querySelector("#publish-start")?.addEventListener("click",()=>{
      if(this.view.yayin?.paket && globalThis.confirm && !globalThis.confirm("Yayın paketi yeniden çıkarılsın mı? Eski paket Sürümler'de kalır.")) return;
      this.ask(()=>api(this.path("yayin/tahmin"),{method:"POST",body:"{}"}),"Yayın paketini çıkar: başlat",()=>this.call("yayin",{},"Yayın paketi yazılıyor; harcama aşağıda."));
    });
    if(step==="ses") {
      root.querySelector("#voice-files")?.addEventListener("change",event=>{
        const files=[...event.target.files].sort((x,y)=>x.name.localeCompare(y.name));
        if(!files.length) return;
        this.act(async()=>{for(const [i,f] of files.entries()) await api(`${this.path("ses/yukle")}?ad=${encodeURIComponent(f.name)}&yeni=${i===0?1:0}`,
          {method:"POST",body:f,headers:{"Content-Type":"application/octet-stream"}});},`${files.length} ses dosyası yüklendi.`);
      });
      root.querySelector("#voice-match")?.addEventListener("click",()=>this.call("ses/eslestir",{},"Ses cümlelerle eşleştirildi."));
      root.querySelector("#voice-text")?.addEventListener("click",()=>{
        if(globalThis.confirm && !globalThis.confirm("Metin dosyaları yeniden hazırlansın mı? Eskiler klasörde kalır; ses yeniden yüklenmeli.")) return;
        this.call("ses/metin",{},"Seslendirme metni yeniden hazırlandı.");
      });
      root.querySelectorAll("[data-voice-folder]").forEach(b=>b.addEventListener("click",()=>api(`${this.path("ses/klasor")}?hangi=${b.dataset.voiceFolder}`,{method:"POST",body:"{}"})
        .catch(error=>{this.message=error.message;this.rerender();})));
      root.querySelector("#voice-settings")?.addEventListener("submit",event=>{event.preventDefault();
        this.act(()=>api("settings/seslendirme",{method:"PUT",body:JSON.stringify(Object.fromEntries(new FormData(event.target)))}),"Ses ayarları kaydedildi.");});
    }
    if(step==="kurgu") {
      root.querySelector("#kurgu-build")?.addEventListener("click",()=>this.call("kurgu/kur",{},"Kurgu paketi yeniden kuruldu."));
      root.querySelector("#kurgu-send")?.addEventListener("click",()=>this.call("kurgu/gonder",{},"Kurguya gönderim bitti; sonuç aşağıda."));
      root.querySelector("#kurgu-folder")?.addEventListener("click",()=>api(this.path("kurgu/klasor"),{method:"POST",body:"{}"})
        .catch(error=>{this.message=error.message;this.rerender();}));
    }
    if(step==="kontrol") root.querySelector("#check-reopen")?.addEventListener("click",()=>this.call("kontrol/ac",{},"Kontrol yeniden açıldı."));
  }

  /** The estimate first; the job starts only after its "Başlat". */
  async ask(estimateCall, label, start) {
    this.busy=true;this.pending=null;
    try {const found=await estimateCall();this.pending={estimate:found?.tahmin===undefined?found:found.tahmin, label, start};this.message="";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;}
    if(this.pending && !this.pending.estimate) {const job=this.pending;this.pending=null;return job.start();}     // no Claude: nothing to estimate
    await this.rerender();
    this.main?.querySelector("#step-estimate")?.scrollIntoView?.({block:"nearest"});
  }
  call(rest, body, message) {return this.act(()=>api(this.path(rest),{method:"POST",body:JSON.stringify(body || {})}),message);}
  async act(request, message) {
    this.busy=true;
    try {await request();this.message=message;this.cost={};}
    catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;}
    await this.ctx.reload?.();
    return this.rerender();
  }
  async cancel(jobId) {
    try {await api(`jobs/${encodeURIComponent(jobId)}/cancel`,{method:"POST"});this.message="İptal edildi; iş kayda “iptal edildi” diye düştü, harcaması sayıldı.";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    await this.ctx.reload?.();
    return this.rerender();
  }

  /** The one approval component: Onayla, Düzeltme iste (the note is required; a Claude step shows its estimate first), Reddet. */
  decide(kind, note) {
    const step=this.ctx.route.step;
    this.note=note;
    const done=message=>{this.note="";return message;};
    if(kind==="onayla") {
      if(step==="kontrol" && !this.tone) {this.message="Onaylarken devam edilecek tonu seçin.";return this.rerender();}
      return this.call(`adimlar/${step}/onayla`,{not:note,...(step==="kontrol"?{surum:this.tone}:{})},done("Onaylandı."));
    }
    if(kind==="reddet") {
      if(globalThis.confirm && !globalThis.confirm("Reddedilsin mi? Adım hazır durumuna döner; çıktı Sürümler'de kalır.")) return;
      return this.call(`adimlar/${step}/reddet`,{not:note},done("Reddedildi; adım hazır."));
    }
    if(!note.trim()) {this.message="Düzeltme isterken not zorunlu: neyin nasıl değişmesi gerektiğini yazın.";return this.rerender();}
    return this.ask(()=>api(this.path(`adimlar/${step}/duzeltme/tahmin`),{method:"POST",body:JSON.stringify({not:note})}),"Düzeltme iste: başlat",
      ()=>this.call(`adimlar/${step}/duzeltme`,{not:note},done(step==="kontrol"?"Düzeltme notu 4 · Yazım adımına gönderildi; o adım hazır.":"Düzeltme istendi; Claude çalışıyor.")));
  }
}
