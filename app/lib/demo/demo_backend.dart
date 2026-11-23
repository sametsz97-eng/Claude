// TARAYICI DEMOSU: Supabase yerine bellek içinde çalışan sahte backend.
// Gerçek uygulamada KULLANILMAZ (sadece lib/demo/main_demo.dart).
// Sunucudaki RPC'lerin cevap biçimlerini taklit eder; bir "bot" sohbet
// arkadaşı eşleşir, mesajlara cevap verir ve arkadaşlık isteklerini kabul eder.
import 'dart:async';
import 'dart:math';

import '../core/realtime_bridge.dart';

class DemoError implements Exception {
  DemoError(this.code);
  final String code;
}

class _Bot {
  _Bot(this.id, this.nickname, this.emoji);
  final String id;
  final String nickname;
  final String emoji;
}

class DemoBackend {
  DemoBackend() {
    _seed();
  }

  final _rnd = Random();
  final realtime = DemoRealtime();

  // ---- "ben" ----
  final String myId = _uuid(Random());
  String nickname = 'Sessiz Martı';
  String emoji = '🐦';
  int rerolls = 0;
  String? gender;
  bool verified = false;
  bool consents = false;
  String? currentMatchId;
  String? lastPartnerId;
  DateTime? queueSince;
  int friendRequestsSentToday = 0;
  static const dailyLimit = 3;

  final Map<String, _Bot> _bots = {};
  final Map<String, Map<String, dynamic>> _matches = {};
  final List<Map<String, dynamic>> _messages = [];
  final List<Map<String, dynamic>> _requests = [];
  final Map<String, Map<String, dynamic>> _friendships = {};
  final List<Map<String, dynamic>> _friendMessages = [];
  final Set<String> _blocked = {};
  int _msgSeq = 1;

  static const _names = [
    ['Neşeli Tilki', '🦊'],
    ['Gizemli Baykuş', '🦉'],
    ['Uykucu Panda', '🐼'],
    ['Meraklı Yunus', '🐬'],
    ['Cesur Aslan', '🦁'],
    ['Sakin Kaplumbağa', '🐢'],
    ['Şakacı Penguen', '🐧'],
    ['Gezgin Kelebek', '🦋'],
    ['Bilge Ahtapot', '🐙'],
    ['Tatlı Koala', '🐨'],
    ['Hayalperest Balina', '🐳'],
    ['Yıldızlı Kirpi', '🦔'],
  ];

  static const _greetings = [
    'Selam! 👋 Nasılsın?',
    'Merhaba :) Nerelisin?',
    'Hey! Bugün nasıl geçti?',
  ];

  static const _replies = [
    'Haha, aynen öyle 😄',
    'Gerçekten mi? Anlatsana biraz.',
    'Ben de genelde akşamları buradayım.',
    'Bugün biraz yorgunum ama sohbet iyi geldi 🙂',
    'En son hangi diziyi izledin?',
    'Müzik dinler misin? Ne tür seversin?',
    'Çok güzel bir soru, hiç düşünmemiştim 🤔',
    'Aynı fikirdeyim!',
  ];

  void _seed() {
    final friend = _newBot('Neşeli Tilki', '🦊');
    final fid = _uuid(_rnd);
    _friendships[fid] = {
      'id': fid,
      'bot': friend.id,
      'created_at': _iso(DateTime.now().subtract(const Duration(days: 2))),
      'removed_at': null,
    };
    _addFriendMessage(
      fid,
      friend.id,
      'Dün konuştuğumuz film neydi? Unuttum 😅',
      at: DateTime.now().subtract(const Duration(hours: 5)),
    );
    _addFriendMessage(
      fid,
      myId,
      'Başlangıç (Inception) 🙂',
      at: DateTime.now().subtract(const Duration(hours: 4)),
      emit: false,
    );

    final requester = _newBot('Cesur Kurt', '🐺');
    _requests.add({
      'id': _uuid(_rnd),
      'from': requester.id,
      'to': myId,
      'status': 'pending',
      'created_at': _iso(DateTime.now().subtract(const Duration(minutes: 30))),
    });
  }

  _Bot _newBot([String? name, String? em]) {
    final pick = _names[_rnd.nextInt(_names.length)];
    final b = _Bot(_uuid(_rnd), name ?? pick[0], em ?? pick[1]);
    _bots[b.id] = b;
    return b;
  }

  // ------------------------------------------------------------------
  // Oturum
  Map<String, dynamic> sessionState() => {
    'banned': false,
    'ban_until': null,
    'ban_permanent': false,
    'consent_version': 'kvkk-v1',
    'consents_ok': consents,
    'profile': {
      'nickname': nickname,
      'emoji': emoji,
      'can_reroll': rerolls < 1,
      'gender': gender,
      'gender_verified': verified,
      'needs_reverification': false,
    },
    'current_match_id': currentMatchId,
    'in_queue': queueSince != null,
  };

