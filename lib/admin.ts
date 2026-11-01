/**
 * Öğretmen (admin) yetki kontrolü.
 * Admin API'leri `x-admin-key` başlığını ADMIN_RESET_SECRET ile karşılaştırır.
 * Bu anahtar sadece öğretmende bulunur; öğrencilere asla gösterilmez.
 */
export function isAdminRequest(req: Request): boolean {
  const key = req.headers.get("x-admin-key") || "";
  const expected = process.env.ADMIN_RESET_SECRET || "";
  return expected.length > 0 && key === expected;
}

export const ADMIN_UNAUTHORIZED = {
  error: "Yetkisiz. Öğretmen anahtarı gerekli.",
} as const;