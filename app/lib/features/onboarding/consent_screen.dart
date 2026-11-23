import 'package:material_ui/material_ui.dart';

import '../../core/config.dart';
import '../../core/errors.dart';
import '../../core/supabase.dart';
import '../../services/app_session.dart';
import '../common/status_screens.dart';
import 'kvkk_text.dart';

class ConsentScreen extends StatefulWidget {
  const ConsentScreen({super.key});

  @override
  State<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends State<ConsentScreen> with BusyState {
  bool _age = false;
  bool _kvkk = false;

  Future<void> _accept() async {
    final session = SessionScope.of(context);
    await runBusy(() async {
      final res = await supabase.rpc(
        'accept_consents',
        params: {
          'p_version': AppConfig.consentVersion,
          'p_age_confirmed': _age,
          'p_kvkk_accepted': _kvkk,
        },
      );
      session.apply(res);
    }, onError: (e) => showError(friendlyError(e)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Onaylar'),
        actions: [
          TextButton(
            onPressed: () => SessionScope.of(context).signOut(),
            child: const Text('Çıkış'),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Container(
                margin: const EdgeInsets.all(16),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: SingleChildScrollView(
                  child: Text(kvkkAydinlatmaMetni, style: theme.textTheme.bodySmall),
                ),
              ),
            ),
            CheckboxListTile(
              value: _age,
              onChanged: (v) => setState(() => _age = v ?? false),
              title: const Text('18 yaşından büyük olduğumu onaylıyorum.'),
            ),
            CheckboxListTile(
              value: _kvkk,
              onChanged: (v) => setState(() => _kvkk = v ?? false),
              title: const Text(
                'Aydınlatma metnini okudum; kişisel verilerimin işlenmesine açık rıza veriyorum.',
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: (_age && _kvkk && !busy) ? _accept : null,
                  child: const Text('Devam et'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
