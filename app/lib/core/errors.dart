import 'package:supabase_flutter/supabase_flutter.dart';

const _messages = <String, String>{
  'banned': 'Hesabın kısıtlandı.',
  'not_authenticated': 'Oturumun sona erdi. Lütfen tekrar giriş yap.',
  'phone_required': 'Telefon numarası doğrulanmadı.',
  'profile_missing': 'Profil bulunamadı. Lütfen uygulamayı yeniden başlat.',
  'consents_required': '18 yaş onayı ve KVKK açık rızası gerekli.',
  'consent_version_mismatch': 'Sözleşme metni güncellendi. Lütfen uygulamayı güncelle.',
  'gender_required': 'Önce cinsiyetini seçmelisin.',
  'gender_locked': 'Doğrulanmış cinsiyet değiştirilemez.',
  'verification_required': 'Önce selfie doğrulamasını tamamlamalısın.',
  'reverification_required': 'Yeniden selfie doğrulaması yapman gerekiyor.',
  'reroll_limit': 'Takma adını yalnızca bir kez değiştirebilirsin.',
  'rate_limited': 'Çok hızlı mesaj gönderiyorsun, biraz yavaşla.',
  'too_many_attempts': 'Çok fazla doğrulama denemesi. 1 saat sonra tekrar dene.',
  'match_not_found': 'Sohbet bulunamadı.',
  'identity_missing': 'Bu kullanıcı artık mevcut değil.',
  'provider_error': 'Doğrulama servisine ulaşılamadı. Lütfen tekrar dene.',
};

/// Sunucu hatalarını kullanıcıya gösterilecek Türkçe metne çevirir.
String friendlyError(Object error) {
  String? code;
  if (error is PostgrestException) {
    code = error.message;
    if (error.code == '42501') return 'Bu işlem için yetkin yok.';
  } else if (error is FunctionException) {
    final details = error.details;
    if (details is Map && details['error'] is String) code = details['error'] as String;
  } else if (error is AuthException) {
    final m = error.message.toLowerCase();
    if (m.contains('expired') || m.contains('invalid') || m.contains('token')) {
      return 'Kod hatalı veya süresi dolmuş.';
    }
    if (m.contains('rate') || error.statusCode == '429') {
      return 'Çok fazla deneme yaptın. Biraz bekleyip tekrar dene.';
    }
    return 'Giriş yapılamadı. Lütfen tekrar dene.';
  } else if (error is String) {
    code = error;
  }
  if (code != null) {
    final exact = _messages[code.trim()];
    if (exact != null) return exact;
    // En uzun anahtar önce: "reverification_required" "verification_required"dan önce eşleşsin.
    final keys = _messages.keys.toList()..sort((a, b) => b.length.compareTo(a.length));
    for (final key in keys) {
      if (code.contains(key)) return _messages[key]!;
    }
  }
  return 'Bir hata oluştu. Lütfen tekrar dene.';
}
