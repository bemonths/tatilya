import {api, esc, date} from "./api.js";
import {STATUS_TONE} from "./workflow.js";

// GÖREV-21: the "Videolar" screen (project layer; after Rota Stüdyo's Videolar screen). The project's videos: the chosen title's Turkish
// large and its English small and pale, the creation date, the step progress ("3/8"); "Yeni video" with an optional working name (the
// title is chosen from the bank or written in the video's first step); a video opens with a click; "Arşive kaldır" takes a video off
// the list and "Arşivdekileri göster" shows the archived ones. Nothing is deleted.

export function videoRow(video, {open=false, archived=false}={}) {
  const title=video.baslik_tr || video.calisma_adi || "Adsız video";
  return `<li class="video-row ${open?"open":""}" data-video="${esc(video.id)}"><button type="button" class="video-row-main" data-open-video="${esc(video.id)}" ${archived?"disabled":""} title="${archived?"Arşivdeki video açılmaz; önce arşivden çıkarın.":"Videoyu aç"}">
      <span class="title-tr-big">${esc(title)}</span>
      ${video.baslik_en?`<span class="title-en-small" lang="en">${esc(video.baslik_en)}</span>`:'<span class="title-en-small">Başlık henüz seçilmedi (1 · Başlık ve vaat)</span>'}
      <span class="video-row-meta">${video.baslik_tr && video.calisma_adi?`çalışma adı: ${esc(video.calisma_adi)} · `:""}${video.bolge?`${esc(video.bolge)} · `:""}oluşturuldu ${esc(date(video.olusturuldu))}${archived?` · arşive kaldırıldı ${esc(date(video.arsivlendi))}`:""}</span></button>
    <div class="video-row-side"><span class="video-progress" title="Tamamlanan adım / toplam adım">${esc(video.ilerleme)}</span>
      <span class="tag ${STATUS_TONE[video.siradaki.durum] || ""}">${esc(video.siradaki.ad)}: ${esc(video.siradaki.durum_adi)}</span>${open?'<span class="tag green">açık</span>':""}
      ${archived?`<button type="button" class="quiet" data-unarchive="${esc(video.id)}">Arşivden çıkar</button>`:`<button type="button" class="quiet" data-archive="${esc(video.id)}">Arşive kaldır</button>`}</div></li>`;
}

export function videoList(list, form={name:""}, message="") {
  const videos=list?.videolar || [];
  const empty=list?.arsiv?"Arşivde video yok.":"Henüz video yok. “Yeni video” ile boş bir video açabilir ya da Konu bankasında bir adayın “Bu başlıkla video aç” düğmesine basabilirsiniz.";
  return `<section class="library evidence-form new-video"><div class="library-title"><h2>Yeni video</h2><small>başlık videonun 1. adımında bankadan seçilir ya da yazılır</small></div>
      <form id="new-video-form" class="toolbar video-form"><label class="grow">Çalışma adı (isteğe bağlı) <input id="new-video-name" maxlength="120" value="${esc(form.name)}" placeholder="Örn. Rosemary Beach kış videosu"></label>
      <button type="submit" class="primary" id="new-video">Yeni video</button><a class="source-link" href="#konu">Konu bankasından aç →</a></form>
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}</section>
    <section class="library"><div class="library-title"><h2>${list?.arsiv?"Arşivdeki videolar":"Projenin videoları"}</h2><small>${videos.length} video</small></div>
      ${videos.length?`<ul class="video-rows">${videos.map(v=>videoRow(v,{open:v.id===list.acik,archived:list.arsiv})).join("")}</ul>`:`<p class="muted run-empty">${esc(empty)}</p>`}
      <p class="run-empty">${list?.arsiv?'<a class="link-button" href="#videolar">← Projenin videoları</a>':`<a class="link-button" href="#videolar/arsiv" id="show-archived">Arşivdekileri göster (${list?.arsivdeki ?? 0})</a>`}</p></section>`;
}

export class VideoListScreen {
  constructor() {this.list=null;this.sequence=0;this.message="";this.form={name:""};}
  invalidate() {this.sequence++;}
  render(main, data, heading, archived=false) {
    const sequence=++this.sequence;
    this.archived=archived;
    main.innerHTML=heading("Videolar", `${data.selected_destination?.name || "Proje"} projesinin videoları. Bir videoya tıklayınca açılır ve sol menüde yalnız o videonun adımları görünür.`)+
      '<div id="video-list-body" aria-live="polite"><p>Yükleniyor…</p></div>';
    api(`videolar${archived?"?arsiv=true":""}`).then(list=>{
      if(sequence!==this.sequence) return;
      this.list=list;this.draw(main);
    }).catch(error=>{if(sequence===this.sequence && !error.stale) main.querySelector("#video-list-body").textContent=error.message;});
  }
  draw(main) {
    const body=main.querySelector("#video-list-body");
    if(!body || !this.list) return;
    body.innerHTML=videoList(this.list,this.form,this.message);
    body.querySelector("#new-video-name").addEventListener("input",event=>{this.form.name=event.target.value;});
    body.querySelector("#new-video-form").addEventListener("submit",event=>{event.preventDefault();this.create(main);});
    body.querySelectorAll("[data-open-video]").forEach(button=>button.addEventListener("click",()=>
      document.dispatchEvent(new CustomEvent("studio:video-opened",{detail:{id:button.dataset.openVideo}}))));
    body.querySelectorAll("[data-archive]").forEach(button=>button.addEventListener("click",()=>this.archive(main,button.dataset.archive,true)));
    body.querySelectorAll("[data-unarchive]").forEach(button=>button.addEventListener("click",()=>this.archive(main,button.dataset.unarchive,false)));
  }
  async create(main) {
    try {
      const video=await api("videolar",{method:"POST",body:JSON.stringify({ad:this.form.name})});
      this.form.name="";this.message="";
      document.dispatchEvent(new CustomEvent("studio:video-opened",{detail:{id:video.id,step:"baslik"}}));
    } catch(error) {if(error.stale) return;this.message=error.message;this.draw(main);}
  }
  async archive(main, videoId, archived) {
    if(archived && globalThis.confirm && !globalThis.confirm("Video arşive kaldırılsın mı? Hiçbir şey silinmez; “Arşivdekileri göster” ile geri getirebilirsiniz.")) return;
    try {
      await api(`videos/${encodeURIComponent(videoId)}/${archived?"arsivle":"arsivden-cikar"}`,{method:"POST",body:"{}"});
      this.message=archived?"Video arşive kaldırıldı.":"Video arşivden çıkarıldı.";
      this.list=await api(`videolar${this.archived?"?arsiv=true":""}`);
      document.dispatchEvent(new CustomEvent("studio:videos-changed"));
    } catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw(main);
  }
}
