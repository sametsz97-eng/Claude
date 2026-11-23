import '../../core/supabase.dart';
import '../../models/session_state.dart';

class VerificationRepository {
  /// Token'ı sunucuya gönderir; sunucu sağlayıcıya doğrulatıp verified=true yazar.
  Future<bool> confirm({required String providerToken, required Gender claimedGender}) async {
    final res = await supabase.functions.invoke(
      'confirm-verification',
      body: {'provider_token': providerToken, 'claimed_gender': claimedGender.value},
    );
    final data = res.data;
    return data is Map && data['verified'] == true;
  }
}
