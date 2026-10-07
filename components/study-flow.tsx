"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "./icons";
import { VoiceRecorder } from "./voice-recorder";
import { wrongReasons } from "../data/content";

type Attempt = { provider: string; status: number | null; error: string };

type AnalysisState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; text: string; provider: string; model: string }
  | { status: "error"; message: string; attempts?: Attempt[] };

type ApiQuestion = {
  id: string;
  subject: string;
  topic: string;
  stem: string;
  options: Record<string, string>;
  answer: string;
  solution: string;
  skill: string;
  difficulty: number;
  representation?: string;
  visual?: { publicPath: string; page: number } | null;
};

const MAX_PHOTO_BYTES = 6_000_000;

function buildStudentNarrative(written: string, spoken: string): string {
  const w = written.trim();
  const s = spoken.trim();
  if (s && w && s !== w) return `Yazılı anlatım: ${w}\nSesli anlatım: ${s}`;
  if (s) return `Sesli anlatım: ${s}`;
  if (w) return `Yazılı anlatım: ${w}`;
  return "Öğrenci ne yazılı ne sesli açıklama eklemedi";
}

function letterToIndex(letter: string): number {
  return letter.charCodeAt(0) - 65;
}

export function StudyFlow({ initialIndex = 0 }: { initialIndex?: number }) {
  const [questions, setQuestions] = useState<ApiQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(initialIndex);
  const [selected, setSelected] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const [reason, setReason] = useState("");
  const [explanation, setExplanation] = useState("");
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [photo, setPhoto] = useState<{ name: string; data: string } | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisState>({ status: "idle" });
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch("/api/questions", { cache: "no-store" });
        if (!res.ok) throw new Error(`API hatası: ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setQuestions(data.items ?? []);
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Soru bankası yüklenemedi");
          setLoading(false);
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const question = questions.length > 0 ? questions[index % questions.length] : null;
  const answered = checked && selected !== null;
  const isCorrect = answered && selected !== null && question !== null && selected === letterToIndex(question.answer);
  const isLoading = analysis.status === "loading";
  const hasVoice = voiceTranscript.trim().length > 0;

  function reset(nextIndex: number) {
    setIndex(nextIndex % Math.max(questions.length, 1));
    setSelected(null);
    setChecked(false);
    setReason("");
    setExplanation("");
    setVoiceTranscript("");
    setPhoto(null);
    setAnalysis({ status: "idle" });
    if (fileRef.current) fileRef.current.value = "";
  }

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
    if (!question) return;
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
            text: question.stem,
            options: question.options,
            skill: question.skill,
            difficulty: question.difficulty,
          },
          studentAnswer: selected === null ? "" : question.options[String.fromCharCode(65 + selected)] ?? "",
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
      setPhoto(null);
      setVoiceTranscript("");
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  if (loading) {
    return (
      <article className="card" aria-labelledby="soru-basligi">
        <div className="q-head">
          <span>Soru bankası yükleniyor…</span>
        </div>
        <div className="analysis" aria-live="polite">
          <div className="analysis-head">
            <span className="spinner" aria-hidden="true" />
            <b>Sorular yükleniyor…</b>
          </div>
        </div>
      </article>
    );
  }

  if (error) {
    return (
      <article className="card" aria-labelledby="soru-basligi">
        <div className="q-head">
          <span>Hata</span>
        </div>
        <div className="analysis is-error" role="alert">
          <div className="analysis-head">
            <span className="pill is-flame">⚠️ Soru bankası yüklenemedi</span>
          </div>
          <p className="analysis-body">{error}</p>
        </div>
      </article>
    );
  }

  if (!question) {
    return (
      <article className="card" aria-labelledby="soru-basligi">
        <div className="q-head">
          <span>Soru bankası</span>
        </div>
        <div className="analysis is-error" role="alert">
          <div className="analysis-head">
            <span className="pill is-flame">⚠️ Henüz soru yok</span>
          </div>
          <p className="analysis-body">
            Soru bankasında henüz yayınlanmış soru bulunmuyor. Soru altyapısı güncellendikten sonra burada görünecek.
          </p>
        </div>
      </article>
    );
  }

  const optionEntries = Object.entries(question.options);
  const correctIndex = letterToIndex(question.answer);

  return (
    <article className="card" aria-labelledby="soru-basligi">
      <div className="q-head">
        <span>
          {question.subject} · {question.topic}
        </span>
        <b>
          Soru {index + 1} / {questions.length}
        </b>
      </div>
      <div
        className="q-progress"
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={questions.length}
        aria-valuenow={index + 1}
        aria-label="Soru ilerlemesi"
      >
        <i style={{ width: `${((index + 1) / questions.length) * 100}%` }} />
      </div>

      <h2 className="q-text" id="soru-basligi">
        {question.stem}
      </h2>
      <p className="q-skill">
        Kazanım: {question.skill} · Zorluk {question.difficulty}/3
      </p>

      <div className="options-grid" role="group" aria-label="Cevap seçenekleri">
        {optionEntries.map(([letter, option], i) => {
          const classes = ["option"];
          if (selected === i) classes.push("is-selected");
          if (answered && i === correctIndex) classes.push("is-correct");
          if (answered && selected === i && i !== correctIndex) classes.push("is-wrong");
          return (
            <button
              type="button"
              key={letter}
              className={classes.join(" ")}
              aria-pressed={selected === i}
              onClick={() => {
                setSelected(i);
                setChecked(false);
                setAnalysis({ status: "idle" });
              }}
            >
              <span className="option-key" aria-hidden="true">
                {letter}
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
          <p>{question.solution} Sonraki soruya geçebilirsin ya da koçtan pekiştirme isteyebilirsin.</p>
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
            hangisi senin durumana daha yakın?
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
                <span className="spinner" aria-hidden="true" /> Koç inceliyor…
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
              <strong>Doğru cevap:</strong> {question.options[question.answer]} — {question.solution}
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
