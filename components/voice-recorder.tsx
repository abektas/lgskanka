"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "./icons";

/**
 * Sesli anlatım kaydedici — plan §22 ve §49.
 *
 * §22 sözleşmesi (kelimesi kelimesine uygulanmıştır):
 *   Kontroller : Başlat · Duraklat · Devam Et · Durdur · Tekrar Kaydet · Dinle · Kullan
 *   Maksimum   : 60 saniye
 *   Teknik     : `MediaRecorder` gerçek ses kaydını yönetir.
 *                `SpeechRecognition` YALNIZCA transkripsiyon içindir; sessizlik veya
 *                nefes nedeniyle durduğunda gerçek kayıt sonlanmaz.
 *
 * Gizlilik (§23/§59): kayıt yalnızca bu sorudaki hatayı analiz etmek için tutulur,
 * `Kullan` dediğinde üst bileşene transkript verilir ve ham ses hafızadan düşer.
 * Sunucuya gönderilen yalnızca türetilmiş metindir; ses dosyası hiçbir yere yazılmaz.
 */

const MAX_SECONDS = 60;

/** Tarayıcı tipi: MediaRecorder/Blob yalnızca istemcide vardır. */
type RecorderState = "idle" | "requesting" | "recording" | "paused" | "ready" | "error";

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

