import 'package:material_ui/material_ui.dart';

import 'chat_repository.dart';

/// Rastgele sohbet ve arkadaş sohbetinde ortak mesaj listesi.
class MessageList extends StatelessWidget {
  const MessageList({
    super.key,
    required this.messages,
    required this.myId,
    required this.controller,
    this.error,
    this.emptyText,
  });

  final List<ChatMessage> messages;
  final String myId;
  final ScrollController controller;
  final String? error;
  final String? emptyText;

  @override
  Widget build(BuildContext context) {
    if (error != null) return Center(child: Text(error!));
    if (messages.isEmpty && emptyText != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(emptyText!, textAlign: TextAlign.center),
        ),
      );
    }
    return ListView.builder(
      controller: controller,
      padding: const EdgeInsets.all(12),
      itemCount: messages.length,
      itemBuilder: (_, i) {
        final m = messages[i];
        return MessageBubble(message: m, mine: m.senderId == myId);
      },
    );
  }
}

class MessageComposer extends StatelessWidget {
  const MessageComposer({super.key, required this.controller, required this.onSend});

  final TextEditingController controller;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 8, 8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              minLines: 1,
              maxLines: 4,
              textCapitalization: TextCapitalization.sentences,
              textInputAction: TextInputAction.send,
              decoration: const InputDecoration(
                hintText: 'Mesaj yaz…',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onSubmitted: (_) => onSend(),
            ),
          ),
          IconButton.filled(onPressed: onSend, icon: const Icon(Icons.send)),
        ],
      ),
    );
  }
}

class MessageBubble extends StatelessWidget {
  const MessageBubble({super.key, required this.message, required this.mine});

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

/// Onay diyaloğu (engelle, sil, sohbeti bitir vb.)
Future<bool> confirmDialog(BuildContext context, String title, String body) async {
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
