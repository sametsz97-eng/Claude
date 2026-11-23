/// Bekleme ekranındaki tahmini süre metni.
String formatEta(int seconds) {
  if (seconds <= 15) return 'birkaç saniye';
  if (seconds < 60) return '1 dakikadan az';
  if (seconds >= 3600) return '1 saatten fazla';
  final minutes = (seconds / 60).ceil();
  return '~$minutes dk';
}

String formatBanUntil(DateTime until) {
  final l = until.toLocal();
  String two(int v) => v.toString().padLeft(2, '0');
  return '${two(l.day)}.${two(l.month)}.${l.year} ${two(l.hour)}:${two(l.minute)}';
}
