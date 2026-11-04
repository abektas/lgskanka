import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Self-service reset is disabled because username-only recovery cannot verify
 * account ownership. Keep the endpoint inert for older clients.
 */
export async function POST() {
  return NextResponse.json(
    { error: "Güvenlik nedeniyle şifreyi buradan sıfırlayamazsın. Öğretmeninden yardım iste." },
    { status: 410 }
  );
}
