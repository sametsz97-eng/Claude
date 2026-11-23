import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/realtime_bridge.dart';

import '../../core/errors.dart';
import '../chat/chat_repository.dart';
import '../chat/chat_widgets.dart';
import '../chat/report_sheet.dart';
import '../common/status_screens.dart';
import 'friends_repository.dart';

class FriendChatScreen extends StatefulWidget {
  const FriendChatScreen({super.key, required this.friendshipId});

  final String friendshipId;

  @override
  State<FriendChatScreen> createState() => _FriendChatScreenState();
}

class _FriendChatScreenState extends State<FriendChatScreen> with BusyState {
  final _repo = FriendsRepository();
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<ChatMessage> _messages = [];
  final Set<int> _ids = {};
  RowSubscription? _channel;
  FriendshipInfo? _info;
  bool _removed = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _channel = _repo.subscribeChat(
      widget.friendshipId,
      onMessage: _addMessage,
      onRemoved: () {
        if (mounted) setState(() => _removed = true);
      },
    );
    _load();
  }

  Future<void> _load() async {
    try {
      final info = await _repo.loadFriendship(widget.friendshipId);
      final messages = info.active
          ? await _repo.loadMessages(widget.friendshipId)
          : <ChatMessage>[];
      if (!mounted) return;
      setState(() {
        _info = info;
        _removed = !info.active;
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
    if (text.isEmpty || _removed) return;
    if (text.length > 1000) {
      showError('Mesaj en fazla 1000 karakter olabilir.');
      return;
    }
    _input.clear();
    try {
      await _repo.send(widget.friendshipId, text);
    } catch (e) {
      _input.text = text;
      showError(friendlyError(e));
    }
  }

  Future<void> _remove() async {
    final ok = await confirmDialog(
      context,
      'Arkadaşlıktan çıkar',
      'Arkadaşlığınız ve mesaj geçmişiniz iki taraf için de silinecek.',
    );
    if (!ok) return;
    await runBusy(() async {
      await _repo.remove(widget.friendshipId);
      if (mounted) context.pop();
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<void> _block() async {
    final ok = await confirmDialog(
      context,
      'Engelle',
      'Bu kişi engellenecek ve arkadaşlarından çıkarılacak. Bir daha asla eşleşmeyeceksiniz.',
    );
    if (!ok) return;
    await runBusy(() async {
      await _repo.block(widget.friendshipId);
      if (mounted) context.pop();
    }, onError: (e) => showError(friendlyError(e)));
  }

  Future<void> _report() async {
    final selection = await showReportSheet(context);
    if (selection == null || !mounted) return;
    await runBusy(() async {
      await _repo.report(widget.friendshipId, selection.category, selection.note);
      showError('Şikâyetin alındı. Bu kişi engellendi ve arkadaşlarından çıkarıldı.');
      if (mounted) context.pop();
    }, onError: (e) => showError(friendlyError(e)));
  }

  @override
  void dispose() {
    _channel?.cancel();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final info = _info;
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Text(info?.partnerEmoji ?? '👤', style: const TextStyle(fontSize: 24)),
            const SizedBox(width: 8),
            Flexible(child: Text(info?.partnerNickname ?? '…', overflow: TextOverflow.ellipsis)),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            enabled: !busy && !_removed,
            onSelected: (v) {
              switch (v) {
                case 'remove':
                  _remove();
                case 'block':
                  _block();
                case 'report':
                  _report();
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'remove', child: Text('Arkadaşlıktan çıkar')),
              PopupMenuItem(value: 'block', child: Text('Engelle')),
              PopupMenuItem(value: 'report', child: Text('Şikâyet et')),
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
                emptyText: _removed ? null : 'Arkadaşına ilk mesajı sen gönder 👋',
              ),
            ),
            if (_removed)
              Container(
                width: double.infinity,
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                padding: const EdgeInsets.all(16),
                child: const Text('Bu arkadaşlık sona erdi.', textAlign: TextAlign.center),
              )
            else
              MessageComposer(controller: _input, onSend: _send),
          ],
        ),
      ),
    );
  }
}
