/// Türkiye cep numarasını E.164 biçimine çevirir: "0532 123 45 67" -> "+905321234567".
/// Geçersizse null döner.
String? normalizeTurkishMobile(String input) {
  var digits = input.replaceAll(RegExp(r'\D'), '');
  if (digits.startsWith('90') && digits.length == 12) digits = digits.substring(2);
  if (digits.startsWith('0') && digits.length == 11) digits = digits.substring(1);
  if (digits.length != 10 || !digits.startsWith('5')) return null;
  return '+90$digits';
}
