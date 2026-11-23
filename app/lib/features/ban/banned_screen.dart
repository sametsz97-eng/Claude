import 'package:material_ui/material_ui.dart';

import '../../core/format.dart';
import '../../services/app_session.dart';

class BannedScreen extends StatelessWidget {
  const BannedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.watch(context);
    final s = session.state;
    final theme = Theme.of(context);
    final text = (s?.banPermanent ?? false)
        ? 'Hesabın, topluluk kurallarını tekrar tekrar ihlal ettiği için kalıcı olarak kapatıldı.'
        : s?.banUntil != null
        ? 'Hakkında farklı kişilerden gelen şikâyetler nedeniyle hesabın '
              '${formatBanUntil(s!.banUntil!)} tarihine kadar kısıtlandı.'
        : 'Hesabın geçici olarak kısıtlandı.';

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('⛔', style: TextStyle(fontSize: 64)),
                const SizedBox(height: 16),
                Text('Erişim kısıtlandı', style: theme.textTheme.headlineSmall),
                const SizedBox(height: 12),
                Text(text, textAlign: TextAlign.center),
                const SizedBox(height: 32),
                if (!(s?.banPermanent ?? false))
                  FilledButton(
                    onPressed: session.bootstrap,
                    child: const Text('Tekrar kontrol et'),
                  ),
                TextButton(onPressed: session.signOut, child: const Text('Çıkış yap')),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
