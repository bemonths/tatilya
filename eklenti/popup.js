// 30A Studio Yardımcısı — açılır pencere: programla eşleşme, site izinleri, son iş.
import {originPatterns, permittedDomains} from "./logic.js";

const $ = selector => document.querySelector(selector);
const text = (selector, value) => { $(selector).textContent = value; };
const PROGRAM_STATES = {bagli: port => `Bağlı (127.0.0.1:${port}).`, bulunamadi: () => "30A Studio programı bulunamadı. Program açık mı?",
  eslesmedi: () => "Eşleşme kodu yazılmadı.", hata: () => "Programla konuşulamadı."};

async function draw() {
  const state = await chrome.storage.local.get(["kod", "port", "durum", "izinBekleyen", "sonIs"]);
  const durum = state.durum || {};
  const describe = PROGRAM_STATES[durum.program];
  text("#program", describe ? describe(durum.port) + (durum.mesaj ? ` ${durum.mesaj}` : "") : "Bakılıyor…");
  text("#eslesme", state.kod ? `Eşleşti (kod ${state.kod}). Kod değiştiyse yenisini aşağıya yazın.` : "Henüz eşleşmedi.");
  const granted = (await chrome.permissions.getAll()).origins || [];
  const allowed = permittedDomains(granted);
  $("#izinli").innerHTML = "";
  for (const domain of allowed) {
    const li = document.createElement("li");
    li.textContent = domain;
    const remove = document.createElement("button");
    remove.textContent = "İzni kaldır";
    remove.className = "quiet";
    remove.addEventListener("click", async () => { await chrome.permissions.remove({origins: originPatterns(domain)}); draw(); });
    li.append(" ", remove);
    $("#izinli").append(li);
  }
  if (!allowed.length) $("#izinli").innerHTML = '<li class="muted">Yok.</li>';
  $("#bekleyen").innerHTML = "";
  const waiting = (state.izinBekleyen || []).filter(domain => !allowed.includes(domain));
  for (const domain of waiting) {
    const li = document.createElement("li");
    li.textContent = domain;
    const allow = document.createElement("button");
    allow.textContent = "İzin ver";
    allow.addEventListener("click", async () => {
      const ok = await chrome.permissions.request({origins: originPatterns(domain)});   // Chrome asks the user; the extension cannot grant itself
      if (ok) chrome.runtime.sendMessage({tur: "sor"});
      draw();
    });
    li.append(" ", allow);
    $("#bekleyen").append(li);
  }
  if (!waiting.length) $("#bekleyen").innerHTML = '<li class="muted">Yok.</li>';
  const last = state.sonIs;
  text("#son-is", last ? `${last.alan_adi} · ${last.amac || "iş"} · ${last.durum} · ${new Date(last.zaman).toLocaleString("tr-TR")}` : "Henüz iş yok.");
}

$("#kod-formu").addEventListener("submit", async event => {
  event.preventDefault();
  text("#eslesme-sonuc", "Eşleşiyor…");
  const answer = await chrome.runtime.sendMessage({tur: "eslestir", kod: $("#kod").value});
  text("#eslesme-sonuc", answer?.ok ? "Eşleşti. Program artık bu eklentiye iş verebilir." : (answer?.mesaj || "Eşleşemedi."));
  draw();
});

chrome.storage.onChanged.addListener(draw);
draw();
