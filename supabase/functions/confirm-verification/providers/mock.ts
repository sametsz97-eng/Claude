import type { Gender, ProviderResult, VerificationProvider } from "./types.ts";

/**
 * Geliştirme için sahte sağlayıcı. "mock-ok:" ile başlayan her token'ı kabul eder
 * ve beyan edilen cinsiyeti doğru sayar. ÜRETİMDE KULLANMAYIN.
 */
export class MockProvider implements VerificationProvider {
  readonly name = "mock";

  verify(token: string, claimedGender: Gender): Promise<ProviderResult> {
    const ok = token.startsWith("mock-ok:");
    return Promise.resolve({ success: ok, detectedGender: ok ? claimedGender : null });
  }
}
