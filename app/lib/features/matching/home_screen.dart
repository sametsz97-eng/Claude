import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/realtime_bridge.dart';

import '../../core/errors.dart';
import '../../core/supabase.dart';
import '../../services/app_session.dart';
import '../common/status_screens.dart';
import '../friends/friends_repository.dart';
import 'matching_repository.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with BusyState {
  final _repo = MatchingRepository();
  final _friends = FriendsRepository();
  RowSubscription? _friendsChannel;
  int _incomingRequests = 0;

  @override
  void initState() {
    super.initState();
    _friendsChannel = _friends.subscribeOverview(_loadFriendBadge);
    _loadFriendBadge();
  }

  @override
  void dispose() {
    _friendsChannel?.cancel();
    super.dispose();
  }

  Future<void> _loadFriendBadge() async {
    try {
      final o = await _friends.overview();
      if (mounted) setState(() => _incomingRequests = o.incoming.length);
    } catch (_) {
      // Rozet kritik değil; hata sessizce yok sayılır.
    }
  }

  Future<void> _openFriends() async {
    await context.push('/friends');
    _loadFriendBadge();
  }

  Future<void> _findChat() async {
    final session = SessionScope.of(context);
    await runBusy(
      () async {
        final status = await _repo.join();
        if (!mounted) return;
        if (status.isMatched) {
          await session.refresh(); // router sohbete yönlendirir
        } else {
          context.go('/waiting');
        }
      },
      onError: (e) async {
        showError(friendlyError(e));
        await session.refresh();
      },
    );
  }

  Future<void> _reroll() async {
    final session = SessionScope.of(context);
    await runBusy(
      () async => session.apply(await supabase.rpc('reroll_nickname')),
      onError: (e) => showError(friendlyError(e)),
    );
  }

  Future<void> _confirmDelete() async {
    final session = SessionScope.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Hesabını sil'),
        content: const Text(
          'Hesabın ve sohbet geçmişin kalıcı olarak silinecek. Bu işlem geri alınamaz.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Vazgeç')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Sil')),
        ],
      ),
    );
    if (ok == true) {
      await runBusy(session.deleteAccount, onError: (e) => showError(friendlyError(e)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.watch(context);
    final profile = session.state?.profile;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Anonim Sohbet'),
        actions: [
          IconButton(
            tooltip: 'Arkadaşlar',
            onPressed: _openFriends,
            icon: Badge(
              isLabelVisible: _incomingRequests > 0,
              label: Text('$_incomingRequests'),
              child: const Icon(Icons.people_outline),
            ),
          ),
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'logout') session.signOut();
              if (v == 'delete') _confirmDelete();
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'logout', child: Text('Çıkış yap')),
              PopupMenuItem(value: 'delete', child: Text('Hesabımı sil')),
            ],
          ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(profile?.emoji ?? '👤', style: const TextStyle(fontSize: 72)),
                const SizedBox(height: 8),
                Text(profile?.nickname ?? '', style: theme.textTheme.headlineSmall),
                if (profile?.canReroll ?? false)
                  TextButton.icon(
                    onPressed: busy ? null : _reroll,
                    icon: const Icon(Icons.casino_outlined),
                    label: const Text('Takma adı değiştir (1 hak)'),
                  ),
                const SizedBox(height: 8),
                Text(
                  'Karşındaki kişi sadece takma adını ve emojini görür.',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 40),
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: FilledButton.icon(
                    onPressed: busy ? null : _findChat,
                    icon: const Icon(Icons.forum_outlined),
                    label: const Text('Sohbet bul', style: TextStyle(fontSize: 18)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
