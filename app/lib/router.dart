import 'package:go_router/go_router.dart';

import 'features/auth/otp_screen.dart';
import 'features/auth/phone_screen.dart';
import 'features/ban/banned_screen.dart';
import 'features/chat/chat_screen.dart';
import 'features/common/status_screens.dart';
import 'features/friends/friend_chat_screen.dart';
import 'features/friends/friends_screen.dart';
import 'features/matching/home_screen.dart';
import 'features/matching/waiting_screen.dart';
import 'features/onboarding/consent_screen.dart';
import 'features/onboarding/gender_screen.dart';
import 'features/verification/verification_screen.dart';
import 'models/session_state.dart';
import 'services/app_session.dart';

const _authRoutes = {'/phone', '/otp'};

/// Oturum durumuna göre gidilmesi gereken yer. null = olduğu yerde kal.
/// Saf fonksiyon; test/router_test.dart ile test edilir.
String? computeRedirect(SessionPhase phase, SessionState? s, String location) {
  switch (phase) {
    case SessionPhase.loading:
      return location == '/splash' ? null : '/splash';
    case SessionPhase.error:
      return location == '/error' ? null : '/error';
    case SessionPhase.signedOut:
      return _authRoutes.contains(location) ? null : '/phone';
    case SessionPhase.ready:
      break;
  }
  if (s == null) return '/splash';

  String? go(String target) => location == target ? null : target;

  if (s.banned) return go('/banned');
  if (!s.consentsOk) return go('/consent');
  if (s.profile?.gender == null) return go('/gender');
  if (!s.isVerified) {
    // Doğrulanmamışken cinsiyet seçimine geri dönebilir.
    return location == '/gender' ? null : go('/verify');
  }
  final matchId = s.currentMatchId;
  if (matchId != null) {
    return location == '/chat/$matchId' ? null : '/chat/$matchId';
  }
  // Biten bir sohbetin ekranında kalabilir (şikâyet/engelle için).
  if (location.startsWith('/chat/')) return null;
  if (location == '/home' || location == '/waiting') return null;
  if (location == '/friends' || location.startsWith('/friends/')) return null;
  return '/home';
}

GoRouter buildRouter(AppSession session) => GoRouter(
  initialLocation: '/splash',
  refreshListenable: session,
  redirect: (context, state) =>
      computeRedirect(session.phase, session.state, state.matchedLocation),
  routes: [
    GoRoute(path: '/splash', builder: (_, _) => const SplashScreen()),
    GoRoute(path: '/error', builder: (_, _) => const ErrorScreen()),
    GoRoute(path: '/phone', builder: (_, _) => const PhoneScreen()),
    GoRoute(
      path: '/otp',
      builder: (_, st) => OtpScreen(phone: st.uri.queryParameters['phone'] ?? ''),
    ),
    GoRoute(path: '/consent', builder: (_, _) => const ConsentScreen()),
    GoRoute(path: '/gender', builder: (_, _) => const GenderScreen()),
    GoRoute(path: '/verify', builder: (_, _) => const VerificationScreen()),
    GoRoute(path: '/banned', builder: (_, _) => const BannedScreen()),
    GoRoute(path: '/home', builder: (_, _) => const HomeScreen()),
    GoRoute(path: '/waiting', builder: (_, _) => const WaitingScreen()),
    GoRoute(path: '/friends', builder: (_, _) => const FriendsScreen()),
    GoRoute(
      path: '/friends/:id',
      builder: (_, st) => FriendChatScreen(friendshipId: st.pathParameters['id']!),
    ),
    GoRoute(
      path: '/chat/:id',
      builder: (_, st) => ChatScreen(matchId: st.pathParameters['id']!),
    ),
  ],
);
