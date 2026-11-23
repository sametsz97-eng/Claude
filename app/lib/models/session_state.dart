enum Gender {
  female('female', 'Kız'),
  male('male', 'Erkek');

  const Gender(this.value, this.label);
  final String value;
  final String label;

  static Gender? tryParse(Object? v) {
    for (final g in Gender.values) {
      if (g.value == v) return g;
    }
    return null;
  }
}

class Profile {
  const Profile({
    required this.nickname,
    required this.emoji,
    required this.canReroll,
    required this.gender,
    required this.genderVerified,
    required this.needsReverification,
  });

  final String nickname;
  final String emoji;
  final bool canReroll;
  final Gender? gender;
  final bool genderVerified;
  final bool needsReverification;

  factory Profile.fromJson(Map<String, dynamic> j) => Profile(
    nickname: j['nickname'] as String? ?? '',
    emoji: j['emoji'] as String? ?? '👤',
    canReroll: j['can_reroll'] as bool? ?? false,
    gender: Gender.tryParse(j['gender']),
    genderVerified: j['gender_verified'] as bool? ?? false,
    needsReverification: j['needs_reverification'] as bool? ?? false,
  );
}

/// Sunucudaki private.session_state() çıktısı.
class SessionState {
  const SessionState({
    required this.banned,
    required this.banUntil,
    required this.banPermanent,
    required this.consentsOk,
    required this.profile,
    required this.currentMatchId,
    required this.inQueue,
  });

  final bool banned;
  final DateTime? banUntil;
  final bool banPermanent;
  final bool consentsOk;
  final Profile? profile;
  final String? currentMatchId;
  final bool inQueue;

  bool get isVerified =>
      profile != null && profile!.genderVerified && !profile!.needsReverification;

  factory SessionState.fromJson(Map<String, dynamic> j) {
    final p = j['profile'];
    final until = j['ban_until'];
    return SessionState(
      banned: j['banned'] as bool? ?? false,
      banUntil: until is String ? DateTime.tryParse(until) : null,
      banPermanent: j['ban_permanent'] as bool? ?? false,
      consentsOk: j['consents_ok'] as bool? ?? false,
      profile: p is Map ? Profile.fromJson(Map<String, dynamic>.from(p)) : null,
      currentMatchId: j['current_match_id'] as String?,
      inQueue: j['in_queue'] as bool? ?? false,
    );
  }
}
