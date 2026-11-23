import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/errors.dart';
import '../../core/supabase.dart';
import '../common/status_screens.dart';

class OtpScreen extends StatefulWidget {
  const OtpScreen({super.key, required this.phone});

  final String phone;

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> with BusyState {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    final code = _controller.text.trim();
    if (code.length != 6) {
      showError('6 haneli kodu gir.');
      return;
    }
    // Başarılı olunca AppSession "signedIn" olayını yakalar ve yönlendirir.
    await runBusy(
      () => supabase.auth.verifyOTP(phone: widget.phone, token: code, type: OtpType.sms),
      onError: (e) => showError(friendlyError(e)),
    );
  }

  Future<void> _resend() async {
    await runBusy(() async {
      await supabase.auth.signInWithOtp(phone: widget.phone);
      showError('Kod tekrar gönderildi.');
    }, onError: (e) => showError(friendlyError(e)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Kodu gir')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const Text('Telefonuna gelen 6 haneli kodu gir.'),
            const SizedBox(height: 16),
            TextField(
              controller: _controller,
              keyboardType: TextInputType.number,
              maxLength: 6,
              autofillHints: const [AutofillHints.oneTimeCode],
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 28, letterSpacing: 8),
              decoration: const InputDecoration(border: OutlineInputBorder(), counterText: ''),
              onChanged: (v) {
                if (v.length == 6) _verify();
              },
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: busy ? null : _verify,
              child: busy
                  ? const SizedBox.square(dimension: 20, child: CircularProgressIndicator())
                  : const Text('Doğrula'),
            ),
            TextButton(onPressed: busy ? null : _resend, child: const Text('Kodu tekrar gönder')),
          ],
        ),
      ),
    );
  }
}
