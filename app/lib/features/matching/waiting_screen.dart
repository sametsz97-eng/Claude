import 'dart:async';

import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/realtime_bridge.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../models/session_state.dart';
import '../../services/app_session.dart';
import 'matching_repository.dart';

/// Kuyrukta bekleme. ~5 sn'de bir heartbeat gönderir (canlılık + yeniden eşleşme
/// denemesi + tahmini süre). Ayrıca Realtime ile yeni eşleşmeyi anında yakalar.
class WaitingScreen extends StatefulWidget {
  const WaitingScreen({super.key});

  @override
  State<WaitingScreen> createState() => _WaitingScreenState();
}

class _WaitingScreenState extends State<WaitingScreen> with WidgetsBindingObserver {
  final _repo = MatchingRepository();
  Timer? _timer;
  RowSubscription? _channel;
  QueueStatus? _status;
  bool _matched = false;
  bool _leaving = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _channel = _repo.subscribeToNewMatches((_) => _tick());
    _tick();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _tick());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Arka plana alınınca kuyruktan çık; adil sıra için aktif olmayan beklemesin.
    if (state == AppLifecycleState.paused && !_matched) _leave();
  }

  Future<void> _tick() async {
    if (_matched || _leaving) return;
    try {
      final s = await _repo.heartbeat();
      if (!mounted) return;
      if (s.isMatched) {
        _matched = true;
        _timer?.cancel();
        await SessionScope.of(context).refresh(); // router sohbete yönlendirir
        return;
      }
      if (s.status != 'waiting') {
        // banned / idle (ör. bayat kayıt silindi, yeniden doğrulama istendi)
        final session = SessionScope.of(context);
        if (s.status == 'idle' && session.state?.isVerified == true && !session.state!.banned) {
          await _repo.join();
          return;
        }
        await session.refresh();
        if (mounted) context.go('/home');
        return;
      }
      setState(() => _status = s);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(friendlyError(e))));
      }
    }
  }

  Future<void> _leave() async {
    if (_leaving) return;
    _leaving = true;
    _timer?.cancel();
    try {
      await _repo.leave();
    } catch (_) {}
    if (mounted) context.go('/home');
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _channel?.cancel();
    if (!_matched && !_leaving) _repo.leave().catchError((_) {});
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final me = SessionScope.watch(context).state?.profile?.gender;
    final other = me == Gender.female ? 'erkek' : 'kız';
    final s = _status;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _leave();
      },
      child: Scaffold(
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox.square(dimension: 64, child: CircularProgressIndicator()),
                  const SizedBox(height: 32),
                  Text('Sohbet arkadaşı aranıyor…', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 16),
                  if (s != null) ...[
                    Text(
                      'Tahmini bekleme: ${formatEta(s.etaSeconds)}',
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text('Sıran: ${s.position}', style: theme.textTheme.bodyMedium),
                    const SizedBox(height: 8),
                    if (s.oppositeWaiting == 0)
                      Text(
                        'Şu an bekleyen $other yok. Sohbetler her zaman bir kız ve bir erkek '
                        'arasında kurulduğu için sıra seni bekliyor.',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodySmall,
                      ),
                  ],
                  const SizedBox(height: 40),
                  OutlinedButton(onPressed: _leave, child: const Text('Vazgeç')),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
