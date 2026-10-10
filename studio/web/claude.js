import {api, esc} from "./api.js";

// GÖREV-13: Settings → Claude: Claude Code's path and version, the API key warning, the general default model and effort, and per step the
// model, effort ("Genel varsayılan" inherits) and turn limit. Saved in the data folder (ayarlar.json); nothing secret.
export function choiceOptions(items, selected) {
  return items.map(item=>`<option value="${esc(item.value)}" ${item.value===selected?"selected":""}>${esc(item.label)}</option>`).join("");
}

export function claudeSection(view, message="") {
  const {settings, options, info, notes}=view;
  const inherit=[options.inherit];
  const steps=options.steps.map(step=>`<tr><td>${esc(step.label)}</td>
    <td><select data-field="${esc(step.model_field)}" aria-label="${esc(step.label)} modeli">${choiceOptions([...inherit,...options.models],settings[step.model_field])}</select></td>
    <td><select data-field="${esc(step.effort_field)}" aria-label="${esc(step.label)} eforu">${choiceOptions([...inherit,...options.efforts],settings[step.effort_field])}</select></td>
    <td><input type="number" data-field="${esc(step.max_turns_field)}" min="${options.max_turns.min}" max="${options.max_turns.max}" value="${esc(settings[step.max_turns_field])}" aria-label="${esc(step.label)} en fazla tur"></td></tr>`).join("");
  return `<section class="info-card claude-settings" id="claude-settings"><span class="eyebrow">CLAUDE</span><h2 style="margin-top:12px">Claude</h2>
    <p>Program, video adımları için bilgisayardaki Claude Code'u arka planda çağırır; kendi talimatını verir ve yalnız o adımın klasöründe okuyup tek çıktı dosyasını yazmasına izin verir. Abonelik girişiniz kullanılır.</p>
    <div class="path">${info.found?`Bulunan program: ${esc(info.path)}<br>Sürüm: ${esc(info.version || "okunamadı")}`:"Claude Code bulunamadı. Kurulu değilse kurun ya da yolunu aşağıya yazın."}</div>
    ${info.api_key_warning?`<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${esc(info.api_key_warning)}</span></p>`:""}
    ${(notes||[]).map(n=>`<p class="stage-note">${esc(n)}</p>`).join("")}
    <form id="claude-form">
      <label>Claude Code yolu (boşsa kendiliğinden aranır)<input data-field="claude_path" value="${esc(settings.claude_path)}" placeholder="C:\\Users\\…\\claude.exe"></label>
      <div class="form-grid"><label>Genel varsayılan model<select data-field="claude_model">${choiceOptions(options.models,settings.claude_model)}</select></label>
      <label>Genel varsayılan efor<select data-field="claude_effort">${choiceOptions(options.efforts,settings.claude_effort)}</select></label></div>
      <div class="table-scroll"><table class="reference-table"><thead><tr><th>ADIM</th><th>MODEL</th><th>EFOR</th><th>EN FAZLA TUR</th></tr></thead><tbody>${steps}</tbody></table></div>
      <p class="muted form-note">${esc(options.max_turns.help)}</p>
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
      <button class="primary" type="submit">Claude ayarlarını kaydet</button>
    </form></section>`;
}

export function formValues(form) {
  const values={};
  form.querySelectorAll("[data-field]").forEach(el=>{values[el.dataset.field]=el.type==="number"?Number(el.value):el.value;});
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
