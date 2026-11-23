import 'package:material_ui/material_ui.dart';

import 'chat_repository.dart';

class ReportSelection {
  const ReportSelection(this.category, this.note);
  final ReportCategory category;
  final String? note;
}

/// Şikâyet kategorisi seçimi. Seçim yapılmazsa null döner.
Future<ReportSelection?> showReportSheet(BuildContext context) {
  return showModalBottomSheet<ReportSelection>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => const _ReportSheet(),
  );
}

class _ReportSheet extends StatefulWidget {
  const _ReportSheet();

  @override
  State<_ReportSheet> createState() => _ReportSheetState();
}

class _ReportSheetState extends State<_ReportSheet> {
  ReportCategory? _category;
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Şikâyet et', style: theme.textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(
            'Şikâyet ettiğin kişi otomatik olarak engellenir ve bir daha karşına çıkmaz.',
            style: theme.textTheme.bodySmall,
          ),
          RadioGroup<ReportCategory>(
            groupValue: _category,
            onChanged: (v) => setState(() => _category = v),
            child: Column(
              children: [
                for (final c in ReportCategory.values)
                  RadioListTile<ReportCategory>(value: c, title: Text(c.label)),
              ],
            ),
          ),
          TextField(
            controller: _note,
            maxLength: 500,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Açıklama (isteğe bağlı)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _category == null
                ? null
                : () => Navigator.pop(
                    context,
                    ReportSelection(
                      _category!,
                      _note.text.trim().isEmpty ? null : _note.text.trim(),
                    ),
                  ),
            child: const Text('Gönder'),
          ),
        ],
      ),
    );
  }
}