  /// RPC çağrısı (`POST /rest/v1/rpc/{name}`)
  Object? rpc(String name, Map<String, dynamic> p) {
    switch (name) {
      case 'bootstrap_session':
      case 'get_session_state':
        return sessionState();
      case 'accept_consents':
        if (p['p_age_confirmed'] != true || p['p_kvkk_accepted'] != true) {
          throw DemoError('consents_required');
        }
        consents = true;
        return sessionState();
      case 'reroll_nickname':
        if (rerolls >= 1) throw DemoError('reroll_limit');
        final pick = _names[_rnd.nextInt(_names.length)];
        nickname = pick[0];
        emoji = pick[1];
        rerolls++;
        return sessionState();
      case 'set_gender':
        if (verified) throw DemoError('gender_locked');
        gender = p['p_gender'] as String?;
        return sessionState();
      case 'delete_account':
        return null;
      case 'join_queue':
        if (!verified) throw DemoError('verification_required');
        if (currentMatchId != null) return {'status': 'matched', 'match_id': currentMatchId};
        queueSince = DateTime.now();
        return _waiting(2);
      case 'heartbeat_queue':
        return _heartbeat();
      case 'leave_queue':
        queueSince = null;
        return null;
      case 'get_match':
        return _getMatch(p['p_match_id'] as String);
      case 'end_match':
        _endMatch(p['p_match_id'] as String);
        return null;
      case 'block_partner':
        final m = _match(p['p_match_id'] as String);
        _blockBot(m['b'] as String);
        _endMatch(m['id'] as String);
        return null;
      case 'report_partner':
        final m = _match(p['p_match_id'] as String);
        _blockBot(m['b'] as String);
        _endMatch(m['id'] as String);
        return {'counted': true};
      case 'send_friend_request':
        return _sendFriendRequest(p['p_match_id'] as String);
      case 'respond_friend_request':
        return _respond(p['p_request_id'] as String, p['p_accept'] == true);
      case 'get_friends_overview':
        return _overview();
      case 'get_friendship':
        final f = _friendship(p['p_friendship_id'] as String);
        final bot = _bots[f['bot']]!;
        return {
          'id': f['id'],
          'active': f['removed_at'] == null,
          'since': f['created_at'],
          'partner_nickname': bot.nickname,
          'partner_emoji': bot.emoji,
        };
      case 'remove_friend':
        _removeFriendship(p['p_friendship_id'] as String);
        return null;
      case 'block_friend':
        final f = _friendship(p['p_friendship_id'] as String);
        _blockBot(f['bot'] as String);
        return null;
      case 'report_friend':
        final f = _friendship(p['p_friendship_id'] as String);
        _blockBot(f['bot'] as String);
        return {'counted': true};
    }
    throw DemoError('unknown_rpc:$name');
  }

  /// Doğrulama Edge Function'ı (mock her zaman başarılı)
  Map<String, dynamic> confirmVerification() {
    if (gender == null) throw DemoError('gender_required');
    verified = true;
    return {'verified': true};
  }

  // ------------------------------------------------------------------
  // Eşleşme
  Map<String, dynamic> _waiting(int position) => {
    'status': 'waiting',
    'position': position,
    'same_waiting': position + 1,
    'opposite_waiting': 0,
    'eta_seconds': position == 1 ? 12 : 45,
  };

  Map<String, dynamic> _heartbeat() {
    if (currentMatchId != null) return {'status': 'matched', 'match_id': currentMatchId};
    final since = queueSince;
    if (since == null) return {'status': 'idle'};
    if (DateTime.now().difference(since) < const Duration(seconds: 6)) return _waiting(1);

    var bot = _newBot();
    while (_blocked.contains(bot.id) || bot.id == lastPartnerId) {
      bot = _newBot();
    }
    final id = _uuid(_rnd);
    final m = {
      'id': id,
      'user_a': myId,
      'user_b': bot.id,
      'b': bot.id,
      'status': 'active',
      'started_at': _iso(DateTime.now()),
      'ended_at': null,
      'ended_by': null,
    };
    _matches[id] = m;
    currentMatchId = id;
    lastPartnerId = bot.id;
    queueSince = null;
    realtime.emit('matches', RowEvent.insert, _publicMatch(m));
    _later(1400, () {
      if (m['status'] == 'active') {
        _addMessage(id, bot.id, _greetings[_rnd.nextInt(_greetings.length)]);
      }
    });
    return {'status': 'matched', 'match_id': id};
  }

  Map<String, dynamic> _publicMatch(Map<String, dynamic> m) => Map.of(m)..remove('b');

