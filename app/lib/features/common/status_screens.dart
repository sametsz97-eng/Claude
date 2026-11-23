import 'package:material_ui/material_ui.dart';

import '../../services/app_session.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) => const Scaffold(
    body: Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('💬', style: TextStyle(fontSize: 56)),
          SizedBox(height: 16),
          CircularProgressIndicator(),
        ],
      ),
    ),
  );
}

class ErrorScreen extends StatelessWidget {
  const ErrorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.watch(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.cloud_off, size: 48),
                const SizedBox(height: 16),
                Text(session.errorMessage ?? 'Bir hata oluştu.', textAlign: TextAlign.center),
                const SizedBox(height: 24),
                FilledButton(onPressed: session.bootstrap, child: const Text('Tekrar dene')),
                TextButton(onPressed: session.signOut, child: const Text('Çıkış yap')),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Basit "işlem sürüyor" yardımcı karışımı.
mixin BusyState<T extends StatefulWidget> on State<T> {
  bool busy = false;

  Future<void> runBusy(Future<void> Function() action, {void Function(Object e)? onError}) async {
    if (busy) return;
    setState(() => busy = true);
    try {
      await action();
    } catch (e) {
      onError?.call(e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }
}
