/// Derleme zamanında verilir:
/// flutter run --dart-define=SUPABASE_URL=... --dart-define=SUPABASE_PUBLISHABLE_KEY=...
class AppConfig {
  static const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const supabasePublishableKey = String.fromEnvironment('SUPABASE_PUBLISHABLE_KEY');

  /// KVKK/18 yaş metin sürümü. Sunucudaki private.consent_version() ile aynı olmalı.
  static const consentVersion = 'kvkk-v1';

  /// Tarayıcı demosu (lib/demo/main_demo.dart) açık mı?
  static bool demoMode = false;

  static bool get isConfigured => supabaseUrl.isNotEmpty && supabasePublishableKey.isNotEmpty;
}
