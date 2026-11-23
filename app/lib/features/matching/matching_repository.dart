import '../../core/realtime_bridge.dart';
import '../../core/supabase.dart';

/// Sunucudaki join_queue / heartbeat_queue cevabı.
class QueueStatus {
  const QueueStatus({
    required this.status,
    this.matchId,
    this.position = 0,
    this.sameWaiting = 0,
    this.oppositeWaiting = 0,
    this.etaSeconds = 0,
  });

  /// 'waiting' | 'matched' | 'idle' | 'banned'
  final String status;
  final String? matchId;
  final int position;
  final int sameWaiting;
  final int oppositeWaiting;
  final int etaSeconds;

  bool get isMatched => status == 'matched' && matchId != null;

  factory QueueStatus.fromJson(Map<String, dynamic> j) => QueueStatus(
    status: j['status'] as String? ?? 'idle',
    matchId: j['match_id'] as String?,
    position: (j['position'] as num?)?.toInt() ?? 0,
    sameWaiting: (j['same_waiting'] as num?)?.toInt() ?? 0,
    oppositeWaiting: (j['opposite_waiting'] as num?)?.toInt() ?? 0,
    etaSeconds: (j['eta_seconds'] as num?)?.toInt() ?? 0,
  );
}

class MatchingRepository {
  Future<QueueStatus> join() async =>
      QueueStatus.fromJson(Map<String, dynamic>.from(await supabase.rpc('join_queue') as Map));

  Future<QueueStatus> heartbeat() async =>
      QueueStatus.fromJson(Map<String, dynamic>.from(await supabase.rpc('heartbeat_queue') as Map));

  Future<void> leave() => supabase.rpc('leave_queue');

  /// Yeni eşleşme oluştuğunda tetiklenir (RLS sayesinde sadece kendi eşleşmelerin gelir).
  RowSubscription subscribeToNewMatches(void Function(String matchId) onMatch) {
    return RealtimeBridge.instance.listen(
      const [RowListener(table: 'matches', event: RowEvent.insert)],
      (_, row) {
        final id = row['id'];
        if (id is String) onMatch(id);
      },
    );
  }
}
