import 'package:anonim_sohbet/features/friends/friends_repository.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('FriendsOverview sunucu cevabını çözer', () {
    final o = FriendsOverview.fromJson({
      'daily_limit': 3,
      'remaining_today': 1,
      'outgoing_pending': 2,
      'friends': [
        {
          'friendship_id': 'f1',
          'nickname': 'Neşeli Tilki',
          'emoji': '🦊',
          'last_message': 'Selam',
          'last_message_at': '2026-11-23T10:00:00+00:00',
          'last_message_mine': true,
        },
        {'friendship_id': 'f2', 'nickname': 'Sakin Panda', 'emoji': '🐼'},
      ],
      'incoming': [
        {'request_id': 'r1', 'nickname': 'Cesur Kurt', 'emoji': '🐺'},
      ],
    });
    expect(o.remainingToday, 1);
    expect(o.outgoingPending, 2);
    expect(o.friends, hasLength(2));
    expect(o.friends.first.lastMessageMine, isTrue);
    expect(o.friends.first.lastMessageAt, isNotNull);
    expect(o.friends.last.lastMessage, isNull);
    expect(o.incoming.single.id, 'r1');
  });

  test('boş listeler', () {
    final o = FriendsOverview.fromJson({'daily_limit': 3, 'remaining_today': 3});
    expect(o.friends, isEmpty);
    expect(o.incoming, isEmpty);
  });
}
