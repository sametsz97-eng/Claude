import 'package:anonim_sohbet/core/errors.dart';
import 'package:anonim_sohbet/core/format.dart';
import 'package:anonim_sohbet/core/phone.dart';
import 'package:anonim_sohbet/models/session_state.dart';
import 'package:anonim_sohbet/router.dart';
import 'package:anonim_sohbet/services/app_session.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

SessionState state({
  bool banned = false,
  bool consents = true,
  String? gender = 'female',
  bool verified = true,
  bool reverify = false,
  String? match,
}) => SessionState.fromJson({
  'banned': banned,
  'consents_ok': consents,
  'profile': {
    'nickname': 'Sessiz Martı',
    'emoji': '🐦',
    'gender': gender,
    'gender_verified': verified,
    'needs_reverification': reverify,
  },
  'current_match_id': match,
});

void main() {
  group('normalizeTurkishMobile', () {
    test('farklı yazımları kabul eder', () {
      for (final v in ['5321234567', '0532 123 45 67', '+90 532 123 45 67', '905321234567']) {
        expect(normalizeTurkishMobile(v), '+905321234567', reason: v);
      }
    });
    test('geçersizleri reddeder', () {
      for (final v in ['', '123', '2121234567', '05321234']) {
        expect(normalizeTurkishMobile(v), isNull, reason: v);
      }
    });
  });

  test('formatEta', () {
    expect(formatEta(5), 'birkaç saniye');
    expect(formatEta(45), '1 dakikadan az');
    expect(formatEta(130), '~3 dk');
    expect(formatEta(3600), '1 saatten fazla');
  });

  test('friendlyError en uzun kodu önce eşler', () {
    expect(
      friendlyError(const PostgrestException(message: 'reverification_required')),
      'Yeniden selfie doğrulaması yapman gerekiyor.',
    );
    expect(
      friendlyError(const PostgrestException(message: 'verification_required')),
      'Önce selfie doğrulamasını tamamlamalısın.',
    );
    expect(
      friendlyError(const PostgrestException(message: 'friend_daily_limit')),
      'Bugünkü 3 arkadaş ekleme hakkını doldurdun. Yarın tekrar dene.',
    );
    expect(friendlyError(Exception('x')), 'Bir hata oluştu. Lütfen tekrar dene.');
  });

  group('computeRedirect', () {
    const ready = SessionPhase.ready;
    test('oturum yoksa telefona', () {
      expect(computeRedirect(SessionPhase.signedOut, null, '/home'), '/phone');
      expect(computeRedirect(SessionPhase.signedOut, null, '/otp'), isNull);
    });
    test('onboarding sırası', () {
      expect(computeRedirect(ready, state(banned: true), '/home'), '/banned');
      expect(computeRedirect(ready, state(consents: false), '/home'), '/consent');
      expect(computeRedirect(ready, state(gender: null), '/consent'), '/gender');
      expect(computeRedirect(ready, state(verified: false), '/home'), '/verify');
      expect(computeRedirect(ready, state(verified: false), '/gender'), isNull);
      expect(computeRedirect(ready, state(reverify: true), '/waiting'), '/verify');
    });
    test('aktif sohbet varsa sohbete', () {
      expect(computeRedirect(ready, state(match: 'abc'), '/home'), '/chat/abc');
      expect(computeRedirect(ready, state(match: 'abc'), '/chat/abc'), isNull);
    });
    test('doğrulanmış kullanıcı ana sayfa / bekleme / biten sohbet', () {
      expect(computeRedirect(ready, state(), '/verify'), '/home');
      expect(computeRedirect(ready, state(), '/waiting'), isNull);
      expect(computeRedirect(ready, state(), '/chat/eski'), isNull);
      expect(computeRedirect(ready, state(), '/friends'), isNull);
      expect(computeRedirect(ready, state(), '/friends/f1'), isNull);
    });
    test('aktif sohbet varken arkadaş ekranına gidilmez', () {
      expect(computeRedirect(ready, state(match: 'abc'), '/friends'), '/chat/abc');
    });
    test('doğrulanmamış kullanıcı arkadaş ekranına gidemez', () {
      expect(computeRedirect(ready, state(reverify: true), '/friends/f1'), '/verify');
      expect(computeRedirect(ready, state(banned: true), '/friends'), '/banned');
    });
  });
}
