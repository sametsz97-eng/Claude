# Videoyu Adım Adım Üretme Rehberi

Bu klasördeki dosyalar:
- `senaryo.md`: Sahne planı ve yapay zekâ promptları (8. bölüm)
- `altyazi.srt`: Türkçe altyazı
- `animatik/animatik.mp4`: Zamanlaması doğru taslak video. Gerçek klipleri bunun üstüne yerleştireceksin.

Toplam süre: **64 sn**. Aşağıdaki sırayı takip et.

---

## ADIM 1: Sahne kliplerini üret (Görüntü)

**Önerilen araçlar:** Google Veo (Gemini uygulaması veya Google Flow), Kling AI, Runway, OpenAI Sora. Hepsinde ücretsiz deneme veya aylık abonelik var.

1. Önce **karakterin referans fotoğrafını** üret. Bir görsel aracına (ChatGPT, Gemini, Midjourney) şunu yaz:
   > Portrait photo of a 20-year-old Turkish university student, average healthy build, shoulder-length dark brown hair loosely tied, no makeup, oversized grey sweatshirt, light blue jeans, natural light, realistic, vertical 9:16
   Beğendiğin görseli kaydet. **Bütün sahnelerde bu görseli kullan.** Böylece karakter her sahnede aynı kişi gibi görünür.
2. Video aracında **"Image to Video"** (görselden video) modunu seç ve referans görseli yükle.
3. En-boy oranını **9:16** yap.
4. `senaryo.md` dosyasının 8. bölümünden sırayla şunları yapıştır: **ortak karakter tanımı**, ardından **sahnenin promptu**. Araçta "negative prompt" alanı varsa ortak negatif promptu oraya yaz.
5. Her sahne için 2–3 deneme üret, en doğal görüneni seç.
6. Klipleri `01.mp4`, `02.mp4` … `11.mp4` diye adlandır.

**Kontrol:** Tartının ekranında okunabilir bir rakam çıktıysa o klibi kullanma ya da kurgu sırasında o bölgeyi bulanıklaştır.

**İpucu:** Diyalog sahnelerinde (2, 4, 6) karakterin konuşurken ağzını gösterme. Yan profil, el veya fincan yakın planı seç; sesi sonradan ekleyeceksin.

---

## ADIM 2: Seslendirme (Ses)

**Seçenek A: Kendi sesin (ücretsiz, en doğal sonuç)**
1. Sessiz bir odada telefonu ağzından ~20 cm uzakta tut.
2. Anlatıcı metnini `senaryo.md` dosyasındaki 3. bölümün yönergelerine göre yavaş ve sakin oku.
3. Her paragrafı ayrı kaydet: `vo1` … `vo6`.

**Seçenek B: Yapay zekâ sesi (ElevenLabs)**
1. elevenlabs.io → Text to Speech.
2. Model olarak **Multilingual** modeli seç; dil Türkçe. Sakin bir kadın sesi seç.
3. Ayarlar: Stability ~%50, Style düşük.
4. Her paragrafı ayrı üret. Final cümlesinde "istiyorsun"dan sonra durak olması için metne "…" ekle.

**Karakter replikleri** (Defne, Anne, Ece): Bunları gerçek kişilere okut (bir arkadaş, bir aile büyüğü). Yapay zekâ sesi de olur ama her karakter için farklı bir ses seç.

---

## ADIM 3: Müzik

- Instagram'da yayınlarken uygulamanın müzik kütüphanesinden ekleyebilirsin. "sad piano" veya "emotional ambient" diye ara. **Ya da**
- Kurgu programının telifsiz müzik kütüphanesini kullan (CapCut'ta "Müzik → Duygusal / Piyano").
- Davulu ve dramatik yükselişi olan parçaları seçme.

---

## ADIM 4: Kurgu (CapCut ile, telefonda veya bilgisayarda)

1. CapCut → **Yeni proje** → önce `animatik.mp4` dosyasını ekle. Bu senin zaman cetvelin.
2. Kanvas oranını **9:16** yap.
3. Klipleri animatiğin üstündeki katmana yerleştir. Her klibi animatikte o sahnenin başladığı saniyeye hizala:

| Klip | Başlangıç | Bitiş |
|---|---|---|
| 01 | 0:00 | 0:03 |
| 02 | 0:03 | 0:06 |
| 03 | 0:06 | 0:12 |
| 04 | 0:12 | 0:16 |
| 05 | 0:16 | 0:23 |
| 06 | 0:23 | 0:28 |
| 07 | 0:28 | 0:33 |
| 08 | 0:33 | 0:43 |
| 09 | 0:43 | 0:49 |
| 10 | 0:49 | 0:59 |
| 11 | 0:59 | 1:04 |

4. Tüm klipler yerleştikten sonra **animatik katmanını sil** (ya da sesini kapatıp gizle).
5. Seslendirme ve replik dosyalarını ekle. Altyazıyla aynı anda başlamalılar. `altyazi.srt` dosyasındaki zamanlara bak.
6. Müziği ekle ve ses seviyesini düşür (~%15–20). Konuşma olan yerlerde müzik daha da kısık olsun. 0:49–0:51 arasında müziği tamamen kes.
7. **Altyazı:** CapCut → Metin → **Otomatik altyazı** (Türkçe), ya da `altyazi.srt` dosyasını içe aktar (bilgisayar sürümünde: Metin → Altyazıları içe aktar). Yazı tipi beyaz ve kalın, hafif gölgeli olsun. Altyazıları ekranın alt %20'lik kısmının hemen üstüne koy.
8. **Açılış yazısı (0:00–0:03):** Ortaya büyük harflerle *“Biraz daha kilo verirsem kendimi seveceğim.”*
9. **Kapanış kartı (0:59–1:04):** Siyah arka plan, ortada ana metin, altta küçük punto bilgi notu. Metinler `senaryo.md` dosyasında.
10. Renk: "Film" ya da soğuk tonlu bir filtre seç, yoğunluğunu ~%30 yap. Gece sahnelerini biraz daha mavi yap.
11. **Dışa aktar:** 1080×1920, 30 fps, en yüksek kalite. Süre **65 saniyeden kısa** olmalı.

---

## ADIM 5: Yayın öncesi kontrol

- [ ] Hiçbir karede tartıdaki rakam okunmuyor
- [ ] Aşırı zayıf beden görüntüsü yok
- [ ] Süre 65 saniyenin altında
- [ ] Altyazılar Instagram arayüzünün (beğen ve yorum butonları) altında kalmıyor
- [ ] Açıklamada destek bilgisi var (`senaryo.md` → 7. bölüm)
- [ ] Mümkünse bir ruh sağlığı uzmanına izlettin

---

## Yalnızca telefonla, gerçek çekim yapmak istersen
Yapay zekâ yerine bir arkadaşını oyuncu olarak kullanabilirsin. Senaryodaki sahneleri telefonla dikey çek. Doğal ışık kullan (pencere kenarı). Telefonu sabit tut ya da yavaşça hareket ettir. Sonra 4. adımdan devam et. Bu yöntem çoğu zaman yapay zekâdan **daha gerçekçi** sonuç verir ve bu konu için daha etkileyicidir.
