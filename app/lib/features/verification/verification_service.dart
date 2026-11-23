import 'package:material_ui/material_ui.dart';

import '../../models/session_state.dart';

/// Selfie / canlılık doğrulamasının sonucu.
class VerificationResult {
  const VerificationResult._({required this.success, this.providerToken, this.errorMessage});

  const VerificationResult.success(String token) : this._(success: true, providerToken: token);

  const VerificationResult.failure(String message) : this._(success: false, errorMessage: message);

  const VerificationResult.cancelled() : this._(success: false);

  final bool success;

  /// Sağlayıcının verdiği oturum token'ı. Sunucudaki confirm-verification
  /// Edge Function'ı bu token'ı sağlayıcıya doğrulatır. Fotoğraf DEĞİLDİR.
  final String? providerToken;
  final String? errorMessage;
}

/// Selfie doğrulama sağlayıcısı soyutlaması.
///
/// Kurallar (tüm implementasyonlar için):
///  * Fotoğraf/video cihazda ve sağlayıcıda kalır; bizim sunucumuza veya
///    Supabase Storage'a ASLA yüklenmez, diske kaydedilmez.
///  * Sonuç sadece [VerificationResult.providerToken] olarak döner;
///    "verified=true" kaydını sunucu, token'ı doğruladıktan sonra yazar.
///
/// İleride: YotiVerificationService, FaceTecVerificationService.
abstract class VerificationService {
  /// Sağlayıcı adı (log/analitik için).
  String get name;

  /// true ise doğrulama ekranı uygulamanın kendi kamera önizlemesini gösterir.
  /// Yoti/FaceTec gibi SDK'lar kendi arayüzünü getirdiği için false döner.
  bool get usesInAppCameraPreview;

  /// Doğrulamayı başlatır. [claimedGender] kullanıcının beyan ettiği cinsiyettir.
  Future<VerificationResult> verifySelfie({required Gender claimedGender});
}

class VerificationScope extends InheritedWidget {
  const VerificationScope({super.key, required this.service, required super.child});

  final VerificationService service;

  static VerificationService of(BuildContext context) =>
      context.getInheritedWidgetOfExactType<VerificationScope>()!.service;

  @override
  bool updateShouldNotify(VerificationScope oldWidget) => service != oldWidget.service;
}
