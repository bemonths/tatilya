import {api, esc} from "./api.js";
import {tokens} from "./estimate.js";

// GÖREV-13: Settings → Claude: Claude Code's path and version, the API key warning, the general default model and effort, and per step the
// model, effort ("Genel varsayılan" inherits); GÖREV-18: the median spending of each step's last runs beside its model, the output guess of
// the estimate, the token limits of one call and one job (no turn limit: every step is one call). Saved in the data folder (ayarlar.json).
export function choiceOptions(items, selected) {
  return items.map(item=>`<option value="${esc(item.value)}" ${item.value===selected?"selected":""}>${esc(item.label)}</option>`).join("");
}

/** The median spending of a step's last runs for the model table (GÖREV-18 Adım 5): the one-call way's, else the old way's marked. */
export function medianText(row) {
  if(!row) return "—";
  if(row.yeni?.sayi) return `${tokens(row.yeni.ortanca)} (${row.yeni.sayi} çalışma)`;
  if(row.eski?.sayi) return `${tokens(row.eski.ortanca)} (eski düzen, ${row.eski.sayi})`;
  return "henüz yok";
}

export function limitFields(settings, limits) {
  const labels={claude_call_limit:"Tek çağrı sınırı (token)", claude_job_limit:"İş başına toplam sınır (token)"};
  return `<h3 style="margin-top:18px">Token sınırları</h3><div class="form-grid limit-settings">${(limits||[]).map(f=>`<label>${esc(labels[f.field] || f.field)}<input type="number" data-field="${esc(f.field)}" min="${f.min}" max="${f.max}" step="1000" value="${esc(settings[f.field])}"><span class="muted form-note">${esc(f.help)}</span></label>`).join("")}</div>`;
}

export function claudeSection(view, message="") {
  const {settings, options, info, notes}=view;
  const inherit=[options.inherit];
  const spending=Object.fromEntries((view.harcama||[]).map(row=>[row.adim,row]));
  const steps=options.steps.map(step=>`<tr><td>${esc(step.label)}</td>
    <td><select data-field="${esc(step.model_field)}" aria-label="${esc(step.label)} modeli">${choiceOptions([...inherit,...options.models],settings[step.model_field])}</select></td>
    <td><select data-field="${esc(step.effort_field)}" aria-label="${esc(step.label)} eforu">${choiceOptions([...inherit,...options.efforts],settings[step.effort_field])}</select></td>
    <td class="median-cell">${esc(medianText(spending[step.key]))}</td>
    <td><input type="number" data-field="${esc(step.output_guess_field)}" min="${options.output_guess?.min ?? 500}" max="${options.output_guess?.max ?? 128000}" step="500" value="${esc(settings[step.output_guess_field])}" aria-label="${esc(step.label)} çıktı varsayımı"></td></tr>`).join("");
  return `<section class="info-card claude-settings" id="claude-settings"><span class="eyebrow">CLAUDE</span><h2 style="margin-top:12px">Claude</h2>
    <p>Program, video adımları için bilgisayardaki Claude Code'u arka planda çağırır. Her adım tek bir çağrıdır: program adımın bütün malzemesini istemin içinde verir, Claude hiçbir araç kullanmadan tek turda cevabı yazar, program cevabı denetleyip kaydeder. Abonelik girişiniz kullanılır.</p>
    <div class="path">${info.found?`Bulunan program: ${esc(info.path)}<br>Sürüm: ${esc(info.version || "okunamadı")}`:"Claude Code bulunamadı. Kurulu değilse kurun ya da yolunu aşağıya yazın."}</div>
    ${info.api_key_warning?`<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${esc(info.api_key_warning)}</span></p>`:""}
    ${(notes||[]).map(n=>`<p class="stage-note">${esc(n)}</p>`).join("")}
    <form id="claude-form">
      <label>Claude Code yolu (boşsa kendiliğinden aranır)<input data-field="claude_path" value="${esc(settings.claude_path)}" placeholder="C:\\Users\\…\\claude.exe"></label>
      <div class="form-grid"><label>Genel varsayılan model<select data-field="claude_model">${choiceOptions(options.models,settings.claude_model)}</select></label>
      <label>Genel varsayılan efor<select data-field="claude_effort">${choiceOptions(options.efforts,settings.claude_effort)}</select></label></div>
      <div class="table-scroll"><table class="reference-table model-table"><thead><tr><th>ADIM</th><th>MODEL</th><th>EFOR</th><th>SON ÇALIŞMALARIN ORTANCASI</th><th>ÇIKTI VARSAYIMI</th></tr></thead><tbody>${steps}</tbody></table></div>
      <p class="muted form-note">Ortanca, adımın son başarılı çalışmalarının okunan ve yazılan toplam token'ıdır; “eski düzen” çok turlu eski çalışmalardır. ${esc(options.output_guess?.help || "")}</p>
      ${limitFields(settings, options.limits)}
      ${textSettings(settings, options.text)}
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
      <button class="primary" type="submit">Claude ayarlarını kaydet</button>
    </form></section>`;
}

