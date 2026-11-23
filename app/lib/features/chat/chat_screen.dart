import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/realtime_bridge.dart';

import '../../core/errors.dart';
import '../../services/app_session.dart';
import '../common/status_screens.dart';
import '../matching/matching_repository.dart';
import '../friends/friends_repository.dart';
import 'chat_repository.dart';
import 'chat_widgets.dart';
import 'report_sheet.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.matchId});

  final String matchId;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with BusyState {
  late final ChatRepository _repo = ChatRepository(widget.matchId);
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<ChatMessage> _messages = [];
  final Set<int> _ids = {};
  RowSubscription? _channel;
  MatchInfo? _match;
  bool _ended = false;

  /// Sohbeti bu kullanıcı mı bitirdi (bitir/engelle/şikâyet)? RPC'den önce ayarlanır,
  /// çünkü Realtime "bitti" olayı RPC cevabından önce gelebilir.
  bool _endedByMe = false;
  bool _friendRequested = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _channel = _repo.subscribe(onMessage: _addMessage, onEnded: _onEnded);
    _load();
  }

  Future<void> _load() async {
    try {
      final match = await _repo.loadMatch();
      final messages = await _repo.loadMessages();
      if (!mounted) return;
      setState(() {
        _match = match;
        _ended = !match.active;
        for (final m in messages) {
          if (_ids.add(m.id)) _messages.add(m);
        }
        _messages.sort((a, b) => a.id.compareTo(b.id));
      });
      _scrollToEnd();
    } catch (e) {
      if (mounted) setState(() => _loadError = friendlyError(e));
    }
  }

  void _addMessage(ChatMessage m) {
    if (!mounted || !_ids.add(m.id)) return;
    setState(() => _messages.add(m));
    _scrollToEnd();
  }

  void _onEnded() {
    if (!mounted || _ended) return;
    setState(() => _ended = true);
    SessionScope.of(context).refresh();
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty || _ended) return;
    if (text.length > 1000) {
      showError('Mesaj en fazla 1000 karakter olabilir.');
      return;
    }
    _input.clear();
    try {
      await _repo.send(text);
    } catch (e) {
      _input.text = text;
      showError(friendlyError(e));
    }
  }

  Future<void> _endChat() async {
    final session = SessionScope.of(context);
    await runBusy(() async {
      _endedByMe = true;
      await _repo.end();
      setState(() => _ended = true);
      await session.refresh();
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<void> _block() async {
    final ok = await _confirm(
      'Engelle',
      'Bu kişi engellenecek ve sohbet bitecek. Bir daha asla eşleşmeyeceksiniz.',
    );
    if (!ok || !mounted) return;
    final session = SessionScope.of(context);
    await runBusy(() async {
      _endedByMe = true;
      await _repo.block();
      setState(() => _ended = true);
      showError('Kullanıcı engellendi.');
      await session.refresh();
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<void> _report() async {
    final selection = await showReportSheet(context);
    if (selection == null || !mounted) return;
    final session = SessionScope.of(context);
    await runBusy(() async {
      _endedByMe = true;
      await _repo.report(selection.category, selection.note);
      setState(() => _ended = true);
      showError('Şikâyetin alındı. Bu kişiyle bir daha eşleşmeyeceksin.');
      await session.refresh();
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<void> _addFriend() async {
    await runBusy(() async {
      final r = await FriendsRepository().sendRequest(widget.matchId);
      setState(() => _friendRequested = true);
      showError(
        r.accepted
            ? 'Artık arkadaşsınız! 🎉 Arkadaşlar sayfasından yazışabilirsin.'
            : 'Arkadaşlık isteği gönderildi. Bugün ${r.remainingToday} hakkın kaldı.',
      );
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<void> _newChat() async {
    final session = SessionScope.of(context);
    await runBusy(() async {
      final status = await MatchingRepository().join();
      if (!mounted) return;
      if (status.isMatched) {
        await session.refresh();
      } else {
        context.go('/waiting');
      }
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<bool> _confirm(String title, String body) => confirmDialog(context, title, body);

  @override
  void dispose() {
    _channel?.cancel();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final match = _match;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (_ended) {
          context.go('/home');
        } else if (await _confirm('Sohbeti bitir', 'Sohbetten çıkmak istiyor musun?')) {
          await _endChat();
          if (context.mounted) context.go('/home');
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Row(
            children: [
              Text(match?.partnerEmoji ?? '👤', style: const TextStyle(fontSize: 24)),
              const SizedBox(width: 8),
              Flexible(child: Text(match?.partnerNickname ?? '…', overflow: TextOverflow.ellipsis)),
            ],
          ),
          actions: [
            PopupMenuButton<String>(
              enabled: !busy,
              onSelected: (v) {
                switch (v) {
                  case 'end':
                    _endChat();
                  case 'block':
                    _block();
                  case 'report':
                    _report();
                  case 'friend':
                    _addFriend();
                }
              },
              itemBuilder: (_) => [
                if (!_friendRequested)
                  const PopupMenuItem(value: 'friend', child: Text('Arkadaş ekle')),
                if (!_ended) const PopupMenuItem(value: 'end', child: Text('Sohbeti bitir')),
                const PopupMenuItem(value: 'block', child: Text('Engelle')),
                const PopupMenuItem(value: 'report', child: Text('Şikâyet et')),
              ],
            ),
          ],
        ),
        body: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: MessageList(
                  messages: _messages,
                  myId: _repo.myId,
                  controller: _scroll,
                  error: _loadError,
                ),
              ),
              if (_ended)
                Container(
                  width: double.infinity,
                  color: theme.colorScheme.surfaceContainerHighest,
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Text(
                        _endedByMe || match?.endedByMe == true
                            ? 'Sohbet sona erdi.'
                            : 'Sohbet sona erdi. Karşı taraf ayrıldı.',
                        textAlign: TextAlign.center,
                      ),
                      if (!_friendRequested) ...[
                        const SizedBox(height: 8),
                        TextButton.icon(
                          onPressed: busy ? null : _addFriend,
                          icon: const Icon(Icons.person_add_alt_1),
                          label: const Text('Arkadaş olarak ekle'),
                        ),
                      ],
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: busy ? null : () => context.go('/home'),
                              child: const Text('Ana sayfa'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: FilledButton(
                              onPressed: busy ? null : _newChat,
                              child: const Text('Yeni sohbet'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                )
              else
                MessageComposer(controller: _input, onSend: _send),
            ],
          ),
        ),
      ),
    );
  }
}
