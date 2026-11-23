import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/errors.dart';
import '../../core/supabase.dart';
import '../../models/session_state.dart';
import '../../services/app_session.dart';
import '../common/status_screens.dart';

class GenderScreen extends StatefulWidget {
  const GenderScreen({super.key});

  @override
  State<GenderScreen> createState() => _GenderScreenState();
}

class _GenderScreenState extends State<GenderScreen> with BusyState {
  Future<void> _select(Gender g) async {
    final session = SessionScope.of(context);
    await runBusy(() async {
      final res = await supabase.rpc('set_gender', params: {'p_gender': g.value});
      session.apply(res);
      if (mounted) context.go('/verify');
    }, onError: (e) => showError(friendlyError(e)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final profile = SessionScope.watch(context).state?.profile;
    return Scaffold(
      appBar: AppBar(title: const Text('Cinsiyetin')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (profile != null)
                Text(
                  'Merhaba ${profile.emoji} ${profile.nickname}!',
                  style: theme.textTheme.titleLarge,
                  textAlign: TextAlign.center,
                ),
              const SizedBox(height: 12),
              const Text(
                'Sohbetler her zaman bir kız ve bir erkek arasında kurulur. '
                'Seçimin bir sonraki adımda selfie ile doğrulanacak ve doğrulandıktan sonra değiştirilemez.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              for (final g in Gender.values) ...[
                _GenderCard(
                  gender: g,
                  selected: profile?.gender == g,
                  onTap: busy ? null : () => _select(g),
                ),
                const SizedBox(height: 16),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _GenderCard extends StatelessWidget {
  const _GenderCard({required this.gender, required this.selected, required this.onTap});

  final Gender gender;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      color: selected ? scheme.primaryContainer : null,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 28),
          child: Column(
            children: [
              Text(gender == Gender.female ? '👩' : '👨', style: const TextStyle(fontSize: 44)),
              const SizedBox(height: 8),
              Text(gender.label, style: Theme.of(context).textTheme.titleLarge),
            ],
          ),
        ),
      ),
    );
  }
}