  Map<String, dynamic> _match(String id) {
    final m = _matches[id];
    if (m == null) throw DemoError('match_not_found');
    return m;
  }

  Map<String, dynamic> _getMatch(String id) {
    final m = _match(id);
    final bot = _bots[m['b']]!;
    return {
      'id': id,
      'status': m['status'],
      'started_at': m['started_at'],
      'ended_at': m['ended_at'],
      'ended_by_me': m['ended_by'] == myId,
      'partner_nickname': bot.nickname,
      'partner_emoji': bot.emoji,
    };
  }

  void _endMatch(String id) {
    final m = _match(id);
    if (m['status'] != 'active') return;
    m['status'] = 'ended';
    m['ended_at'] = _iso(DateTime.now());
    m['ended_by'] = myId;
    if (currentMatchId == id) currentMatchId = null;
    realtime.emit('matches', RowEvent.update, _publicMatch(m));
  }

  void _blockBot(String botId) {
    _blocked.add(botId);
    for (final f in _friendships.values) {
      if (f['bot'] == botId && f['removed_at'] == null) _removeFriendship(f['id'] as String);
    }
  }

  // ------------------------------------------------------------------
  // Mesajlar (GET/POST /rest/v1/messages)
  List<Map<String, dynamic>> listMessages(String matchId) =>
      _messages.where((m) => m['match_id'] == matchId).toList();

  void insertMessage(Map<String, dynamic> row) {
    final matchId = row['match_id'] as String;
    final m = _match(matchId);
    if (m['status'] != 'active') throw DemoError('42501');
    final body = (row['body'] as String).trim();
    _addMessage(matchId, myId, body);
    _later(1200 + _rnd.nextInt(1500), () {
      if (m['status'] == 'active') {
        _addMessage(matchId, m['b'] as String, _replies[_rnd.nextInt(_replies.length)]);
      }
    });
  }

  void _addMessage(String matchId, String sender, String body) {
    final row = {
      'id': _msgSeq++,
      'match_id': matchId,
      'sender_id': sender,
      'body': body,
      'created_at': _iso(DateTime.now()),
    };
    _messages.add(row);
    realtime.emit('messages', RowEvent.insert, row);
  }

  // ------------------------------------------------------------------
  // Arkadaşlık
  Map<String, dynamic> _sendFriendRequest(String matchId) {
    final m = _match(matchId);
    final botId = m['b'] as String;
    if (_blocked.contains(botId)) throw DemoError('friend_blocked');
    if (_friendships.values.any((f) => f['bot'] == botId && f['removed_at'] == null)) {
      throw DemoError('already_friends');
    }
    if (_requests.any((r) => r['from'] == myId && r['to'] == botId && r['status'] == 'pending')) {
      throw DemoError('friend_request_pending');
    }
    if (friendRequestsSentToday >= dailyLimit) throw DemoError('friend_daily_limit');
    friendRequestsSentToday++;
    final req = {
      'id': _uuid(_rnd),
      'from': myId,
      'to': botId,
      'status': 'pending',
      'created_at': _iso(DateTime.now()),
    };
    _requests.add(req);
    realtime.emit('friend_requests', RowEvent.insert, req);

    // Bot birkaç saniye sonra kabul eder
    _later(2500, () {
      if (req['status'] != 'pending' || _blocked.contains(botId)) return;
      req['status'] = 'accepted';
      realtime.emit('friend_requests', RowEvent.update, req);
      final fid = _createFriendship(botId);
      _later(1500, () => _addFriendMessage(fid, botId, 'İsteğini kabul ettim, arkadaş olalım 😊'));
    });
    return {'status': 'sent', 'remaining_today': dailyLimit - friendRequestsSentToday};
  }

  Map<String, dynamic> _respond(String requestId, bool accept) {
    final r = _requests.firstWhere(
      (r) => r['id'] == requestId && r['to'] == myId && r['status'] == 'pending',
      orElse: () => throw DemoError('friend_request_not_found'),
    );
    r['status'] = accept ? 'accepted' : 'declined';
    realtime.emit('friend_requests', RowEvent.update, r);
    if (!accept) return {'status': 'declined'};
    final fid = _createFriendship(r['from'] as String);
    _later(
      2000,
      () => _addFriendMessage(fid, r['from'] as String, 'Kabul ettiğin için teşekkürler! 🙌'),
    );
    return {'status': 'accepted', 'friendship_id': fid};
  }

  String _createFriendship(String botId) {
    final existing = _friendships.values.where((f) => f['bot'] == botId).firstOrNull;
    if (existing != null) {
      existing['removed_at'] = null;
      existing['created_at'] = _iso(DateTime.now());
      realtime.emit('friendships', RowEvent.update, existing);
      return existing['id'] as String;
    }
    final fid = _uuid(_rnd);
    final f = {'id': fid, 'bot': botId, 'created_at': _iso(DateTime.now()), 'removed_at': null};
    _friendships[fid] = f;
    realtime.emit('friendships', RowEvent.insert, f);
    return fid;
  }

