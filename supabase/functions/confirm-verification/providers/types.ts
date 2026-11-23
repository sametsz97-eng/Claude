export type Gender = "female" | "male";

export interface ProviderResult {
  /** Canlılık (liveness) kontrolü geçti mi? */
  success: boolean;
  /** Sağlayıcının tespit ettiği cinsiyet. Beyanla uyuşmazsa doğrulama başarısız sayılır. */
  detectedGender: Gender | null;
}

/**
 * Sunucu tarafı doğrulama sağlayıcısı.
 * İstemci selfie'yi doğrudan sağlayıcıya gönderir ve bir oturum token'ı alır;
 * biz sadece bu token'ı sağlayıcıya sorarız. Fotoğraf bizim sunucumuza GELMEZ.
 */
export interface VerificationProvider {
  readonly name: string;
  verify(token: string, claimedGender: Gender): Promise<ProviderResult>;
}
