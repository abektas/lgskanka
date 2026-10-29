"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { subjects, errorTypes } from "../../data/content";
import { learner } from "../../data/nav";
import { ERROR_REASON_OPTIONS, saveAnswerRecord } from "../../lib/error-reason";
import {
  computeCycleState,
  cycleSummary,
  ENROLLMENT_CHANGED_EVENT,
  type CycleState,
} from "../../lib/cycle";

const ERROR_REASON_OPTIONS_LOCAL = [
  { id: "anlamadim", label: "Soruyu anlamadım", code: "H3" },
  { id: "yonetim", label: "Yöntemi bilmiyordum", code: "H2" },
  { id: "islem", label: "İşlem hatası yaptım", code: "H4" },
  { id: "eksik", label: "Konuda eksiğim var", code: "H1" },
  { id: "bilmiyorum", label: "Konuyu bilmiyorum", code: null },
];
import { computeUnitMasteries, type UnitMastery } from "../../lib/mastery";

interface DailySummaryProps {
  questions: StudyQuestion[];
  cycle: CycleState | null;
}

function DailySummary({ questions, cycle }: DailySummaryProps) {
  const records = questions.map((q) => {
    const rec = JSON.parse(localStorage.getItem("lgs_answer_log") || "[]")
      .find((r: any) => r.questionId === q.id);
    return { question: q, ...rec };
  }).filter((r: any) => r);

  const total = records.length;
  const correct = records.filter((r: any) => r.correct).length;
  const wrong = total - correct;
  const correctPct = total ? Math.round((correct / total) * 100) : 0;

  // Ders bazında
  const bySubject: Record<string, { total: number; correct: number }> = {};
  for (const r of records) {
    if (!bySubject[r.subject]) bySubject[r.subject] = { total: 0, correct: 0 };
    bySubject[r.subject].total++;
    if (r.correct) bySubject[r.subject].correct++;
  }

  // H türü bazında
  const byH: Record<string, number> = {};
  for (const r of records) {
    if (r.errorReasonCode) {
      byH[r.errorReasonCode] = (byH[r.errorReasonCode] || 0) + 1;
    }
  }

  // H kod -> açıklama haritası (data/content.ts'den errorTypes ile)
  const hDescriptions: Record<string, string> = Object.fromEntries(
    errorTypes.map((et) => [et.code, et.name])
  );

  // Toplam süre
  const totalTime = records.reduce((sum: number, r: any) => sum + (r.timeSpentSec || 0), 0);
  const mm = Math.floor(totalTime / 60);
  const ss = totalTime % 60;

  // XP hesapla
  const xpEarned = correct * 2; // doğru başına 2 XP

  // Zayıf dersler (doğruluk < 60%)
  const weakSubjects = Object.entries(bySubject)
    .filter(([, v]) => v.total > 0 && v.correct / v.total < 0.6)
    .map(([k]) => k);

  return (
    <div className="summary">
      <div className="summary-grid">
        <div className="summary-card">
          <h3>Genel Sonuç</h3>
          <div className="big-number">{correct}/{total}</div>
          <div className="big-percent">%{correctPct}</div>
          <div className="summary-meta">
            <span>⏱ {mm} dk {ss} sn</span>
            <span>⭐ +{xpEarned} XP</span>
          </div>
        </div>
        <div className="summary-card">
          <h3>Ders Bazında</h3>
          <div className="subject-breakdown">
            {Object.entries(bySubject).map(([subj, v]) => (
              <div key={subj} className="subject-row">
                <span>{subj}</span>
                <span>{v.correct}/{v.total} (%{v.total ? Math.round((v.correct / v.total) * 100) : 0})</span>
              </div>
            ))}
          </div>
        </div>
        <div className="summary-card">
          <h3>Hata Türleri</h3>
          {Object.keys(byH).length > 0 ? (
            <div className="h-breakdown">
              {Object.entries(byH).map(([h, count]) => (
                <div key={h} className="h-row">
                  <span className="h-code">{h}</span>
                  <span>{count} hata</span>
                  <span className="h-desc">{hDescriptions[h]}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted-text">Hiç hata yok — mükemmel!</p>
          )}
        </div>
      </div>

      {weakSubjects.length > 0 && (
        <div className="weak-alert">
          <h4>🔍 Tekrar Edilmesi Gereken Konular</h4>
          <p>Bu derslerde doğruluk %60 altı:</p>
          <ul>
            {weakSubjects.map((s) => <li key={s}>{s}</li>)}
          </ul>
          <p className="muted-text">
            Yarın <a href="/pekistirme">Pekiştirme Soruları</a> sayfasında bu eksikliklerin üzerine odaklanarak yeni sorular hazırlanacak.
            Ayrıca <a href="/pekistirme">Pekiştirme Soruları</a> sayfasından ilgili dersi ve konuyu seçip tek başına çalışabilirsin.
          </p>
        </div>
      )}

      <div className="next-steps">
        <h4>📋 Sıradaki Adımlar</h4>
        <ol>
          <li>Yanlış yaptığın soruların H türünü not et — hangi alanda eksiklik var?</li>
          <li>Zayıf derslerde <a href="/pekistirme">pekiştirme çalışma</a> yap (ders filtresinden seç).</li>
          <li>
            Hafta sonu{" "}
            <a href={cycle?.weekendTest === "aylik" ? "/aylik-denemeler" : "/haftalik-test"}>
              {cycle?.weekendTest === "aylik" ? "aylık deneme" : "haftalık test"}
            </a>{" "}
            ile ilerlemeni ölç (cumartesi veya pazar).
          </li>
          <li><a href="/sonuclar">Sonuçlar ve İlerleme</a> sayfasından ünite ustalığını takip et.</li>
        </ol>
      </div>

      <div className="summary-actions">
        <a className="btn btn-primary" href="/calis">Yeni Günlük Çalışma Başlat</a>
        <a
          className={"btn btn-soft " + (learner.streakDays >= 5 ? "" : "disabled")}
          href={cycle?.weekendTest === "aylik" ? "/aylik-denemeler" : "/haftalik-test"}
          style={learner.streakDays < 5 ? { pointerEvents: "none", opacity: 0.5 } : {}}
        >
          {cycle?.weekendTest === "aylik" ? "Aylık Denemeye Geç" : "Haftalık Teste Geç"}
        </a>
        <a className="btn btn-soft" href="/sonuclar">İlerlemesini Gör</a>
      </div>
    </div>
  );
}

interface StudyQuestion {
  id: string;
  subject: string;
  sourceBook: string;
  questionNumber: number;
  page: number;
  imagePath: string;
  unit: number | null;
  unitName: string | null;
  section: string | null;
  questionText: string | null;
  topic: string | null;
  learningOutcomeCode: string | null;
  learningOutcomeText: string | null;
  pedagogicalDifficulty: number | null;
  difficultyConfidence: string | null;
  skill: string | null;
  questionType: string | null;
  analysisStatus: string | null;
  answer?: string | null;
}

export default function CalisPage() {
  const [questions, setQuestions] = useState<StudyQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [checkState, setCheckState] = useState<"pending" | "correct" | "wrong" | null>(null);
  const [errorReason, setErrorReason] = useState<string | null>(null);
  const [unitMastery, setUnitMastery] = useState<UnitMastery | null>(null);
  const [cycle, setCycle] = useState<CycleState | null>(null);
  const [completed, setCompleted] = useState(false);
  const questionStartRef = useRef<number>(Date.now());

  // Döngü: kayıt tarihinden itibaren 4 hafta.
  // Hafta sonu (cumartesi veya pazar) sınav günü: 1-3. hafta haftalık test,
  // 4. hafta aylık deneme.
  useEffect(() => {
    setCycle(computeCycleState());
    const onChange = () => setCycle(computeCycleState());
    window.addEventListener(ENROLLMENT_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(ENROLLMENT_CHANGED_EVENT, onChange);
  }, []);

  const dayType = cycle?.dayType ?? "gunluk";

  // Günlük soruları çek: 5'er Türkçe, Mat, Fen; 3'er İnkılap, Din, İngilizce = 24 soru
  // Sıralama: ünite artan, zorluk artan (kolaydan zora, 1. üniteden başlayarak)
  useEffect(() => {
    if (dayType !== "gunluk") return;
    setLoading(true);
    const subjectLimits: Record<string, number> = {
      turkce: 5,
      matematik: 5,
      fen: 5,
      "inkilap-tarihi": 3,
      "din-kulturu": 3,
      ingilizce: 3,
    };
    Promise.all(
      subjects.map((s) =>
        fetch(`/api/study?subject=${s.slug}&limit=${subjectLimits[s.slug]}&sort=unit_difficulty`)
          .then((r) => r.json())
          .then((d) => (d.items || []) as StudyQuestion[])
      )
    )
      .then((batches) => {
        const merged = batches.flat();
        setQuestions(merged);
        setCurrentIndex(0);
        setSelectedAnswer(null);
        setShowResult(false);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [dayType]);

  // Cumartesi: döngüdeki haftaya göre haftalık test veya aylık denemeye yönlendir
  useEffect(() => {
    if (!cycle) return;
    if (cycle.dayType === "haftalik") {
      window.location.href = "/haftalik-test";
    } else if (cycle.dayType === "aylik") {
      window.location.href = "/aylik-denemeler";
    }
  }, [cycle]);

  const currentQuestion = questions[currentIndex];

  // Soru değişince çözüm süresi sayacı sıfırlanır
  useEffect(() => {
    questionStartRef.current = Date.now();
  }, [currentQuestion?.id]);

  // Ünite ustalığı cevap kayıtlarından kural tabanlı türetilir (plan §45)
  useEffect(() => {
    if (!currentQuestion) return;
    const found = computeUnitMasteries().find(
      (m) => m.subject === currentQuestion.subject && m.unit === currentQuestion.unit
    );
    setUnitMastery(found ?? null);
  }, [currentQuestion?.subject, currentQuestion?.unit, checkState, errorReason]);

  const handleAnswer = (letter: string) => {
    if (showResult) return;
    setSelectedAnswer(letter);
    setShowResult(true);
    setCheckState("pending");
    setErrorReason(null);
    const q = currentQuestion;
    const startedAt = questionStartRef.current;
    fetch("/api/study", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: q.id, answer: letter }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (typeof data.correct !== "boolean") {
          setCheckState(null);
          return;
        }
        setCheckState(data.correct ? "correct" : "wrong");
        if (data.correct) {
          saveAnswerRecord({
            questionId: q.id,
            subject: q.subject,
            unit: q.unit,
            unitName: q.unitName,
            topic: q.topic,
            selectedAnswer: letter,
            correct: true,
            errorReasonCode: null,
            timeSpentSec: Math.max(0, Math.round((Date.now() - startedAt) / 1000)),
            createdAt: new Date().toISOString(),
          });
        }
      })
      .catch(() => setCheckState(null));
  };

  const selectErrorReason = (code: string | null) => {
    setErrorReason(code ?? "SKIPPED");
    const q = currentQuestion;
    if (!q || !selectedAnswer) return;
    saveAnswerRecord({
      questionId: q.id,
      subject: q.subject,
      unit: q.unit,
      unitName: q.unitName,
      topic: q.topic,
      selectedAnswer,
      correct: false,
      errorReasonCode: code,
      timeSpentSec: Math.max(0, Math.round((Date.now() - questionStartRef.current) / 1000)),
      createdAt: new Date().toISOString(),
    });
  };

  const nextQuestion = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setSelectedAnswer(null);
      setShowResult(false);
      setCheckState(null);
      setErrorReason(null);
    } else {
      setCompleted(true);
    }
  };

  // Büyütülmüş görsel açıkken ESC ile kapat
  useEffect(() => {
    if (!zoomOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoomOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomOpen]);

  const gunAdlari = ["Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi"];
  const bugun = gunAdlari[new Date().getDay()];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Çalışma alanı</span>
          <h1>Günlük Çalışma Planı</h1>
          <p>
            Bugün {bugun}.{" "}
            {dayType === "gunluk" && "Türkçe, Matematik, Fen 5'er; İngilizce, İnkılap, Din 3'er = 24 soru."}
            {dayType === "haftalik" && "Bugün haftalık test günü."}
            {dayType === "aylik" && "Bugün aylık deneme günü."}
            {dayType === "dinlenme" && "Dinlenme günü."}
          </p>
          {cycle && (
            <p className="muted-text" style={{ marginTop: 6, fontSize: 13 }}>
              {cycleSummary(cycle)}
            </p>
          )}
        </div>
        {dayType === "haftalik" && (
          <Link className="btn btn-primary" href="/haftalik-test">
            Haftalık teste git <Icon name="arrow" size={18} />
          </Link>
        )}
        {dayType === "aylik" && (
          <Link className="btn btn-primary" href="/aylik-denemeler">
            Aylık denemeye git <Icon name="arrow" size={18} />
          </Link>
        )}
      </header>

      {dayType === "dinlenme" && (
        <section className="card" style={{ textAlign: "center", padding: 40 }}>
          <h2>🎉 Bugün Dinlenme Günü</h2>
          <p style={{ marginTop: 12, color: "var(--metin-soluk)" }}>
            Bu hafta çok iyi çalıştın. Zihnini dinlendir, yarın yenilenmiş başla.
          </p>
        </section>
      )}

      {dayType === "gunluk" && loading && <div className="exam-loading">Günlük sorular yükleniyor...</div>}

      {dayType === "gunluk" && !loading && !currentQuestion && (
        <div className="exam-empty">Bugün için soru bulunamadı.</div>
      )}

      {dayType === "gunluk" && currentQuestion && (
        <section className="exam-question" id="sorular">
          <div className="exam-question-header">
            <span className="pill is-gok">
              Soru {currentIndex + 1} / {questions.length}
            </span>
            <span className="pill is-mint" style={{ fontSize: 11 }}>
              {currentQuestion.subject} · {currentQuestion.unitName || "—"}
            </span>
          </div>
          <div className="exam-question-image">
            <img
              src={currentQuestion.imagePath}
              alt={`${currentQuestion.subject} soru ${currentQuestion.questionNumber}`}
              loading="eager"
              onClick={() => setZoomOpen(true)}
            />
          </div>
          <p className="exam-image-hint">Görseli büyütmek için tıkla</p>
          <div className="exam-answers">
            {["A", "B", "C", "D"].map((letter) => (
              <button
                key={letter}
                className={`exam-answer-btn ${selectedAnswer === letter ? "selected" : ""}`}
                onClick={() => handleAnswer(letter)}
                disabled={showResult}
              >
                {letter}
              </button>
            ))}
          </div>
          {showResult && (
            <div className="exam-result">
              <p>
                Cevabın: <b>{selectedAnswer}</b>
                {checkState === "correct" && <span className="correct"> ✓ Doğru</span>}
                {checkState === "wrong" && <span className="wrong"> ✗ Yanlış</span>}
              </p>
              {checkState === "wrong" && errorReason === null && (
                <div className="error-reason">
                  <p className="muted-text">Yanlışını anlamamıza yardım et — sana en yakın olanı seç:</p>
                  <div className="error-reason-options">
                    {ERROR_REASON_OPTIONS_LOCAL.map((opt) => (
                      <button key={opt.id} className="btn btn-soft" onClick={() => selectErrorReason(opt.code)}>
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {errorReason && errorReason !== "SKIPPED" && (
                <div className="error-reason-result">
                  <b>{errorReason} · {errorTypes.find((e) => e.code === errorReason)?.name}</b>
                  <p className="muted-text">{errorTypes.find((e) => e.code === errorReason)?.advice}</p>
                </div>
              )}
              <p className="muted-text">Cevap anahtarı sunucuda tutulur.</p>
            </div>
          )}
          {showResult && (
            <button className="btn btn-soft" onClick={nextQuestion}>
              Sonraki soru <Icon name="arrow" size={16} />
            </button>
          )}
        </section>
      )}

      {zoomOpen && currentQuestion && (
        <div className="zoom-overlay" onClick={() => setZoomOpen(false)} role="button" aria-label="Görseli kapat">
          <img src={currentQuestion.imagePath} alt={`${currentQuestion.subject} soru ${currentQuestion.questionNumber} — büyütülmüş`} />
        </div>
      )}

      {completed && (
        <section className="card" id="ozet" style={{ marginTop: 24 }}>
          <h2>🎉 Günlük Çalışma Tamamlandı!</h2>
          <p className="muted-text">Bugün {questions.length} soru çözdün. Harika bir ilerleme!</p>
          <DailySummary questions={questions} cycle={cycle} />
        </section>
      )}
    </div>
  );
}