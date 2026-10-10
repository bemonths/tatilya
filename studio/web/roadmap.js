export const roadmap = {
  collect: {headline:"Kaynağın biçimine göre veri toplama", description:"Her site için ayrı bir veri toplayıcı. Ham kayıt, kaynak adresi ve çekim zamanı birlikte saklanacak.", cards:[
    ["01 · KAYNAK", "Bağlantıyı kur", "API, JSON, HTML veya gerektiğinde Playwright ile tarayıcıdan okuma."],
    ["02 · KAYIT", "Ham veriyi koru", "Her çekimi tarihli bir sürüm olarak kaydetme; eski kayıtları koruma."],
    ["03 · TAKİP", "İşi izle", "İlerleme, kaynak bazında hata, yeniden deneme ve iptal."]]},
  research: {headline:"30A verisinden içerik konuları", description:"Bölge, dönem ve okuyucu ihtiyacını birleştirerek dayanağı olan konu adayları hazırlanacak.", cards:[
    ["GİRDİ", "Kontrol edilmiş veri", "Kaynaklı ve tarihli kayıtlar, eksikler ve bölge karşılaştırmaları."],
    ["ÇALIŞMA", "Konu önerileri", "Claude bağlantısı ile başlık, açı ve hedef kitle önerileri."],
    ["ÇIKTI", "Seçilen konu", "Her önerinin veri dayanağı görülecek; seçimi siz yapacaksınız."]]},
  competitors: {headline:"İçerikte eksik kalan soruları bul", description:"Seçilen konu için YouTube ve web içeriklerini karşılaştırarak kapsam boşlukları çıkarılacak.", cards:[
    ["GİRDİ", "Rakip içerik listesi", "Bağlantı, başlık, yayın tarihi ve araştırma notları."],
    ["ÇALIŞMA", "Kapsam karşılaştırması", "Ortak başlıklar, eksik açıklamalar ve güncelliğini yitiren bilgiler."],
    ["ÇIKTI", "İçerik fırsatları", "Kaynak gösteren karşılaştırma raporu ve araştırılacak sorular."]]},
  brief: {headline:"Yazmaya başlamadan kapsamı netleştir", description:"Konu, okuyucu, anlatım açısı ve kullanılacak veriler tek bir briefte toplanacak.", cards:[
    ["GİRDİ", "Konu ve araştırma", "Seçilen konu, rakip bulguları ve doğrulanmış veri paketi."],
    ["ÇALIŞMA", "Bölüm planı", "Ana mesaj, bölüm sırası ve her bölümün kaynakları."],
    ["ÇIKTI", "Onaylanmış brief", "Düzenleme ve onaydan sonra makale aşamasına geçiş."]]},
  article: {headline:"Kaynakları izlenebilen bir makale", description:"Onaylı brief üzerinden taslak üretilecek; sayılar, tarihler ve iddialar kaynak kayıtlarıyla karşılaştırılacak.", cards:[
    ["GİRDİ", "Onaylı brief", "Kapsam ve kullanılmasına karar verilen veriler."],
    ["ÇALIŞMA", "Yazım ve denetim", "Taslak, kaynak kontrolü ve düzenleme döngüsü."],
    ["ÇIKTI", "Makale sürümleri", "Önceki sürümleri koruyan, düzenlenebilir metin."]]},
  check: {headline:"Video metnini veriyle karşılaştır", description:"Video metnindeki sayılar, tarihler ve iddialar veri paketindeki satırlarla karşılaştırılacak; kaynağın söylemediği bir şey metinde kalmayacak.", cards:[
    ["GİRDİ", "Video metni ve veri paketi", "Metnin son sürümü ve videonun kanıt paketi."],
    ["ÇALIŞMA", "Kesin kontroller", "Sayı, tarih ve kaynak denetimi; Claude ile anlam kontrolü."],
    ["ÇIKTI", "Kontrol raporu", "Düzeltilmesi gereken yerler ve açık sorunlar listesi."]]},
  visuals: {headline:"Anlatıyı sahnelere dönüştür", description:"Makalenin her bölümü için görsel, grafik, harita ve video ihtiyaçları belirlenecek.", cards:[
    ["GİRDİ", "Makale", "Son metin ve metindeki kaynaklı sayısal bilgiler."],
    ["ÇALIŞMA", "Sahne planı", "Sahne amacı, görsel türü, süre ve gereken varlıklar."],
    ["ÇIKTI", "Görsel listesi", "Varlıkların dosya, kaynak ve kullanım bilgileri."]]},
  video: {headline:"Sahneleri tek bir üretimde birleştir", description:"Görsel plan tamamlandıktan sonra zaman çizelgesi, ses, altyazı ve render süreçleri eklenecek.", cards:[
    ["GİRDİ", "Sahneler ve varlıklar", "Onaylanan görseller, metin, ses ve süre bilgileri."],
    ["ÇALIŞMA", "Kurgu ve önizleme", "Sahneleri ayrı ayrı izleme ve üretim ayarları."],
    ["ÇIKTI", "Video dosyası", "İlerleme takibi olan render işi ve yerel çıktı."]]},
  publish: {headline:"Yayın için eksiksiz bir paket", description:"Makale, video, başlık, açıklama ve görseller yayın öncesi bir araya getirilecek.", cards:[
    ["GİRDİ", "Üretim çıktıları", "Onaylanmış makale, video ve görseller."],
    ["ÇALIŞMA", "Son kontrol", "Eksik varlıklar, kaynaklar, başlık ve açıklama kontrolü."],
    ["ÇIKTI", "Yayın paketi", "Dışa aktarılabilir dosyalar. Otomatik yayın ayrı bir aşama."]]}
};
