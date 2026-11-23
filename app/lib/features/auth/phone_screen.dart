import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/config.dart';
import '../../core/errors.dart';
import '../../core/phone.dart';
import '../../core/supabase.dart';
import '../common/status_screens.dart';

class PhoneScreen extends StatefulWidget {
  const PhoneScreen({super.key});

  @override
  State<PhoneScreen> createState() => _PhoneScreenState();
}

class _PhoneScreenState extends State<PhoneScreen> with BusyState {
  final _controller = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final phone = normalizeTurkishMobile(_controller.text);
    if (phone == null) {
      setState(() => _error = 'Geçerli bir cep telefonu numarası gir (5XX XXX XX XX).');
      return;
    }
    setState(() => _error = null);
    await runBusy(() async {
      await supabase.auth.signInWithOtp(phone: phone);
      if (mounted) context.push('/otp?phone=${Uri.encodeComponent(phone)}');
    }, onError: (e) => showError(friendlyError(e)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 40),
            const Text('💬', style: TextStyle(fontSize: 56), textAlign: TextAlign.center),
            const SizedBox(height: 12),
            Text(
              'Anonim Sohbet',
              style: theme.textTheme.headlineMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Telefonunla giriş yap. Numaran kimseye gösterilmez; '
              'sohbette sadece rastgele takma adın görünür.',
              style: theme.textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            if (AppConfig.demoMode) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    '🧪 Demo: herhangi bir cep numarası gir (ör. 532 123 45 67). SMS gönderilmez.',
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            TextField(
              controller: _controller,
              keyboardType: TextInputType.phone,
              autofillHints: const [AutofillHints.telephoneNumber],
              decoration: InputDecoration(
                labelText: 'Cep telefonu',
                prefixText: '+90 ',
                hintText: '5XX XXX XX XX',
                errorText: _error,
                border: const OutlineInputBorder(),
              ),
              onSubmitted: (_) => _send(),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: busy ? null : _send,
              child: busy
                  ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator())
                  : const Text('SMS kodu gönder'),
            ),
          ],
        ),
      ),
    );
  }
}
