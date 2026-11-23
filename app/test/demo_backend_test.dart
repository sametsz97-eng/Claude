import 'package:anonim_sohbet/demo/demo_backend.dart';
import 'package:anonim_sohbet/demo/demo_http_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() {
  test('demo backend: giriş, onay, doğrulama, eşleşme, mesaj, arkadaş', () async {
    final backend = DemoBackend();
    final client = SupabaseClient(
      'https://demo.supabase.local',
      'demo-key',
      httpClient: demoHttpClient(backend),
      authOptions: const AuthClientOptions(autoRefreshToken: false),
    );
    await client.auth.signInWithOtp(phone: '+905321234567');
    final auth = await client.auth.verifyOTP(
      phone: '+905321234567',
      token: '123456',
      type: OtpType.sms,
    );
    expect(auth.session, isNotNull);

    final s = await client.rpc('bootstrap_session', params: {'p_device_id': null});
    expect((s as Map)['consents_ok'], false);
    await client.rpc(
      'accept_consents',
      params: {'p_version': 'kvkk-v1', 'p_age_confirmed': true, 'p_kvkk_accepted': true},
    );
    await client.rpc('set_gender', params: {'p_gender': 'female'});
    final v = await client.functions.invoke(
      'confirm-verification',
      body: {'provider_token': 'mock-ok:1', 'claimed_gender': 'female'},
    );
    expect((v.data as Map)['verified'], true);

    final o = await client.rpc('get_friends_overview') as Map;
    expect((o['incoming'] as List), hasLength(1));
    expect((o['friends'] as List), hasLength(1));

    final j = await client.rpc('join_queue') as Map;
    expect(j['status'], 'waiting');

    await expectLater(
      client.rpc('reroll_nickname').then((_) => client.rpc('reroll_nickname')),
      throwsA(isA<PostgrestException>().having((e) => e.message, 'message', 'reroll_limit')),
    );
  });
}
