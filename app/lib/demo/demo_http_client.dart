// TARAYICI DEMOSU: Supabase istemcisinin HTTP isteklerini sahte backend'e yönlendirir.
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'demo_backend.dart';

http.Client demoHttpClient(DemoBackend backend) => MockClient((req) async {
  await Future<void>.delayed(const Duration(milliseconds: 120)); // ağ gecikmesi hissi
  http.Response res;
  try {
    res = _route(backend, req);
  } on DemoError catch (e) {
    res = e.code == '42501'
        ? _json({
            'code': '42501',
            'message': 'new row violates row-level security policy',
          }, status: 403)
        : _json({'code': 'P0001', 'message': e.code, 'details': null, 'hint': null}, status: 400);
  }
  return _withRequest(res, req);
});

/// postgrest-dart cevabın isteğini (response.request) okur; MockClient bunu doldurmaz.
http.Response _withRequest(http.Response r, http.Request req) =>
    http.Response.bytes(r.bodyBytes, r.statusCode, headers: r.headers, request: req);

http.Response _json(Object? body, {int status = 200}) => http.Response.bytes(
  utf8.encode(jsonEncode(body)),
  status,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Map<String, dynamic> _body(http.Request req) {
  if (req.body.isEmpty) return {};
  final decoded = jsonDecode(req.body);
  if (decoded is Map) return Map<String, dynamic>.from(decoded);
  if (decoded is List && decoded.isNotEmpty) return Map<String, dynamic>.from(decoded.first as Map);
  return {};
}

String? _eq(http.Request req, String column) {
  final v = req.url.queryParameters[column];
  return v != null && v.startsWith('eq.') ? v.substring(3) : null;
}

http.Response _route(DemoBackend b, http.Request req) {
  final path = req.url.path;

  // ---- Auth ----
  if (path.endsWith('/auth/v1/otp')) return _json({});
  if (path.endsWith('/auth/v1/verify')) {
    final body = _body(req);
    if ((body['token'] as String? ?? '').length != 6) {
      return _json({
        'code': 403,
        'error_code': 'otp_expired',
        'msg': 'Token has expired or is invalid',
      }, status: 403);
    }
    return _json(_session(b, body['phone'] as String? ?? ''));
  }
  if (path.endsWith('/auth/v1/logout')) return http.Response('', 204);
  if (path.endsWith('/auth/v1/user')) return _json(_user(b, ''));

  // ---- Edge Function ----
  if (path.endsWith('/functions/v1/confirm-verification')) return _json(b.confirmVerification());

  // ---- RPC ----
  const rpcPrefix = '/rest/v1/rpc/';
  final rpcIndex = path.indexOf(rpcPrefix);
  if (rpcIndex >= 0) {
    return _json(b.rpc(path.substring(rpcIndex + rpcPrefix.length), _body(req)));
  }

  // ---- Tablolar ----
  if (path.endsWith('/rest/v1/messages')) {
    if (req.method == 'GET') return _json(b.listMessages(_eq(req, 'match_id') ?? ''));
    b.insertMessage(_body(req));
    return http.Response('', 201);
  }
  if (path.endsWith('/rest/v1/friend_messages')) {
    if (req.method == 'GET') {
      final rows = b.listFriendMessages(_eq(req, 'friendship_id') ?? '');
      final desc = req.url.queryParameters['order']?.endsWith('.desc') ?? false;
      return _json(desc ? rows.reversed.toList() : rows);
    }
    b.insertFriendMessage(_body(req));
    return http.Response('', 201);
  }

  return _json({'message': 'demo: bilinmeyen istek $path'}, status: 404);
}

Map<String, dynamic> _user(DemoBackend b, String phone) => {
  'id': b.myId,
  'aud': 'authenticated',
  'role': 'authenticated',
  'phone': phone.replaceAll('+', ''),
  'app_metadata': {'provider': 'phone'},
  'user_metadata': <String, dynamic>{},
  'created_at': DateTime.now().toUtc().toIso8601String(),
};

Map<String, dynamic> _session(DemoBackend b, String phone) {
  final exp = DateTime.now().add(const Duration(days: 1)).millisecondsSinceEpoch ~/ 1000;
  String seg(Map<String, dynamic> m) =>
      base64Url.encode(utf8.encode(jsonEncode(m))).replaceAll('=', '');
  final jwt =
      '${seg({'alg': 'HS256', 'typ': 'JWT'})}.'
      '${seg({'sub': b.myId, 'role': 'authenticated', 'aud': 'authenticated', 'exp': exp})}.demo';
  return {
    'access_token': jwt,
    'token_type': 'bearer',
    'expires_in': 86400,
    'expires_at': exp,
    'refresh_token': 'demo-refresh',
    'user': _user(b, phone),
  };
}
