import 'dart:math';

import '../../models/session_state.dart';
import 'verification_service.dart';

/// Geliştirme amaçlı sahte doğrulama. Hiçbir görüntü yakalamaz/göndermez;
/// kısa bir beklemeden sonra başarılı token döner.
/// Sunucu bu token'ı yalnızca VERIFICATION_MODE=mock iken kabul eder.
class MockVerificationService implements VerificationService {
  MockVerificationService({this.delay = const Duration(seconds: 2), this.alwaysFail = false});

  final Duration delay;
  final bool alwaysFail;

  @override
  String get name => 'mock';

  @override
  bool get usesInAppCameraPreview => true;

  @override
  Future<VerificationResult> verifySelfie({required Gender claimedGender}) async {
    await Future<void>.delayed(delay);
    if (alwaysFail) {
      return const VerificationResult.failure('Yüzün algılanamadı. Lütfen tekrar dene.');
    }
    final nonce = Random.secure().nextInt(1 << 32).toRadixString(16);
    return VerificationResult.success('mock-ok:$nonce');
  }
}
