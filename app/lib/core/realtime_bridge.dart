import 'package:supabase_flutter/supabase_flutter.dart';

import 'supabase.dart';

enum RowEvent { insert, update, all }

/// Bir Realtime aboneliği. [cancel] ile kapatılır.
class RowSubscription {
  RowSubscription(this._cancel);

  final void Function() _cancel;
  bool _cancelled = false;

  void cancel() {
    if (_cancelled) return;
    _cancelled = true;
    _cancel();
  }
}

class RowListener {
  const RowListener({required this.table, required this.event, this.eqColumn, this.eqValue});

  final String table;
  final RowEvent event;
  final String? eqColumn;
  final Object? eqValue;
}

/// Realtime soyutlaması: üretimde Supabase Realtime (postgres_changes),
/// tarayıcı demosunda bellek içi sahte backend.
abstract class RealtimeBridge {
  static RealtimeBridge instance = SupabaseRealtimeBridge();

  /// [listeners] içindeki her değişiklikte [onRow] yeni satırla çağrılır.
  RowSubscription listen(
    List<RowListener> listeners,
    void Function(String table, Map<String, dynamic> newRecord) onRow,
  );
}

class SupabaseRealtimeBridge implements RealtimeBridge {
  int _seq = 0;

  @override
  RowSubscription listen(
    List<RowListener> listeners,
    void Function(String table, Map<String, dynamic> newRecord) onRow,
  ) {
    var channel = supabase.channel('rt-${DateTime.now().microsecondsSinceEpoch}-${_seq++}');
    for (final l in listeners) {
      channel = channel.onPostgresChanges(
        event: switch (l.event) {
          RowEvent.insert => PostgresChangeEvent.insert,
          RowEvent.update => PostgresChangeEvent.update,
          RowEvent.all => PostgresChangeEvent.all,
        },
        schema: 'public',
        table: l.table,
        filter: l.eqColumn == null
            ? null
            : PostgresChangeFilter(
                type: PostgresChangeFilterType.eq,
                column: l.eqColumn!,
                value: l.eqValue,
              ),
        callback: (p) => onRow(l.table, p.newRecord),
      );
    }
    channel.subscribe();
    return RowSubscription(() => supabase.removeChannel(channel));
  }
}
