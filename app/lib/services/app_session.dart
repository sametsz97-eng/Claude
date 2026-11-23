import 'dart:async';

import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../core/device_id.dart';
import '../core/errors.dart';
import '../core/supabase.dart';
import '../models/session_state.dart';

enum SessionPhase { loading, signedOut, ready, error }

/// Uygulamanın oturum durumu. Router bu nesneyi dinleyerek yönlendirme yapar.
class AppSession extends ChangeNotifier {
  SessionPhase phase = SessionPhase.loading;
  SessionState? state;
  String? errorMessage;

  StreamSubscription<AuthState>? _authSub;

  void start() {
    _authSub = supabase.auth.onAuthStateChange.listen((data) {
      switch (data.event) {
        case AuthChangeEvent.initialSession:
          if (data.session == null) {
            _setSignedOut();
          } else {
            bootstrap();
          }
        case AuthChangeEvent.signedIn:
          bootstrap();
        case AuthChangeEvent.signedOut:
          _setSignedOut();
        default:
          break;
      }
    });
  }

  void _setSignedOut() {
    state = null;
    phase = SessionPhase.signedOut;
    notifyListeners();
  }

  /// Giriş sonrası ve uygulama açılışında: cihaz/telefon hash kaydı + ban kontrolü.
  Future<void> bootstrap() async {
    phase = SessionPhase.loading;
    notifyListeners();
    try {
      final deviceId = await getDeviceId();
      final res = await supabase.rpc('bootstrap_session', params: {'p_device_id': deviceId});
      apply(res);
    } catch (e) {
      errorMessage = friendlyError(e);
      phase = SessionPhase.error;
      notifyListeners();
    }
  }

  Future<void> refresh() async {
    try {
      apply(await supabase.rpc('get_session_state'));
    } catch (e) {
      errorMessage = friendlyError(e);
      phase = SessionPhase.error;
      notifyListeners();
    }
  }

  /// RPC'lerin döndürdüğü oturum durumunu uygular.
  void apply(dynamic json) {
    state = SessionState.fromJson(Map<String, dynamic>.from(json as Map));
    phase = SessionPhase.ready;
    errorMessage = null;
    notifyListeners();
  }

  Future<void> signOut() async {
    try {
      await supabase.rpc('leave_queue');
    } catch (_) {}
    await supabase.auth.signOut();
  }

  Future<void> deleteAccount() async {
    await supabase.rpc('delete_account');
    await supabase.auth.signOut();
  }

  @override
  void dispose() {
    _authSub?.cancel();
    super.dispose();
  }
}

/// Widget ağacında AppSession'a erişim.
class SessionScope extends InheritedNotifier<AppSession> {
  const SessionScope({super.key, required AppSession session, required super.child})
    : super(notifier: session);

  static AppSession of(BuildContext context) =>
      context.getInheritedWidgetOfExactType<SessionScope>()!.notifier!;

  static AppSession watch(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<SessionScope>()!.notifier!;
}
