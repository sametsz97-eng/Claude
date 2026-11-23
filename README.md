# Anonim Sohbet (Flutter + Supabase)

Bire bir, anonim, kız–erkek eşleşmeli sohbet uygulaması. Arayüz Türkçe.

- **Giriş:** SMS ile telefon doğrulama (Supabase Auth). Numara hiçbir kullanıcıya gösterilmez. Herkese rastgele bir takma ad ve emoji verilir ("Sessiz Martı 🐦"); takma ad bir kez yeniden üretilebilir.
- **Onay:** 18 yaş onayı ve KVKK açık rızası, sürüm numarasıyla birlikte kaydedilir.
- **Cinsiyet ve selfie doğrulama:** `VerificationService` arayüzü ve şimdilik mock implementasyonu var; Yoti/FaceTec sonra bağlanacak. Fotoğraf saklanmaz, sadece `gender_verified=true` yazılır.
- **Eşleşme:** Her sohbet bir kız ve bir erkek arasında kurulur, bu yüzden aktif sohbetlerde iki cinsiyetin sayısı hep eşittir. Fazla olan taraf kuyrukta bekler ve tahmini süreyi görür. Mantık SQL RPC içinde, row lock (`FOR UPDATE SKIP LOCKED`) ile çalışır.
- **Sohbet:** Supabase Realtime kullanılır. Engellenen kişiyle bir daha eşleşme olmaz. Art arda aynı kişiyle de eşleşilmez.
- **Arkadaşlık:** Sohbet ettiğin kişiye arkadaşlık isteği gönderebilirsin; karşı taraf kabul edince arkadaş olursunuz. İki taraf birbirine istek gönderirse otomatik kabul edilir. Günde en fazla **3 istek** gönderilebilir (Türkiye saatiyle gece yarısı yenilenir). Arkadaşlar listeden ya da sohbet ekranından "Arkadaşlıktan çıkar" ile silinebilir; silme iki taraf için de arkadaşlığı ve mesaj geçmişini kaldırır, günlük hakkı geri vermez. Engelleme ve şikâyet arkadaşlığı da kaldırır; arkadaş sohbetinden gelen şikâyetler aynı ban sayacına işlenir.
- **Şikâyet:** Kategoriler taciz, küfür, +18 ve cinsiyeti farklı. Sadece farklı kişilerden gelen şikâyetler sayılır ve sayaç ömür boyudur. 3 şikâyette 24 saat, 6'da 7 gün, 9'da kalıcı ban. Son doğrulamadan sonra 3 farklı kişi "cinsiyeti farklı" derse yeniden doğrulama gerekir. Ban telefon numarası (hash) ve cihaz kimliğine (hash) bağlanır.

## Klasör yapısı

```
supabase/
  config.toml                         # yerel Supabase CLI ayarları (SMS test OTP'leri dahil)
  migrations/                         # şema, RPC'ler, RLS, realtime
  functions/confirm-verification/     # verified=true yazan tek yer (service role)
  tests/run_local.sh                  # migration + SQL akış testleri + eşzamanlılık testi
app/                                  # Flutter uygulaması
  lib/core/                           # config, hata metinleri, telefon/cihaz yardımcıları
  lib/services/app_session.dart       # oturum durumu (router bunu dinler)
  lib/router.dart                     # onboarding yönlendirme kuralları
  lib/features/...                    # auth, onboarding, verification, matching, chat, ban
```

## Veri modeli (özet)

