import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/supabase.dart';

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.senderId,
    required this.body,
    required this.createdAt,
  });

  final int id;
  final String senderId;
  final String body;
  final DateTime createdAt;

  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
    id: (j['id'] as num).toInt(),
    senderId: j['sender_id'] as String,
    body: j['body'] as String,
    createdAt: DateTime.parse(j['created_at'] as String),
  );
}

class MatchInfo {
  const MatchInfo({
    required this.id,
    required this.active,
    required this.partnerNickname,
    required this.partnerEmoji,
    required this.endedByMe,
  });

  final String id;
  final bool active;
  final String partnerNickname;
  final String partnerEmoji;
  final bool endedByMe;

  factory MatchInfo.fromJson(Map<String, dynamic> j) => MatchInfo(
    id: j['id'] as String,
    active: j['status'] == 'active',
    partnerNickname: j['partner_nickname'] as String? ?? '',
    partnerEmoji: j['partner_emoji'] as String? ?? '👤',
    endedByMe: j['ended_by_me'] as bool? ?? false,
  );
}

enum ReportCategory {
  harassment('harassment', 'Taciz'),
  profanity('profanity', 'Küfür / hakaret'),
  nsfw('nsfw', '+18 içerik'),
  genderMismatch('gender_mismatch', 'Cinsiyeti farklı');

  const ReportCategory(this.value, this.label);
  final String value;
  final String label;
}

class ChatRepository {
  ChatRepository(this.matchId);

  final String matchId;

  String get myId => supabase.auth.currentUser!.id;

  Future<MatchInfo> loadMatch() async => MatchInfo.fromJson(
    Map<String, dynamic>.from(
      await supabase.rpc('get_match', params: {'p_match_id': matchId}) as Map,
    ),
  );

  Future<List<ChatMessage>> loadMessages() async {
    final rows = await supabase
        .from('messages')
        .select('id, sender_id, body, created_at')
        .eq('match_id', matchId)
        .order('created_at')
        .limit(500);
    return rows.map(ChatMessage.fromJson).toList();
  }

  Future<void> send(String body) =>
      supabase.from('messages').insert({'match_id': matchId, 'sender_id': myId, 'body': body});

  Future<void> end() => supabase.rpc('end_match', params: {'p_match_id': matchId});

  Future<void> block() => supabase.rpc('block_partner', params: {'p_match_id': matchId});

  Future<void> report(ReportCategory category, String? note) => supabase.rpc(
    'report_partner',
    params: {'p_match_id': matchId, 'p_category': category.value, 'p_note': note},
  );

  /// Yeni mesajlar ve sohbetin bitişi (Realtime, RLS ile filtrelenir).
  RealtimeChannel subscribe({
    required void Function(ChatMessage) onMessage,
    required void Function() onEnded,
  }) {
    return supabase
        .channel('chat-$matchId')
        .onPostgresChanges(
          event: PostgresChangeEvent.insert,
          schema: 'public',
          table: 'messages',
          filter: PostgresChangeFilter(
            type: PostgresChangeFilterType.eq,
            column: 'match_id',
            value: matchId,
          ),
          callback: (p) => onMessage(ChatMessage.fromJson(p.newRecord)),
        )
        .onPostgresChanges(
          event: PostgresChangeEvent.update,
          schema: 'public',
          table: 'matches',
          filter: PostgresChangeFilter(
            type: PostgresChangeFilterType.eq,
            column: 'id',
            value: matchId,
          ),
          callback: (p) {
            if (p.newRecord['status'] == 'ended') onEnded();
          },
        )
        .subscribe();
  }
}
