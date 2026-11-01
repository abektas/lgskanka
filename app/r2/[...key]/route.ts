import { NextRequest } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";

/**
 * R2 görsel sunucusu — yalnızca .webp soru görselleri herkese açıktır.
 * Manifestolar (image_map.json, all_questions.json) cevap anahtarı
 * içerdiğinden ASLA buradan sunulmaz; sunucu tarafında R2 binding
 * üzerinden okunur (Answer key server-side kalır).
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ key: string[] }> }
) {
  const { key } = await params;
  const objectKey = key.map(decodeURIComponent).join("/");

  if (!objectKey.endsWith(".webp") || objectKey.includes("..")) {
    return new Response("Not Found", { status: 404 });
  }

  const { env } = await getCloudflareContext();
  const bucket = (
    env as unknown as {
      R2: {
        get(key: string): Promise<{
          body: ReadableStream;
          httpEtag: string;
          writeHttpMetadata(headers: Headers): void;
        } | null>;
      };
    }
  ).R2;

  const object = await bucket.get(objectKey);
  if (!object) {
    return new Response("Not Found", { status: 404 });
  }

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("etag", object.httpEtag);
  headers.set("cache-control", "public, max-age=31536000, immutable");
  return new Response(object.body, { headers });
}