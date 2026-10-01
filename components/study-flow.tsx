"use client";

import { useRef, useState } from "react";
import { Icon } from "./icons";
import { VoiceRecorder } from "./voice-recorder";
import { questionBank, wrongReasons } from "../data/content";

type Attempt = { provider: string; status: number | null; error: string };

type AnalysisState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; text: string; provider: string; model: string }
  | { status: "error"; message: string; attempts?: Attempt[] };

const MAX_PHOTO_BYTES = 6_000_000;

/**
 * AI istemine giden anlatım metnini kurar.
 *
 * Yazılı açıklama ve sesli anlatım ayrı ayrı tutulur (§7). Sesli kayıt varsa o
 * önceliklidir; ikisi de varsa ikisi birlikte gönderilir. Kaydın kendisi değil,
 * yalnızca türetilmiş metin gider (§49 kalıcı ses saklama yok).
 */
function buildStudentNarrative(written: string, spoken: string): string {
  const w = written.trim();
  const s = spoken.trim();
  if (s && w && s !== w) return `Yazılı anlatım: ${w}\nSesli anlatım: ${s}`;
  if (s) return `Sesli anlatım: ${s}`;
  if (w) return `Yazılı anlatım: ${w}`;
  return "Öğrenci ne yazılı ne sesli açıklama eklemedi";
}

/**
 * Soru akışı: cevap → öz değerlendirme (neden?) → AI koçtan teşhis.
 *
 * Yanlış cevap sonrası üç kanıt toplanır (§7):
 *   1. Anket        — öğrencinin hatanın nedenini seçmesi
 *   2. Kendi cümleleri — yazılı açıklama
 *   3. Sesli anlat   — `VoiceRecorder` (§22, en fazla 60 sn)
 *   4. Çözüm fotoğrafı — yalnızca analiz için
 *
 * Teşhis isteği sunucudaki `/api/ai` ucuna gider; sağlayıcı seçimi ve
 * anahtar yönetimi orada yapılır.
 */