function getSpeechRecognition(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** 43 → "00:43" */
function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = String(Math.floor(safe / 60)).padStart(2, "0");
  const seconds = String(safe % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function VoiceRecorder({
  disabled = false,
  onUse,
}: {
  /** AI isteği sürerken veya kayıt varken butonlar kilitlenir. */
  disabled?: boolean;
  /** `Kullan` ile çağrılır: taşınacak transkript (yazılı açıklama da olabilir). */
  onUse: (transcript: string) => void;
}) {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const timerRef = useRef<number | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  /** Kayıt durmuşken gerçekten bir dosya oluştu mu? (Kullan/Dinle için) */
  const hasRecording = previewUrl !== null;

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  /** Kayıt yolunu ve önizleme nesnesini serbest bırakır (bellek sızıntısı olmaması için). */
  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
  }, []);

  const revokePreview = useCallback(() => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setPreviewUrl(null);
  }, []);

  /** Ham sesi ve yolunu tamamen siler (kullanıcı vazgeçti / yeni kayıt). */
  const discardRecording = useCallback(() => {
    chunksRef.current = [];
    revokePreview();
  }, [revokePreview]);

  const stopRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    // `SpeechRecognition` sessizlikte kendiliğinden durabilir; bu GERÇEK kaydı bitirmez.
    try {
      recognition?.stop();
    } catch {
      /* zaten durmuş olabilir */
    }
  }, []);

  const resetAll = useCallback(() => {
    clearTimer();
    stopRecognition();
    releaseStream();
    discardRecording();
    setState("idle");
    setSeconds(0);
    setTranscript("");
    setError(null);
  }, [clearTimer, discardRecording, releaseStream, stopRecognition]);

  // Bileşen kalkarken mikrofonu kapat ve önizlemeyi iptal et.
  useEffect(() => {
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      stopRecognition();
      releaseStream();
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    };
  }, [releaseStream, stopRecognition]);

  const stopRecording = useCallback(
    (next: "ready" | "idle") => {
      clearTimer();
      // Transkripsiyonu durdur; kayıt zaten kapanıyor.
      stopRecognition();
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.stop();
      }
      releaseStream();
      setState(next);
    },
    [clearTimer, releaseStream, stopRecognition],
  );

  const startRecording = useCallback(async () => {
    setError(null);

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setState("error");
      setError("Bu tarayıcı ses kaydını desteklemiyor. Yazılı açıklama yazabilirsin.");
      return;
    }

    setState("requesting");

    let stream: MediaStream;
    try {
      // Mikrofon izni — kullanıcı tarayıcıdan onaylar.
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (cause) {
      setState("error");
      const name = cause instanceof Error ? cause.name : "";
      setError(
        name === "NotAllowedError"
          ? "Mikrofon izni verilmedi. Tarayıcı adres çubuğundaki izin düğmesinden açabilirsin."
          : "Mikrofona erişilemedi. Cihazında mikrofon bağlı mı?",
      );
      return;
    }

    streamRef.current = stream;
    chunksRef.current = [];
    setSeconds(0);
    setTranscript("");

    // Eski kayıt varsa önce onu serbest bırak.
    revokePreview();

    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(stream);
    } catch {
      releaseStream();
      setState("error");
      setError("Ses kaydı başlatılamadı. Tarayıcı bu biçimi desteklemiyor.");
      return;
    }
    recorderRef.current = recorder;

    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      chunksRef.current = [];
      if (blob.size > 0) {
        const url = URL.createObjectURL(blob);
        previewUrlRef.current = url;
        setPreviewUrl(url);
        setState("ready");
      } else {
        // Kayıt boş çıktı: kullanıcıyı bilgilendir, takılma.
        setState("error");
        setError("Kayıt boş çıktı. Biraz daha uzun konuşmayı dene.");
      }
    };

    recorder.start();
    setState("recording");

    // 60 saniye üst sınırı (plan §22).
    timerRef.current = window.setInterval(() => {
      setSeconds((value) => {
        const next = value + 1;
        if (next >= MAX_SECONDS) {
          stopRecording("ready");
        }
        return next;
      });
    }, 1000);

    // Transkripsiyon paralel çalışır; HATA VEYA BİTİŞ GERÇEK KAYDI ETKİLEMEZ.
    const Recognition = getSpeechRecognition();
    if (Recognition) {
      try {
        const recognition = new Recognition();
        recognition.lang = "tr-TR";
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.onresult = (event) => {
          let combined = "";
          for (let i = event.resultIndex; i < event.results.length; i += 1) {
            combined += event.results[i][0]?.transcript ?? "";
          }
          if (combined.trim()) setTranscript(combined.trim());
        };
        // Sessizlikte de `onend` tetiklenir; kaydı burada ASLA durdurmuyoruz.
        recognition.onend = () => {
          recognitionRef.current = null;
        };
        recognition.onerror = () => {
          // Transkripsiyon yoksa yazılı açıklama yeterli; sessiz geç.
          recognitionRef.current = null;
        };
        recognitionRef.current = recognition;
        recognition.start();
      } catch {
        recognitionRef.current = null;
      }
    }
  }, [releaseStream, revokePreview, stopRecording]);

  const pauseRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state === "recording") {
      recorder.pause();
      clearTimer();
      setState("paused");
    }
  }, [clearTimer]);

  const resumeRecording = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "paused") return;

    // 60 saniye sınırı kaldığı yerden devam eder.
    timerRef.current = window.setInterval(() => {
      setSeconds((value) => {
        const next = value + 1;
        if (next >= MAX_SECONDS) {
          stopRecording("ready");
        }
        return next;
      });
    }, 1000);

    recorder.resume();
    setState("recording");
  }, [stopRecording]);

  const handleRerecord = useCallback(() => {
    resetAll();
  }, [resetAll]);

  const handleUse = useCallback(() => {
    const finalText = transcript.trim();
    // Ham ses artık gerekli değil: kaydı ve önizlemeyi hemen serbest bırak.
    discardRecording();
    stopRecognition();
    setState("idle");
    setSeconds(0);
    onUse(finalText);
  }, [discardRecording, onUse, stopRecognition, transcript]);

  const isBusy = state === "requesting" || state === "recording" || state === "paused";
  const isLocked = disabled || isBusy;
  const remaining = MAX_SECONDS - seconds;

  return (
    <div className="voice-box">
      <div className="voice-head">
        <span className="voice-title">
          <Icon name="mic" size={17} />
          Çözümü sesli anlat
        </span>
        {(state === "recording" || state === "paused") && (
          <span className="pill is-flame" role="timer" aria-live="off">
            <span className="voice-dot" aria-hidden="true" />
            {formatClock(seconds)} / 01:00
          </span>
        )}
      </div>

      <p className="voice-hint">
        {state === "recording"
          ? `Anlatıyorsun — kalan ${remaining} saniye. Bitince Durdur'a bas.`
          : state === "paused"
            ? "Kayıt duraklatıldı. Devam Et ya da Durdur."
            : "En fazla 60 saniye. Ses yalnızca bu sorudaki hatanı analiz etmek için kullanılır."}
      </p>

      <div className="voice-actions" role="group" aria-label="Ses kaydı kontrolleri">
        {state === "idle" && (
          <button
            type="button"
            className="btn-evidence is-voice"
            onClick={startRecording}
            disabled={disabled}
            aria-label="Ses kaydını başlat"
          >
            <Icon name="mic" size={17} />
            Başlat
          </button>
        )}

        {state === "requesting" && (
          <button type="button" className="btn-evidence is-voice" disabled aria-label="Mikrofon izni bekleniyor">
            <span className="spinner" aria-hidden="true" />
            İzin bekleniyor...
          </button>
        )}

        {state === "recording" && (
          <>
            <button
              type="button"
              className="btn-evidence is-voice"
              onClick={pauseRecording}
              aria-label="Kaydı duraklat"
            >
              <Icon name="play" size={17} />
              Duraklat
            </button>
            <button
              type="button"
              className="btn-evidence is-voice"
              onClick={() => stopRecording("ready")}
              aria-label="Kaydı durdur"
            >
              <Icon name="check" size={17} />
              Durdur
            </button>
          </>
        )}

        {state === "paused" && (
          <>
            <button
              type="button"
              className="btn-evidence is-voice"
              onClick={resumeRecording}
              aria-label="Kayda devam et"
            >
              <Icon name="play" size={17} />
              Devam Et
            </button>
            <button
              type="button"
              className="btn-evidence is-voice"
              onClick={() => stopRecording("ready")}
              aria-label="Kaydı durdur"
            >
              <Icon name="check" size={17} />
              Durdur
            </button>
          </>
        )}

        {state === "ready" && hasRecording && (
          <>
            {previewUrl && (
              <audio className="voice-audio" controls src={previewUrl} aria-label="Kaydını dinle" />
            )}
            <button
              type="button"
              className="btn-evidence is-voice"
              onClick={handleRerecord}
              aria-label="Kaydı sil ve yeniden kaydet"
            >
              <Icon name="bolt" size={17} />
              Tekrar Kaydet
            </button>
            <button
              type="button"
              className="btn-evidence is-voice is-primary"
              onClick={handleUse}
              aria-label="Kaydı analize ekle"
            >
              <Icon name="check" size={17} />
              Kullan
            </button>
          </>
        )}
      </div>

      {state === "ready" && (
        <p className="voice-note">
          {transcript
            ? `Algılanan anlatım: “${transcript}”`
            : "Yazılı transkript oluşmadı; Kullan dersen bu kayıt boş metin olarak işlenecek."}
        </p>
      )}

      {state === "error" && error && (
        <p className="voice-error" role="alert">
          <span aria-hidden="true">⚠️</span> {error}
        </p>
      )}

      <p className="voice-privacy">
        <Icon name="shield" size={14} />
        Kayıt kalıcı olarak saklanmaz; <strong>Kullan</strong> dediğinde silinir, profile yazılmaz.
      </p>
    </div>
  );
}
