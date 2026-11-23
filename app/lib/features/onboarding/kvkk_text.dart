// UYARI: Bu metin bir YER TUTUCUDUR. Yayına almadan önce bir hukukçuya
// (KVKK uyumu) inceletin ve veri sorumlusu bilgilerini doldurun.
// Metni değiştirdiğinizde AppConfig.consentVersion ve sunucudaki
// private.consent_version() değerini birlikte artırın.

const kvkkAydinlatmaMetni = '''
KİŞİSEL VERİLERİN KORUNMASI – AYDINLATMA METNİ VE AÇIK RIZA

Veri sorumlusu: [Şirket unvanı, adres, iletişim]

1. İşlenen veriler
• Telefon numarası: yalnızca giriş (SMS doğrulama) ve kötüye kullanımın önlenmesi (ban) için. Diğer kullanıcılara asla gösterilmez. Ban kontrolü için numaranın tek yönlü şifrelenmiş (hash) özeti saklanır.
• Cihaz kimliği: kötüye kullanımın önlenmesi amacıyla tek yönlü şifrelenmiş özet olarak saklanır.
• Cinsiyet bilgisi ve doğrulama sonucu: eşleştirme yapabilmek için.
• Selfie (yüz görüntüsü): yalnızca anlık canlılık ve cinsiyet doğrulaması için doğrulama hizmet sağlayıcısına iletilir. Fotoğraf tarafımızca SAKLANMAZ; yalnızca "doğrulandı" bilgisi kaydedilir. Bu işlem biyometrik veri (özel nitelikli kişisel veri) içerebilir ve açık rızanıza dayanır.
• Sohbet mesajları ve şikâyet kayıtları: hizmetin sunulması ve güvenliğin sağlanması için.

2. Aktarım
Verileriniz, altyapı hizmeti aldığımız bulut sağlayıcıların (veritabanı, SMS, doğrulama) yurt içi/yurt dışı sunucularında işlenebilir. Yurt dışına aktarım açık rızanıza dayanır.

3. Haklarınız (KVKK m.11)
Verilerinize erişme, düzeltme, silme, işlemeye itiraz etme ve şikâyet hakkına sahipsiniz. Uygulama içindeki "Hesabımı sil" seçeneğiyle hesabınızı silebilirsiniz. Kötüye kullanımın önlenmesi için ban kayıtları (şifrelenmiş özet olarak) saklanmaya devam eder.

4. Açık rıza
Aşağıdaki kutucuğu işaretleyerek yukarıda belirtilen verilerimin, özellikle selfie doğrulaması kapsamında biyometrik verilerimin işlenmesine ve yurt dışına aktarılmasına açık rıza verdiğimi kabul ederim.
''';