export function StudyFlow({ initialIndex = 0 }: { initialIndex?: number }) {
  const [index, setIndex] = useState(initialIndex);
  const [selected, setSelected] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const [reason, setReason] = useState("");
  const [explanation, setExplanation] = useState("");
  /** Sesli anlatımın metni; yazılı açıklamadan ayrı tutulur (§7, §22). */
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [photo, setPhoto] = useState<{ name: string; data: string } | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisState>({ status: "idle" });
  const fileRef = useRef<HTMLInputElement>(null);

  const question = questionBank[index % questionBank.length];
  const answered = checked && selected !== null;
  const isCorrect = answered && selected === question.correct;
  const isLoading = analysis.status === "loading";
  const hasVoice = voiceTranscript.trim().length > 0;

  function reset(nextIndex: number) {
    setIndex(nextIndex % questionBank.length);
    setSelected(null);
    setChecked(false);
    setReason("");
    setExplanation("");
    setVoiceTranscript("");
    setPhoto(null);
    setAnalysis({ status: "idle" });
    if (fileRef.current) fileRef.current.value = "";
  }

  /** `Kullan` → transkripti alır ve yazılı alanı bozmadan saklar. */
  function onVoiceUse(transcript: string) {
    setVoiceTranscript(transcript);
    setAnalysis({ status: "idle" });
  }

  function onPhoto(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_PHOTO_BYTES) {
      setAnalysis({ status: "error", message: "Fotoğraf çok büyük (en fazla 6 MB). Daha küçük bir fotoğraf seç." });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        setPhoto({ name: file.name, data: reader.result });
        setAnalysis({ status: "idle" });
      }
    };
    reader.readAsDataURL(file);
  }

  async function askCoach() {
    setAnalysis({ status: "loading" });
    try {
      const response = await fetch("/api/ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: buildStudentNarrative(explanation, voiceTranscript),
          question: {
            subject: question.subject,
            topic: question.topic,
            text: question.text,
            options: question.options,
            skill: question.skill,
            difficulty: question.difficulty,
          },
          studentAnswer: selected === null ? "" : question.options[selected],
          reason,
          voiceTranscript: voiceTranscript || explanation,
          imageData: photo?.data ?? null,
        }),
      });

      const data: {
        answer?: string;
        provider?: string;
        model?: string;
        error?: string;
        attempts?: Attempt[];
      } = await response.json();

      if (!response.ok || !data.answer) {
        setAnalysis({
          status: "error",
          message: data.error ?? "AI şu an yanıt veremedi. Birazdan yeniden dene.",
          attempts: data.attempts,
        });
        return;
      }

      setAnalysis({
        status: "done",
        text: data.answer,
        provider: data.provider ?? "ai",
        model: data.model ?? "",
      });
    } catch {
      setAnalysis({
        status: "error",
        message: "Bağlantı kurulamadı. İnternetini kontrol edip yeniden dene.",
      });
    } finally {
      // Raw solution photos and derived voice transcripts are temporary analysis inputs.
      setPhoto(null);
      setVoiceTranscript("");
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <article className="card" aria-labelledby="soru-basligi">
      <div className="q-head">
        <span>
          {question.subject} · {question.topic}
        </span>
        <b>
          Soru {index + 1} / {questionBank.length}
        </b>
      </div>
      <div
        className="q-progress"
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={questionBank.length}
        aria-valuenow={index + 1}
        aria-label="Soru ilerlemesi"
      >
        <i style={{ width: `${((index + 1) / questionBank.length) * 100}%` }} />
      </div>

      <h2 className="q-text" id="soru-basligi">
        {question.text}
      </h2>
      <p className="q-skill">
        Kazanım: {question.skill} · Zorluk {question.difficulty}/3
      </p>

      <div className="options-grid" role="group" aria-label="Cevap seçenekleri">
        {question.options.map((option, i) => {
          const classes = ["option"];
          if (selected === i) classes.push("is-selected");
          if (answered && i === question.correct) classes.push("is-correct");
          if (answered && selected === i && i !== question.correct) classes.push("is-wrong");
          return (
            <button
              type="button"
              key={option}
              className={classes.join(" ")}
              aria-pressed={selected === i}
              onClick={() => {
                setSelected(i);
                setChecked(false);
                setAnalysis({ status: "idle" });
              }}
            >
              <span className="option-key" aria-hidden="true">
                {String.fromCharCode(65 + i)}
              </span>
              {option}
            </button>
          );
        })}
      </div>

      {!answered && (
        <button
          type="button"
          className="btn btn-primary btn-block"
          disabled={selected === null}
          onClick={() => setChecked(true)}
        >
          {selected === null ? "Bir seçenek işaretle" : "Cevabımı gönder"}
        </button>
      )}

      {answered && isCorrect && (
        <div className="result is-ok">
          <b>✓ Doğru cevap!</b>
          <p>{question.explain} Sonraki soruya geçebilirsin ya da koçtan pekiştirme isteyebilirsin.</p>
          <button type="button" className="btn btn-primary btn-block" onClick={() => reset(index + 1)}>
            Sonraki soru <Icon name="arrow" size={18} />
          </button>
        </div>
      )}

      {answered && !isCorrect && (
        <div className="result is-bad">
          <b>Bu soruda hata var — birlikte bulalım.</b>
          <p>
            Doğrudan &ldquo;konuyu bilmiyorsun&rdquo; demiyoruz. Önce ilk hata noktasını bulalım:
            hangisi senin durumuna daha yakın?
          </p>

          <div className="reason-grid" role="group" aria-label="Hatanın nedeni">
            {wrongReasons.map((option) => (
              <button
                type="button"
                key={option}
                className={`chip${reason === option ? " is-active" : ""}`}
                aria-pressed={reason === option}
                onClick={() => setReason(option)}
              >
                {option}
              </button>
            ))}
          </div>

          <label className="field">
            <span className="field-label">Nasıl düşündün? (kendi cümlelerinle kısaca anlat)</span>
            <textarea
              rows={3}
              value={explanation}
              onChange={(event) => setExplanation(event.target.value)}
              placeholder="Örn. Üsleri çarpmam gerektiğini düşündüm, sonra emin olamadım."
            />
          </label>

          {/* §22: sesli anlatım. Yazılı alan yerine geçmez, ona eklenir. */}
          <VoiceRecorder disabled={isLoading} onUse={onVoiceUse} />

          {hasVoice && (
            <p className="photo-note">
              <Icon name="mic" size={15} /> Sesli anlatım eklendi
              <button
                type="button"
                className="link-btn"
                onClick={() => setVoiceTranscript("")}
              >
                kaldır
              </button>
            </p>
          )}

          <div className="evidence-row">
            <label className="btn-evidence">
              <Icon name="camera" size={17} />
              {photo ? "Fotoğrafı değiştir" : "Çözüm fotoğrafı ekle"}
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="sr-only"
                onChange={onPhoto}
              />
            </label>
            <span className="pill is-gok">
              <Icon name="shield" size={15} /> Analiz bitince dosya silinir
            </span>
          </div>

          <p className="privacy-notice" role="note">
            🔒 <strong>Gizlilik bilgilendirmesi:</strong> Gönderdiğin ses kaydı veya çözüm
            fotoğrafı yalnızca bu sorudaki hatanı analiz etmek için kullanılır. Analiz
            tamamlandıktan sonra dosya kalıcı olarak silinir ve öğrenci profilinde saklanmaz.
          </p>

          {photo && (
            <p className="photo-note">
              📷 {photo.name} eklendi · {Math.round(photo.data.length / 1365)} KB
              <button
                type="button"
                className="link-btn"
                onClick={() => {
                  setPhoto(null);
                  if (fileRef.current) fileRef.current.value = "";
                }}
              >
                kaldır
              </button>
            </p>
          )}

          <button type="button" className="btn btn-primary btn-block" onClick={askCoach} disabled={isLoading}>
            {isLoading ? (
              <>
                <span className="spinner" aria-hidden="true" /> Koç inceliyor...
              </>
            ) : (
              <>
                🤖 AI koçtan teşhis al <Icon name="arrow" size={18} />
              </>
            )}
          </button>

          <details className="answer-peek">
            <summary>Doğru cevabı ve kısa çözümü gör</summary>
            <p>
              <strong>Doğru cevap:</strong> {question.options[question.correct]} — {question.explain}
            </p>
          </details>

          <button type="button" className="btn btn-ghost btn-block" onClick={() => reset(index + 1)}>
            Sonraki soru
          </button>
        </div>
      )}

      {analysis.status === "loading" && (
        <div className="analysis" aria-live="polite">
          <div className="analysis-head">
            <span className="spinner" aria-hidden="true" />
            <b>Koç cevabını inceliyor…</b>
          </div>
          <p className="analysis-body">
            Yanıtını, seçtiğin nedeni ve eklediğin kanıtları birlikte değerlendiriyor. Genelde 5–15
            saniye sürer.
          </p>
        </div>
      )}

      {analysis.status === "done" && (
        <div className="analysis" aria-live="polite">
          <div className="analysis-head">
            <span className="pill is-mint">🤖 Koç teşhisi</span>
          </div>
          <p className="analysis-body">{analysis.text}</p>
          <div className="analysis-meta">
            <span>Yanıtlayan: {analysis.provider}</span>
            <span>Model: {analysis.model}</span>
            <span>Seçtiğin neden: {reason || "belirtilmedi"}</span>
          </div>
          {(hasVoice || photo) && (
            <p className="privacy-notice is-done">
              ✓ Analiz tamamlandı. {hasVoice ? "Ses kaydın" : "Fotoğrafın"} analiz için kullanıldı
              ve kalıcı olarak silindi.
            </p>
          )}
        </div>
      )}

      {analysis.status === "error" && (
        <div className="analysis is-error" role="alert">
          <div className="analysis-head">
            <span className="pill is-flame">⚠️ Koç şu an yanıt veremedi</span>
          </div>
          <p className="analysis-body">{analysis.message}</p>
          {analysis.attempts && analysis.attempts.length > 0 && (
            <ul className="attempts-list">
              {analysis.attempts.map((attempt) => (
                <li key={attempt.provider}>
                  {attempt.provider}: {attempt.error}
                  {attempt.status ? ` (HTTP ${attempt.status})` : ""}
                </li>
              ))}
            </ul>
          )}
          <p className="analysis-body attempts-hint">
            Sağlayıcı ayarlarını <code>.env.local</code> dosyasından değiştirebilirsin
            (<code>GEMINI_API_KEY</code>).
          </p>
        </div>
      )}
    </article>
  );
}
