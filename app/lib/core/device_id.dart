import 'dart:io';

import 'package:android_id/android_id.dart';
import 'package:device_info_plus/device_info_plus.dart';

/// Ban'ları cihaza bağlamak için kullanılan cihaz kimliği.
/// Sunucuya ham gönderilir, sunucuda HMAC ile hash'lenip öyle saklanır.
/// Not: Android ID fabrika ayarlarında, iOS identifierForVendor ise uygulama
/// silinip yüklendiğinde değişebilir. Asıl güçlü engel telefon numarasıdır.
Future<String?> getDeviceId() async {
  try {
    if (Platform.isAndroid) return await const AndroidId().getId();
    if (Platform.isIOS) return (await DeviceInfoPlugin().iosInfo).identifierForVendor;
  } catch (_) {
    // Cihaz kimliği alınamazsa sadece telefon banı uygulanır.
  }
  return null;
}
