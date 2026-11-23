import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/realtime_bridge.dart';

import '../../core/errors.dart';
import '../chat/chat_widgets.dart';
import '../common/status_screens.dart';
import 'friends_repository.dart';

class FriendsScreen extends StatefulWidget {
  const FriendsScreen({super.key});

  @override
  State<FriendsScreen> createState() => _FriendsScreenState();
}

class _FriendsScreenState extends State<FriendsScreen> with BusyState {
  final _repo = FriendsRepository();
  RowSubscription? _channel;
  FriendsOverview? _data;
  String? _error;

  @override
  void initState() {
    super.initState();
    _channel = _repo.subscribeOverview(_load);
    _load();
  }

  @override
  void dispose() {
    _channel?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await _repo.overview();
      if (mounted) {
        setState(() {
          _data = d;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    }
  }

  Future<void> _respond(FriendRequest r, bool accept) async {
    await runBusy(() async {
      await _repo.respond(r.id, accept: accept);
      showError(accept ? '${r.nickname} artık arkadaşın! 🎉' : 'İstek reddedildi.');
      await _load();
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<void> _remove(Friend f) async {
    final ok = await confirmDialog(
      context,
      'Arkadaşlıktan çıkar',
      '${f.nickname} arkadaş listenden silinecek ve mesaj geçmişiniz iki taraf için de silinecek. '
          'Bu işlem günlük arkadaş ekleme hakkını geri vermez.',
    );
    if (!ok) return;
    await runBusy(() async {
      await _repo.remove(f.friendshipId);
      showError('${f.nickname} arkadaşlarından çıkarıldı.');
      await _load();
    }, onError: (e) => showError(friendlyError(e)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final d = _data;

    return Scaffold(
      appBar: AppBar(title: const Text('Arkadaşlar')),
      body: SafeArea(
        child: _error != null && d == null
            ? Center(
                child: TextButton(onPressed: _load, child: Text('$_error\nTekrar dene')),
              )
            : d == null
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  children: [
                    Card(
                      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: ListTile(
                        leading: const Icon(Icons.person_add_alt_1),
                        title: Text(
                          'Bugün ${d.remainingToday}/${d.dailyLimit} arkadaş ekleme hakkın kaldı',
                        ),
                        subtitle: const Text(
                          'Sohbet ettiğin kişiyi sohbet ekranındaki menüden ekleyebilirsin. '
                          'Haklar her gün gece yarısı yenilenir.',
                        ),
                      ),
                    ),
                    if (d.incoming.isNotEmpty) ...[
                      _Header('Gelen istekler (${d.incoming.length})'),
                      for (final r in d.incoming)
                        ListTile(
                          leading: _Avatar(r.emoji),
                          title: Text(r.nickname),
                          subtitle: const Text('Seni arkadaş olarak eklemek istiyor'),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                tooltip: 'Reddet',
                                onPressed: busy ? null : () => _respond(r, false),
                                icon: const Icon(Icons.close),
                              ),
                              IconButton.filled(
                                tooltip: 'Kabul et',
                                onPressed: busy ? null : () => _respond(r, true),
                                icon: const Icon(Icons.check),
                              ),
                            ],
                          ),
                        ),
                    ],
                    _Header('Arkadaşların (${d.friends.length})'),
                    if (d.friends.isEmpty)
                      Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          'Henüz arkadaşın yok.',
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodyMedium,
                        ),
                      ),
                    for (final f in d.friends)
                      ListTile(
                        leading: _Avatar(f.emoji),
                        title: Text(f.nickname),
                        subtitle: f.lastMessage == null
                            ? const Text('Henüz mesaj yok')
                            : Text(
                                '${f.lastMessageMine ? 'Sen: ' : ''}${f.lastMessage}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                        onTap: () => context.push('/friends/${f.friendshipId}'),
                        trailing: PopupMenuButton<String>(
                          enabled: !busy,
                          onSelected: (v) {
                            if (v == 'chat') context.push('/friends/${f.friendshipId}');
                            if (v == 'remove') _remove(f);
                          },
                          itemBuilder: (_) => const [
                            PopupMenuItem(value: 'chat', child: Text('Mesaj gönder')),
                            PopupMenuItem(value: 'remove', child: Text('Arkadaşlıktan çıkar')),
                          ],
                        ),
                      ),
                    if (d.outgoingPending > 0)
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text(
                          'Yanıt bekleyen ${d.outgoingPending} isteğin var.',
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodySmall,
                        ),
                      ),
                  ],
                ),
              ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
    child: Text(text, style: Theme.of(context).textTheme.titleSmall),
  );
}

class _Avatar extends StatelessWidget {
  const _Avatar(this.emoji);

  final String emoji;

  @override
  Widget build(BuildContext context) => CircleAvatar(
    backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
    child: Text(emoji, style: const TextStyle(fontSize: 22)),
  );
}
