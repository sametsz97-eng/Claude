import type { Gender, ProviderResult, VerificationProvider } from "./types.ts";

/**
 * Yoti (Age/Face) entegrasyonu için yer tutucu.
 * Uygulanacaklar: YOTI_SDK_ID + YOTI_PRIVATE_KEY ile oturum sonucunu sorgula,
 * liveness ve cinsiyet sonucunu ProviderResult'a çevir.
 */
export class YotiProvider implements VerificationProvider {
  readonly name = "yoti";

  verify(_token: string, _claimedGender: Gender): Promise<ProviderResult> {
    throw new Error("Yoti entegrasyonu henüz yapılmadı");
  }
}
