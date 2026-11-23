import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'core/config.dart';
import 'features/verification/mock_verification_service.dart';
import 'features/verification/verification_service.dart';
import 'router.dart';
import 'services/app_session.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!AppConfig.isConfigured) {
    runApp(const _MissingConfigApp());
    return;
  }
  await Supabase.initialize(
    url: AppConfig.supabaseUrl,
    publishableKey: AppConfig.supabasePublishableKey,
  );

  final session = AppSession()..start();
  // İleride: YotiVerificationService() veya FaceTecVerificationService()
  final VerificationService verification = MockVerificationService();

  runApp(AnonimSohbetApp(session: session, verification: verification));
}

class AnonimSohbetApp extends StatefulWidget {
  const AnonimSohbetApp({super.key, required this.session, required this.verification});

  final AppSession session;
  final VerificationService verification;

  @override
  State<AnonimSohbetApp> createState() => _AnonimSohbetAppState();
}

class _AnonimSohbetAppState extends State<AnonimSohbetApp> {
  late final GoRouter _router = buildRouter(widget.session);

  @override
  Widget build(BuildContext context) {
    return SessionScope(
      session: widget.session,
      child: VerificationScope(
        service: widget.verification,
        child: MaterialApp.router(
          title: 'Anonim Sohbet',
          debugShowCheckedModeBanner: false,
          theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF6B4EFF))),
          darkTheme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFF6B4EFF),
              brightness: Brightness.dark,
            ),
          ),
          routerConfig: _router,
        ),
      ),
    );
  }
}

class _MissingConfigApp extends StatelessWidget {
  const _MissingConfigApp();

  @override
  Widget build(BuildContext context) => const MaterialApp(
    home: Scaffold(
      body: Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'SUPABASE_URL ve SUPABASE_PUBLISHABLE_KEY tanımlı değil.\n'
            'README\'deki "Uygulamayı çalıştır" adımına bakın.',
            textAlign: TextAlign.center,
          ),
        ),
      ),
    ),
  );
}
