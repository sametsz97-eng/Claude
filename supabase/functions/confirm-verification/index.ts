// confirm-verification
// İstemciden gelen doğrulama token'ını sağlayıcıya doğrulatır ve sonucu
// service_role ile veritabanına yazar. verified=true yazabilen TEK yer burasıdır.
// Fotoğraf bu fonksiyona hiç gelmez ve hiçbir yerde saklanmaz.
import { createClient } from "jsr:@supabase/supabase-js@2";
import { MockProvider } from "./providers/mock.ts";
import { YotiProvider } from "./providers/yoti.ts";
import { FaceTecProvider } from "./providers/facetec.ts";
import type { Gender, VerificationProvider } from "./providers/types.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function providerFromEnv(): VerificationProvider {
  // Bilerek varsayılan yok: üretimde yanlışlıkla mock açık kalmasın.
  switch (Deno.env.get("VERIFICATION_MODE")) {
    case "yoti":
      return new YotiProvider();
    case "facetec":
      return new FaceTecProvider();
    case "mock":
      return new MockProvider();
    default:
      throw new Error("VERIFICATION_MODE ayarlı değil veya geçersiz");
  }
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405);

  const url = Deno.env.get("SUPABASE_URL")!;
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  const authHeader = req.headers.get("Authorization") ?? "";
  const userClient = createClient(url, anonKey, {
    global: { headers: { Authorization: authHeader } },
  });
  const { data: userData, error: userErr } = await userClient.auth.getUser();
  if (userErr || !userData.user) return json({ error: "unauthorized" }, 401);

  let body: { provider_token?: unknown; claimed_gender?: unknown };
  try {
    body = await req.json();
  } catch {
    return json({ error: "invalid_body" }, 400);
  }
  const token = typeof body.provider_token === "string" ? body.provider_token : "";
  const claimed = body.claimed_gender;
  if (!token || token.length > 2048 || (claimed !== "female" && claimed !== "male")) {
    return json({ error: "invalid_body" }, 400);
  }

  let provider: VerificationProvider;
  let result;
  try {
    provider = providerFromEnv();
    result = await provider.verify(token, claimed as Gender);
  } catch (e) {
    console.error("verification provider error", e);
    return json({ error: "provider_error" }, 502);
  }

  const admin = createClient(url, serviceKey, { auth: { persistSession: false } });
  const { data, error } = await admin.rpc("admin_mark_verified", {
    p_user: userData.user.id,
    p_provider: provider.name,
    p_success: result.success,
    p_detected_gender: result.detectedGender,
  });
  if (error) {
    const code = error.message.includes("too_many_attempts") ? 429 : 400;
    return json({ error: error.message }, code);
  }
  return json({ verified: data === true });
});
