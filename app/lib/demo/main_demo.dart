// TARAYICI DEMOSU giriş noktası.
//   flutter run -d chrome -t lib/demo/main_demo.dart
//   flutter build web -t lib/demo/main_demo.dart
// Supabase'e bağlanmaz; tüm veriler bellektedir ve sayfa yenilenince sıfırlanır.
import 'dart:math';

import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../core/config.dart';
import '../core/realtime_bridge.dart';
import '../features/verification/mock_verification_service.dart';
import '../main.dart';
import '../services/app_session.dart';
import 'demo_backend.dart';
import 'demo_http_client.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  AppConfig.demoMode = true;

  final backend = DemoBackend();
  RealtimeBridge.instance = backend.realtime;

  await Supabase.initialize(
    url: 'https://demo.supabase.local',
    publishableKey: 'demo-publishable-key',
    httpClient: demoHttpClient(backend),
    authOptions: const FlutterAuthClientOptions(localStorage: EmptyLocalStorage()),
    debug: false,
  );

  final session = AppSession()..start();
  runApp(
    AnonimSohbetApp(
      session: session,
      verification: MockVerificationService(delay: const Duration(milliseconds: 1500)),
      builder: _phoneFrame,
    ),
  );
}

/// Masaüstü tarayıcıda telefon genişliğinde göster.
Widget _phoneFrame(BuildContext context, Widget? child) {
  final mq = MediaQuery.of(context);
  final width = min(mq.size.width, 430.0);
  final framed = mq.size.width > 500;
  return ColoredBox(
    color: framed ? const Color(0xFFE8E5F5) : Theme.of(context).colorScheme.surface,
    child: Center(
      child: SizedBox(
        width: width,
        height: framed ? min(mq.size.height - 32, 900) : mq.size.height,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(framed ? 24 : 0),
          child: MediaQuery(
            data: mq.copyWith(size: Size(width, mq.size.height)),
            child: Banner(
              message: 'DEMO',
              location: BannerLocation.topEnd,
              textDirection: TextDirection.ltr,
              layoutDirection: TextDirection.ltr,
              child: child ?? const SizedBox.shrink(),
            ),
          ),
        ),
      ),
    ),
  );
}
