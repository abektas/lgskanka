import { NextRequest, NextResponse } from "next/server";

const R2_PUBLIC_URL = "https://pub-782be99090dc4f8586da5bf5d073c4a5.r2.dev";

async function fetchJson(url: string): Promise<any> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
  return res.json();
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const imageMapRaw = await fetchJson(`${R2_PUBLIC_URL}/study_manifests/image_map.json`);
    const result = new Map<string, string>();
    for (const [localPath, info] of Object.entries(imageMapRaw as Record<string, any>)) {
      const name = localPath.split("/").pop();
      const webpPath = info?.webp_path;
      if (name && webpPath) {
        const r2Key = webpPath.split("/webp/")[1] || "";
        result.set(name, r2Key);
      }
    }
    
    // Test lookup for a known key
    const testKey = "MEB-LGS-2016-TURKCE-Q19.png";
    const found = result.get(testKey);
    
    return NextResponse.json({
      imageMapSize: result.size,
      testKey,
      found,
      firstFewKeys: Array.from(result.keys()).slice(0, 5)
    }, { headers: { "Cache-Control": "no-store" } });
  } catch (e) {
    return NextResponse.json(
      { error: "Test failed", detail: String(e) },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}