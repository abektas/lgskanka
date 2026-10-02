import { NextRequest, NextResponse } from "next/server";
import { errorCodePromptLine } from "../../../data/content";
import { AllProvidersFailed, ProviderError, runAI } from "./providers";

const MAX_PROMPT_CHARS = Number(process.env.AI_MAX_PROMPT_CHARS) || 4000;
const MAX_IMAGE_BYTES = Number(process.env.AI_MAX_IMAGE_BYTES) || 8_000_000;

function buildPrompt(body: {
  prompt: string;
  question: unknown;
  studentAnswer: string;
  reason: string;
  voiceTranscript: string;
}): string {
  return `Sen bir ortaokul/LGS öğrenme koçusun. Öğrenciyi yargılama ve cevabı sadece söylemek yerine hatanın kaynağını teşhis et. Seviye 3: 7. sınıf bilgisi + 8. sınıfa geçiş + LGS becerileri.

SORU:
${JSON.stringify(body.question)}

ÖĞRENCİ CEVABI: ${body.studentAnswer}
ÖĞRENCİNİN İŞARETLEDİĞİ ZORLUK: ${body.reason}
SESLE ANLATIM: ${body.voiceTranscript}

${body.prompt}

Yanıtı Türkçe ve kısa bölümler halinde ver: 1) Teşhis 2) Neden 3) Mini konu tekrarı 4) Öğrencinin şimdi yapacağı 3 adım 5) Benzer 2 alıştırma. ${errorCodePromptLine} Eğer kanıt yetersizse bunu belirt.`;
}

export async function POST(req: NextRequest) {
  let raw: unknown;
  try {
    raw = await req.json();
  } catch {
    return NextResponse.json({ error: "Geçersiz JSON gövdesi." }, { status: 400 });
  }

  const body = (raw ?? {}) as Record<string, unknown>;
  const asText = (value: unknown): string => (typeof value === "string" ? value : "");

  const clientPrompt = asText(body.prompt).slice(0, MAX_PROMPT_CHARS);
  const imageData = typeof body.imageData === "string" && body.imageData.length > 0 ? body.imageData : null;

  if (imageData && imageData.length > MAX_IMAGE_BYTES) {
    return NextResponse.json(
      { error: `Görsel çok büyük (${imageData.length} karakter > ${MAX_IMAGE_BYTES}). Lütfen daha küçük bir fotoğraf yükleyin.` },
      { status: 413 },
    );
  }

  const prompt = buildPrompt({
    prompt: clientPrompt,
    question: body.question ?? {},
    studentAnswer: asText(body.studentAnswer),
    reason: asText(body.reason),
    voiceTranscript: asText(body.voiceTranscript),
  });

  try {
    const result = await runAI({ prompt, imageData });
    return NextResponse.json({ answer: result.text, provider: result.provider, model: result.model });
  } catch (error) {
    if (error instanceof AllProvidersFailed) {
      return NextResponse.json({ error: error.message, attempts: error.attempts }, { status: error.status });
    }
    if (error instanceof ProviderError) {
      return NextResponse.json({ error: error.message }, { status: error.status || 500 });
    }
    const message = error instanceof Error ? error.message : "Beklenmeyen hata";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