  Map<String, dynamic> _friendship(String id) {
    final f = _friendships[id];
    if (f == null) throw DemoError('friendship_not_found');
    return f;
  }

  void _removeFriendship(String id) {
    final f = _friendship(id);
    _friendMessages.removeWhere((m) => m['friendship_id'] == id);
    f['removed_at'] = _iso(DateTime.now());
    realtime.emit('friendships', RowEvent.update, f);
  }

  Map<String, dynamic> _overview() {
    final friends =
        _friendships.values.where((f) => f['removed_at'] == null).map((f) {
          final bot = _bots[f['bot']]!;
          final msgs = _friendMessages.where((m) => m['friendship_id'] == f['id']).toList();
          final last = msgs.isEmpty ? null : msgs.last;
          return {
            'friendship_id': f['id'],
            'nickname': bot.nickname,
            'emoji': bot.emoji,
            'since': f['created_at'],
            'last_message': last?['body'],
            'last_message_at': last?['created_at'],
            'last_message_mine': last?['sender_id'] == myId,
          };
        }).toList()..sort(
          (a, b) => ((b['last_message_at'] ?? b['since']) as String).compareTo(
            (a['last_message_at'] ?? a['since']) as String,
          ),
        );
    return {
      'daily_limit': dailyLimit,
      'remaining_today': max(dailyLimit - friendRequestsSentToday, 0),
      'friends': friends,
      'incoming': _requests.where((r) => r['to'] == myId && r['status'] == 'pending').map((r) {
        final bot = _bots[r['from']]!;
        return {
          'request_id': r['id'],
          'nickname': bot.nickname,
          'emoji': bot.emoji,
          'created_at': r['created_at'],
        };
      }).toList(),
      'outgoing_pending': _requests
          .where((r) => r['from'] == myId && r['status'] == 'pending')
          .length,
    };
  }

  List<Map<String, dynamic>> listFriendMessages(String friendshipId) =>
      _friendMessages.where((m) => m['friendship_id'] == friendshipId).toList();

  void insertFriendMessage(Map<String, dynamic> row) {
    final fid = row['friendship_id'] as String;
    final f = _friendship(fid);
    if (f['removed_at'] != null) throw DemoError('42501');
    _addFriendMessage(fid, myId, (row['body'] as String).trim());
    _later(1500 + _rnd.nextInt(1500), () {
      if (f['removed_at'] == null) {
        _addFriendMessage(fid, f['bot'] as String, _replies[_rnd.nextInt(_replies.length)]);
      }
    });
  }

  String _addFriendMessage(
    String fid,
    String sender,
    String body, {
    DateTime? at,
    bool emit = true,
  }) {
    final row = {
      'id': _msgSeq++,
      'friendship_id': fid,
      'sender_id': sender,
      'body': body,
      'created_at': _iso(at ?? DateTime.now()),
    };
    _friendMessages.add(row);
    if (emit) realtime.emit('friend_messages', RowEvent.insert, row);
    return fid;
  }

  // ------------------------------------------------------------------
  void _later(int ms, void Function() f) => Timer(Duration(milliseconds: ms), f);

  static String _iso(DateTime d) => d.toUtc().toIso8601String();

  static String _uuid(Random r) {
    String hex(int n) => List.generate(n, (_) => r.nextInt(16).toRadixString(16)).join();
    return '${hex(8)}-${hex(4)}-4${hex(3)}-a${hex(3)}-${hex(12)}';
  }
}

/// Bellek içi Realtime: sahte backend'deki değişiklikleri abonelere iletir.
class DemoRealtime implements RealtimeBridge {
  final List<(List<RowListener>, void Function(String, Map<String, dynamic>))> _subs = [];

  @override
  RowSubscription listen(
    List<RowListener> listeners,
    void Function(String table, Map<String, dynamic> newRecord) onRow,
  ) {
    final entry = (listeners, onRow);
    _subs.add(entry);
    return RowSubscription(() => _subs.remove(entry));
  }

  void emit(String table, RowEvent event, Map<String, dynamic> row) {
    for (final (listeners, cb) in List.of(_subs)) {
      for (final l in listeners) {
        if (l.table != table) continue;
        if (l.event != RowEvent.all && l.event != event) continue;
        if (l.eqColumn != null && row[l.eqColumn] != l.eqValue) continue;
        // Gerçek Realtime gibi asenkron teslim et
        scheduleMicrotask(() => cb(table, Map.of(row)));
        break;
      }
    }
  }
}