const TEXT_LABELS={claude_max_sessions:"Aynı anda en çok Claude oturumu", claude_limit_five_hour:"5 saatlik pencere eşiği (%)", claude_limit_week:"Haftalık pencere eşiği (%)"};

/** GÖREV-15: the video text chain's settings — sessions at once, the usage thresholds and "Plandan sonra dur". */
export function textSettings(settings, text) {
  if(!text) return "";
  const fields=text.fields.map(f=>`<label>${esc(TEXT_LABELS[f.field] || f.field)}<input type="number" data-field="${esc(f.field)}" min="${f.min}" max="${f.max}" value="${esc(settings[f.field])}"><span class="muted form-note">${esc(f.help)}</span></label>`).join("");
  const stop=text.stop_after_plan;
  return `<h3 style="margin-top:18px">Video metni çalışması</h3><div class="form-grid text-settings">${fields}
    <label class="checkbox-label"><input type="checkbox" data-field="${esc(stop.field)}" ${settings[stop.field]?"checked":""}> Plandan sonra dur<span class="muted form-note">${esc(stop.help)}</span></label></div>`;
}

// GÖREV-14 (Adım 4e): the destination's title suffixes. The program writes them into every title and evaluation run and checks every title.
export function suffixSection(view, message="") {
  const shown=value=>`"${esc(value)}"`;
  return `<section class="info-card suffix-settings" id="suffix-settings"><span class="eyebrow">BAŞLIK EKİ</span><h2 style="margin-top:12px">Başlık eki</h2>
    <p>Her önerilen ve düzenlenen başlık bu eklerle biter. Program ekleri her başlık ve değerlendirme çalışmasında Claude'a verir ve bitişte denetler. Ekin başındaki boşluk da ekin parçasıdır.</p>
    <form id="suffix-form"><label>İngilizce başlık eki<input data-suffix="en" value="${esc(view.en)}" maxlength="40"></label>
      <label>Türkçe başlık eki<input data-suffix="tr" value="${esc(view.tr)}" maxlength="40"></label>
      <p class="muted form-note">Başlangıç değerleri: İngilizce ${shown(view.defaults?.en || "")}, Türkçe ${shown(view.defaults?.tr || "")}.</p>
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
      <button class="primary" type="submit">Başlık ekini kaydet</button></form></section>`;
}

export async function renderSuffixSettings(container, message="") {
  try {
    const view=await api("settings/title-suffix");
    container.innerHTML=suffixSection(view, message);
    container.querySelector("#suffix-form").addEventListener("submit",async event=>{
      event.preventDefault();
      const values={};event.target.querySelectorAll("[data-suffix]").forEach(el=>{values[el.dataset.suffix]=el.value;});
      try {
        await api("settings/title-suffix",{method:"PUT",body:JSON.stringify(values)});
        await renderSuffixSettings(container,"Başlık eki kaydedildi; bundan sonraki çalışmalarda kullanılır.");
      } catch(error) {if(!error.stale) await renderSuffixSettings(container,error.message);}
    });
  } catch(error) {if(!error.stale) container.textContent=error.message;}
}

export function formValues(form) {
  const values={};
  form.querySelectorAll("[data-field]").forEach(el=>{values[el.dataset.field]=el.type==="checkbox"?el.checked:el.type==="number"?Number(el.value):el.value;});
  return values;
}

export async function renderClaudeSettings(container, message="") {
  try {
    const view=await api("settings/claude");
    container.innerHTML=claudeSection(view, message);
    container.querySelector("#claude-form").addEventListener("submit",async event=>{
      event.preventDefault();
      try {
        await api("settings/claude",{method:"PUT",body:JSON.stringify(formValues(event.target))});
        await renderClaudeSettings(container,"Claude ayarları kaydedildi.");
      } catch(error) {if(!error.stale) await renderClaudeSettings(container,error.message);}
    });
  } catch(error) {if(!error.stale) container.textContent=error.message;}
}