| Tablo | İçerik | İstemci erişimi |
|---|---|---|
| `public.profiles` | takma ad, emoji, cinsiyet, doğrulama, aktif sohbet | sadece kendi satırını okur |
| `public.consents` | 18 yaş + KVKK onay kayıtları (sürümlü) | kendi kayıtlarını okur |
| `public.match_queue` | bekleyenler + heartbeat | kendi satırını okur |
| `public.matches` | bire bir sohbetler | katılımcı okur |
| `public.messages` | mesajlar (Realtime) | katılımcı okur; aktif sohbete kendi adına yazar |
| `public.blocks` | engellemeler | kendi engellediklerini okur |
| `public.friend_requests` | arkadaşlık istekleri (bekliyor / kabul / ret) | gönderen ve alan okur |
| `public.friendships` | arkadaşlıklar (silme: `removed_at`) | iki taraf okur |
| `public.friend_messages` | arkadaş mesajları (Realtime) | iki taraf okur; aktif arkadaşlığa kendi adına yazar |
| `private.identities` | user → telefon HMAC hash'i | **kapalı** |
| `private.devices` | user → cihaz HMAC hash'leri | **kapalı** |
| `private.bans` | user / telefon hash / cihaz hash banları | **kapalı** |
| `private.reports` | şikâyet defteri (telefon hash'iyle, ömür boyu) | **kapalı** |
| `private.verification_attempts` | doğrulama sonuçları (fotoğraf yok) | **kapalı** |

Tüm durum değişiklikleri `SECURITY DEFINER` RPC'lerle yapılır: `bootstrap_session`, `accept_consents`, `set_gender`, `join_queue`, `heartbeat_queue`, `leave_queue`, `get_match`, `end_match`, `block_partner`, `report_partner`, `reroll_nickname`, `delete_account`; arkadaşlık için `send_friend_request`, `respond_friend_request`, `get_friends_overview`, `get_friendship`, `remove_friend`, `block_friend`, `report_friend`. İstemcinin doğrudan yazabildiği tablolar sadece `messages` ve `friend_messages`; ikisi de RLS ile korunur. `admin_mark_verified` ve `admin_ban` fonksiyonlarını sadece `service_role` çağırabilir.

### Eşleşme ve yarış durumları

1. `try_match` önce çağıranın kuyruk satırını `FOR UPDATE` ile kilitler. Ardından karşı cinsten en eski uygun adayı `FOR UPDATE SKIP LOCKED` ile seçer. Uygun aday şu koşulları sağlar: son 30 sn içinde heartbeat göndermiş, aktif sohbette değil, iki yönde de engel yok, son partner değil, banlı değil.
2. Sohbet kaydının açılması, iki kuyruk satırının silinmesi ve `profiles.current_match_id` güncellemesi tek transaction'da yapılır.
3. İki kişi aynı anda birbirini atlarsa bir sonraki heartbeat'te (yaklaşık 5 sn) eşleşirler. Deadlock oluşmaz, çünkü tüm fonksiyonlar aynı kilit sırasını izler: önce kuyruk, sonra sohbet ve profiller.
4. Tahmini süre şöyle hesaplanır: `(kendi cinsiyetindeki sıra − bekleyen karşı cins) / son 10 dk'daki dakikalık eşleşme hızı`.

## Kurulum

### Gerekenler
- [Supabase CLI](https://supabase.com/docs/guides/cli) ve Docker (yerel geliştirme için)
- Flutter 3.50+ (stable). Proje bu sürümle geliştirildi ve test edildi; Material bileşenleri için `package:material_ui` kullanılıyor.
- Üretimde SMS için bir sağlayıcı hesabı (Twilio, Vonage, MessageBird veya Textlocal)

### 1. Yerel Supabase

```bash
supabase start                 # migration'lar otomatik uygulanır
```

Telefon ve cihaz hash'leri için gizli bir pepper ayarlayın. Bu adım zorunlu; ayarlanmazsa `bootstrap_session` hata verir.

```bash
PEPPER=$(openssl rand -hex 32)
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
  -c "insert into private.app_config(key, value) values ('hash_pepper', '$PEPPER')
      on conflict (key) do update set value = excluded.value;"
```

> Pepper'ı bir kez belirleyin ve **asla değiştirmeyin**. Değişirse mevcut banlar artık eşleşmez.

Yerelde gerçek SMS gönderilmez. `config.toml` içindeki test numaralarıyla (`+90 555 000 00 01`, kod `123456`) giriş yapabilirsiniz.

Edge Function'ı mock modunda çalıştırın:

```bash
echo "VERIFICATION_MODE=mock" > supabase/functions/.env
supabase functions serve --env-file supabase/functions/.env
```

### 2. Üretim (Supabase Cloud)

```bash
supabase link --project-ref <proje-ref>
supabase db push                                   # migration'lar
supabase functions deploy confirm-verification
supabase secrets set VERIFICATION_MODE=mock        # Yoti/FaceTec hazır olunca: yoti | facetec
```

Ardından pepper'ı Dashboard → SQL Editor'den yukarıdaki `insert` ile ekleyin.

Dashboard ayarları:
1. **Authentication → Sign In / Providers → Phone:** etkinleştirin ve SMS sağlayıcısını (ör. Twilio) bağlayın. Email girişini kapatın.
2. **Authentication → Rate Limits:** SMS limitlerini kontrol edin.
3. **Project Settings → Data API → Exposed schemas:** sadece `public` olmalı. `private` **eklenmemeli**.
4. **Database → Publications → supabase_realtime:** `messages` ve `matches` tablolarının ekli olduğunu doğrulayın. Migration bunları ekliyor.

> ⚠️ Üretimde `VERIFICATION_MODE=mock` bırakmayın. Mock modunda herkes doğrulanmış sayılır.

### 3. Uygulamayı çalıştır

```bash
cd app
flutter pub get
flutter run \
  --dart-define=SUPABASE_URL=http://127.0.0.1:54321 \
  --dart-define=SUPABASE_PUBLISHABLE_KEY=<supabase status çıktısındaki publishable/anon key>
```

Android emülatöründe yerel Supabase'e erişmek için `SUPABASE_URL=http://10.0.2.2:54321` kullanın.

Kamera izinleri (`NSCameraUsageDescription` ve `android.permission.CAMERA`) eklendi. Mock doğrulama yalnızca canlı önizleme gösterir; hiçbir kare yakalanmaz.

### 4. Testler

```bash
# Veritabanı: migration'lar + uçtan uca akış + arkadaşlık + 60 kullanıcılık eşzamanlı eşleşme testi
# (yerelde PostgreSQL 15+ ikili dosyaları gerekir; Supabase'in auth şeması taklit edilir)
supabase/tests/run_local.sh

# Flutter: telefon normalizasyonu, hata metinleri, yönlendirme kuralları, arkadaş listesi çözümleme
cd app && flutter analyze && flutter test
```

## Yoti / FaceTec entegrasyonu

1. **Flutter:** `VerificationService` arayüzünü uygulayan bir sınıf yazın (ör. `YotiVerificationService`). Sağlayıcının SDK'sını açsın ve sonunda `VerificationResult.success(sessionToken)` dönsün. `usesInAppCameraPreview` değeri `false` olmalı. Ardından `main.dart` içinde `MockVerificationService` yerine bu sınıfı kullanın.
2. **Sunucu:** `supabase/functions/confirm-verification/providers/yoti.ts` (veya `facetec.ts`) dosyasında token'ı sağlayıcının API'sine doğrulatın. Liveness ve tespit edilen cinsiyeti `ProviderResult` olarak döndürün. Anahtarları `supabase secrets set` ile verin.
3. Fotoğraf sizin sunucunuza hiç gelmemeli. İstemci görüntüyü doğrudan sağlayıcıya gönderir, biz sadece sonucu sorgularız.

## Moderasyon

- Manuel ban (service role ile, ör. SQL Editor): `select public.admin_ban('<user-uuid>', 24, 'manual');` Süre saat cinsindendir; `null` kalıcı ban demektir.
- Banı kaldırmak için: `update private.bans set expires_at = now() where user_id = '<uuid>' or phone_hash = (select phone_hash from private.identities where user_id = '<uuid>');`

## Bilinen sınırlar ve notlar

- **Cihaz kimliği** (Android ID, iOS identifierForVendor) fabrika ayarlarına dönünce ya da uygulama yeniden yüklenince değişebilir. Asıl güçlü engel telefon hash'idir.
- **Hesap silme:** Profil, mesajlar ve eşleşmeler silinir. Ban ve şikâyet kayıtları kötüye kullanımı önlemek için hash olarak kalır. Bunu aydınlatma metninde belirtin.
- **KVKK metni** (`app/lib/features/onboarding/kvkk_text.dart`) bir yer tutucudur. Selfie doğrulaması biyometrik veri (özel nitelikli kişisel veri) içerdiği ve Supabase sunucuları yurt dışında olabileceği için metni bir hukukçuya inceletin. Metni değiştirince `AppConfig.consentVersion` ile `private.consent_version()` değerini birlikte artırın.
- Bekleme ekranı arka plana alınınca kullanıcı kuyruktan çıkar. 30 sn heartbeat göndermeyen kayıt aktif sayılmaz, 2 dk sonra silinir.
- Mesaj başına 1000 karakter sınırı ve kişi başına 10 sn'de en fazla 15 mesaj hız sınırı vardır (rastgele ve arkadaş sohbetinde ayrı ayrı).
- Günlük arkadaş isteği sınırı `private.friend_daily_limit()` fonksiyonundan değiştirilebilir. Toplam arkadaş sayısında sınır yok.
- Arkadaş sohbetlerinde yeni mesaj için anlık bildirim (push) yok; mesajlar uygulama açıkken Realtime ile gelir.
