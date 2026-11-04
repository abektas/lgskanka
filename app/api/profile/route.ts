import { NextRequest, NextResponse } from "next/server";
import { dbSelectOne, dbUpsert, dbDelete } from "../../../lib/db";
import { authFromRequest } from "../../../lib/auth";

async function authorizeOwnProfile(request: NextRequest, profileId: string) {
  const auth = await authFromRequest(request);
  if (!auth) return NextResponse.json({ error: "Giriş yapılmamış." }, { status: 401 });
  if (auth.sub !== profileId) return NextResponse.json({ error: "Yetki yok." }, { status: 403 });
  return null;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const profileId = searchParams.get("profileId");

  if (!profileId) {
    return NextResponse.json({ error: "profileId required" }, { status: 400 });
  }
  const denied = await authorizeOwnProfile(request, profileId);
  if (denied) return denied;

  try {
    const row = await dbSelectOne("profiles", `id=eq.${encodeURIComponent(profileId)}`);
    if (!row) {
      return NextResponse.json({ error: "Profile not found" }, { status: 404 });
    }
    return NextResponse.json(row);
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }

  const { profileId, ...profileData } = body as Record<string, unknown>;

  if (!profileId || typeof profileId !== "string") {
    return NextResponse.json({ error: "profileId required" }, { status: 400 });
  }
  const denied = await authorizeOwnProfile(request, profileId);
  if (denied) return denied;

  try {
    const rows = await dbUpsert(
      "profiles",
      {
        id: profileId,
        user_id: profileId, // For now, profileId = user_id (no auth yet)
        name: profileData.name as string,
        gender: profileData.gender as "boy" | "girl",
        variant: (profileData.variant as number) ?? 0,
        registered_at: profileData.registeredAt as string,
      },
      "id"
    );
    return NextResponse.json({ success: true, data: rows });
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const profileId = searchParams.get("profileId");

  if (!profileId) {
    return NextResponse.json({ error: "profileId required" }, { status: 400 });
  }
  const denied = await authorizeOwnProfile(request, profileId);
  if (denied) return denied;

  try {
    await dbDelete("profiles", `id=eq.${encodeURIComponent(profileId)}`);
    return NextResponse.json({ success: true });
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}