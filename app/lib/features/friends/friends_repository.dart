import '../../core/realtime_bridge.dart';
import '../../core/supabase.dart';
import '../chat/chat_repository.dart';

class Friend {
  const Friend({
    required this.friendshipId,
    required this.nickname,
    required this.emoji,
    this.lastMessage,
    this.lastMessageAt,
    this.lastMessageMine = false,
  });

  final String friendshipId;
  final String nickname;
  final String emoji;
  final String? lastMessage;
  final DateTime? lastMessageAt;
  final bool lastMessageMine;

  factory Friend.fromJson(Map<String, dynamic> j) => Friend(
    friendshipId: j['friendship_id'] as String,
    nickname: j['nickname'] as String? ?? '',
    emoji: j['emoji'] as String? ?? '👤',
    lastMessage: j['last_message'] as String?,
    lastMessageAt: j['last_message_at'] is String
        ? DateTime.tryParse(j['last_message_at'] as String)
        : null,
    lastMessageMine: j['last_message_mine'] as bool? ?? false,
  );
}

class FriendRequest {
  const FriendRequest({required this.id, required this.nickname, required this.emoji});

  final String id;
  final String nickname;
  final String emoji;

  factory FriendRequest.fromJson(Map<String, dynamic> j) => FriendRequest(
    id: j['request_id'] as String,
    nickname: j['nickname'] as String? ?? '',
    emoji: j['emoji'] as String? ?? '👤',
  );
}

class FriendsOverview {
  const FriendsOverview({
    required this.dailyLimit,
    required this.remainingToday,
    required this.friends,
    required this.incoming,
    required this.outgoingPending,
  });

  final int dailyLimit;
  final int remainingToday;
  final List<Friend> friends;
  final List<FriendRequest> incoming;
  final int outgoingPending;

  factory FriendsOverview.fromJson(Map<String, dynamic> j) {
    List<Map<String, dynamic>> list(Object? v) =>
        (v as List? ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList();
    return FriendsOverview(
      dailyLimit: (j['daily_limit'] as num?)?.toInt() ?? 3,
      remainingToday: (j['remaining_today'] as num?)?.toInt() ?? 0,
      friends: list(j['friends']).map(Friend.fromJson).toList(),
      incoming: list(j['incoming']).map(FriendRequest.fromJson).toList(),
      outgoingPending: (j['outgoing_pending'] as num?)?.toInt() ?? 0,
    );
  }
}

class FriendRequestResult {
  const FriendRequestResult({required this.accepted, required this.remainingToday});

  final bool accepted;
  final int remainingToday;
}

class FriendshipInfo {
  const FriendshipInfo({
    required this.id,
    required this.active,
    required this.partnerNickname,
    required this.partnerEmoji,
  });

  final String id;
  final bool active;
  final String partnerNickname;
  final String partnerEmoji;

  factory FriendshipInfo.fromJson(Map<String, dynamic> j) => FriendshipInfo(
    id: j['id'] as String,
    active: j['active'] as bool? ?? false,
    partnerNickname: j['partner_nickname'] as String? ?? '',
    partnerEmoji: j['partner_emoji'] as String? ?? '👤',
  );
}

Map<String, dynamic> _map(Object? v) => Map<String, dynamic>.from(v as Map);

class FriendsRepository {
  String get myId => supabase.auth.currentUser!.id;

  Future<FriendsOverview> overview() async =>
      FriendsOverview.fromJson(_map(await supabase.rpc('get_friends_overview')));

  /// Rastgele sohbetteki kişiye istek. Günde 3 hak (Türkiye saatiyle).
  Future<FriendRequestResult> sendRequest(String matchId) async {
    final r = _map(await supabase.rpc('send_friend_request', params: {'p_match_id': matchId}));
    return FriendRequestResult(
      accepted: r['status'] == 'accepted',
      remainingToday: (r['remaining_today'] as num?)?.toInt() ?? 0,
    );
  }

  Future<void> respond(String requestId, {required bool accept}) => supabase.rpc(
    'respond_friend_request',
    params: {'p_request_id': requestId, 'p_accept': accept},
  );

  Future<void> remove(String friendshipId) =>
      supabase.rpc('remove_friend', params: {'p_friendship_id': friendshipId});

  Future<void> block(String friendshipId) =>
      supabase.rpc('block_friend', params: {'p_friendship_id': friendshipId});

  Future<void> report(String friendshipId, ReportCategory category, String? note) => supabase.rpc(
    'report_friend',
    params: {'p_friendship_id': friendshipId, 'p_category': category.value, 'p_note': note},
  );

  Future<FriendshipInfo> loadFriendship(String friendshipId) async => FriendshipInfo.fromJson(
    _map(await supabase.rpc('get_friendship', params: {'p_friendship_id': friendshipId})),
  );

  Future<List<ChatMessage>> loadMessages(String friendshipId) async {
    final rows = await supabase
        .from('friend_messages')
        .select('id, sender_id, body, created_at')
        .eq('friendship_id', friendshipId)
        .order('created_at', ascending: false)
        .limit(500);
    return rows.map(ChatMessage.fromJson).toList().reversed.toList();
  }

  Future<void> send(String friendshipId, String body) => supabase.from('friend_messages').insert({
    'friendship_id': friendshipId,
    'sender_id': myId,
    'body': body,
  });

  /// Arkadaş sohbeti: yeni mesajlar ve arkadaşlığın kaldırılması.
  RowSubscription subscribeChat(
    String friendshipId, {
    required void Function(ChatMessage) onMessage,
    required void Function() onRemoved,
  }) {
    return RealtimeBridge.instance.listen(
      [
        RowListener(
          table: 'friend_messages',
          event: RowEvent.insert,
          eqColumn: 'friendship_id',
          eqValue: friendshipId,
        ),
        RowListener(
          table: 'friendships',
          event: RowEvent.update,
          eqColumn: 'id',
          eqValue: friendshipId,
        ),
      ],
      (table, row) {
        if (table == 'friend_messages') onMessage(ChatMessage.fromJson(row));
        if (table == 'friendships' && row['removed_at'] != null) onRemoved();
      },
    );
  }

  /// Arkadaş listesini/rozeti tazelemek için: yeni istek, kabul, silme, yeni mesaj.
  /// (RLS sayesinde sadece kendi satırların gelir.)
  RowSubscription subscribeOverview(void Function() onChange) {
    return RealtimeBridge.instance.listen(const [
      RowListener(table: 'friend_requests', event: RowEvent.all),
      RowListener(table: 'friendships', event: RowEvent.all),
      RowListener(table: 'friend_messages', event: RowEvent.all),
    ], (_, _) => onChange());
  }
}
