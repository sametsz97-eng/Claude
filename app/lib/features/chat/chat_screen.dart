import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/errors.dart';
import '../../services/app_session.dart';
import '../common/status_screens.dart';
import '../matching/matching_repository.dart';
import 'chat_repository.dart';
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
  RealtimeChannel? _channel;
  MatchInfo? _match;
  bool _ended = false;
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
      await _repo.report(selection.category, selection.note);
      setState(() => _ended = true);
      showError('Şikâyetin alındı. Bu kişiyle bir daha eşleşmeyeceksin.');
      await session.refresh();
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

  Future<bool> _confirm(String title, String body) async {
    final r = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Vazgeç')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(title)),
        ],
      ),
    );
    return r ?? false;
  }

  @override
  void dispose() {
    if (_channel != null) Supabase.instance.client.removeChannel(_channel!);
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
                }
              },
              itemBuilder: (_) => [
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
                child: _loadError != null
                    ? Center(child: Text(_loadError!))
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.all(12),
                        itemCount: _messages.length,
                        itemBuilder: (_, i) {
                          final m = _messages[i];
                          return _Bubble(message: m, mine: m.senderId == _repo.myId);
                        },
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
                        match?.endedByMe == true || busy
                            ? 'Sohbet sona erdi.'
                            : 'Sohbet sona erdi. Karşı taraf ayrıldı.',
                        textAlign: TextAlign.center,
                      ),
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
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 4, 8, 8),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _input,
                          minLines: 1,
                          maxLines: 4,
                          textCapitalization: TextCapitalization.sentences,
                          decoration: const InputDecoration(
                            hintText: 'Mesaj yaz…',
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                          onSubmitted: (_) => _send(),
                        ),
                      ),
                      IconButton.filled(onPressed: _send, icon: const Icon(Icons.send)),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message, required this.mine});

  final ChatMessage message;
  final bool mine;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 3),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: mine ? scheme.primary : scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          message.body,
          style: TextStyle(color: mine ? scheme.onPrimary : scheme.onSurface),
        ),
      ),
    );
  }
}
