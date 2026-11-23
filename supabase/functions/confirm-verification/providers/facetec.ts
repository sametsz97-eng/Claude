import type { Gender, ProviderResult, VerificationProvider } from "./types.ts";

/**
 * FaceTec entegrasyonu için yer tutucu.
 * Uygulanacaklar: FaceTec Server SDK'ya session sonucu sorgusu, liveness kontrolü.
 * Not: FaceTec cinsiyet tahmini vermez; ek bir sınıflandırıcı gerekir.
 */
export class FaceTecProvider implements VerificationProvider {
  readonly name = "facetec";

  verify(_token: string, _claimedGender: Gender): Promise<ProviderResult> {
    throw new Error("FaceTec entegrasyonu henüz yapılmadı");
  }
}
