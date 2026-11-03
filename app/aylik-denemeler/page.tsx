"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Icon } from "../../components/icons";
import { CycleBadge } from "../../components/cycle-badge";
import { subjects } from "../../data/content";
import { saveExamRecord, examDelta, type ExamRecord, loadExamHistory } from "../../lib/exam-history";
import { calculateExamScore } from "../../lib/exam-score";
import { getCycleAnchor, isMonthUnlocked, setCycleAnchor } from "../../lib/cycle";
import { syncReinforcementTasks } from "../../lib/reinforcement";
import { pushExamSession, pullExamSession, apiFetch } from "../../lib/sync";

interface ExamQuestion {
  id: string;
  month: number;
  monthName: string;
  subject: string;
  questionNumber: number;
  imagePath: string;
  originalYear: number;
  difficultyScore: number;
  questionType: string | null;
  visualDependency: string | null;
  underlineDependent: boolean | null;
  topic: string | null;
  unit: number | null;
  unitName: string | null;
}

interface ExamResult {
  total: number;
  correct: number;
  wrong: number;
  empty: number;
  percentage: number;
  level: string;
  bySubject: Record<string, { correct: number; wrong: number; empty: number; total: number }>;
  details: Array<{
    questionId: string;
    subject: string;
    given: string | null;
    correct: string | null;
    isCorrect: boolean;
    topic: string | null;
    unit: number | null;
    difficultyScore: number;
  }>;
}

interface MonthInfo {
  month: number;
  name: string;
  totalQuestions: number;
  durationMinutes: number;
}

export default function AylikDenemelerPage() {
  const searchParams = useSearchParams();
  const urlMonth = searchParams.get("month");
  const urlResume = searchParams.get("resume") === "1";
  const [months, setMonths] = useState<MonthInfo[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [examResult, setExamResult] = useState<ExamResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [timerEnded, setTimerEnded] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [completedMonths, setCompletedMonths] = useState<number[]>([]);
  const [serverResults, setServerResults] = useState<Array<{
    month: number;
    monthName: string;
    total: number;
    correct: number;
    wrong: number;
    empty: number;
    percentage: number;
    level: string;
    bySubject: Record<string, { correct: number; wrong: number; empty: number; total: number }>;
    completedAt: string;
  }>>([]);
  const completedMonthsRef = useRef<number[]>([]);
  completedMonthsRef.current = completedMonths;
  const serverResultsRef = useRef<Array<typeof serverResults[0]>>([]);
  serverResultsRef.current = serverResults;
  const [elapsedSec, setElapsedSec] = useState(0);
  const [subjectElapsed, setSubjectElapsed] = useState<Record<string, number>>({});
  const [pausedSubjects, setPausedSubjects] = useState<Record<string, boolean>>({});
  const subjectElapsedRef = useRef<Record<string, number>>({});
  const subjectPausedRef = useRef<Record<string, boolean>>({});
  const currentSubjectRef = useRef<string | null>(null);
  const [reportedIds, setReportedIds] = useState<Set<string>>(new Set());

  /** "Soru eksik veya bozuk" bildirimi — öğretmen paneline düşer. */
  const reportQuestion = useCallback(
    async (q: ExamQuestion) => {
      if (reportedIds.has(q.id)) return;
      setReportedIds((prev) => new Set(prev).add(q.id));
      try {
        await apiFetch("/api/question-reports", {
          method: "POST",
          body: JSON.stringify({
            source: "deneme",
            month: q.month,
            monthName: q.monthName,
            questionId: q.id,
            questionNumber: q.questionNumber,
            subject: q.subject,
            imagePath: q.imagePath,
          }),
        });
      } catch {
        // Sunucuya ulaşılamadıysa buton geri açılsın
        setReportedIds((prev) => {
          const next = new Set(prev);
          next.delete(q.id);
          return next;
        });
      }
    },
    [reportedIds]
  );

  // Büyütülmüş görsel açıkken ESC ile kapat
  useEffect(() => {
    if (!zoomOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoomOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomOpen]);

  useEffect(() => {
    fetch("/api/exams-by-month?list=true")
      .then((r) => r.json())
      .then((data) => {
        if (data.months) {
          setMonths(data.months);
          // Tamamlanan sınavlar (yerel kayıt) — biten sınavın sıradakisi açılır
          let done: number[] = [];
          try {
            done = JSON.parse(localStorage.getItem("lgs_completed_exams") || "[]");
          } catch {
            done = [];
          }
          setCompletedMonths(done);
          // Sunucu tarafı tamamlanma kayıtlarını da getir (localStorage kaybına karşı)
          apiFetch("/api/exams-status")
            .then((r) => r.json())
            .then((srv) => {
              if (Array.isArray(srv.completedMonths) && srv.completedMonths.length > 0) {
                const merged = [...new Set([...done, ...srv.completedMonths])];
                try {
                  localStorage.setItem("lgs_completed_exams", JSON.stringify(merged));
                } catch {}
                setCompletedMonths(merged);
              }
              if (Array.isArray(srv.results) && srv.results.length > 0) {
                setServerResults(srv.results);
              }
            })
            .catch(() => {});
          // İlk erişilebilir deneme: kayıt tarihine göre kademeli açılır
          // Seviye tespit (0) hemen aktif; diğerleri ay ay açılır
          // URL'de ?month= varsa o ayı seç (kaldığın yerden devam)
          const urlMonthNum = urlMonth !== null ? parseInt(urlMonth, 10) : NaN;
          const first = (!isNaN(urlMonthNum) && data.months.some((m: MonthInfo) => m.month === urlMonthNum)
            ? data.months.find((m: MonthInfo) => m.month === urlMonthNum)
            : data.months.find((m: MonthInfo) => isMonthUnlocked(m.month)) || data.months[0]);
          if (first) setSelectedMonth(first.month);
        }
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedMonth === null) return;
    // Biten deneme: sorular açılmaz, sadece sonuç gösterilir
    if (completedMonthsRef.current.includes(selectedMonth)) {
      setQuestions([]);
      setLoading(false);
      setSubmitted(true);
      setShowResult(true);
      setTimerStarted(false);
      // Yerel/sunucu kaydından sonucu çöz
      const localRec = loadExamHistory().filter((r) => r.month === selectedMonth).pop() ?? null;
      if (localRec) {
        setExamResult({
          total: localRec.total,
          correct: localRec.correct,
          wrong: localRec.wrong,
          empty: localRec.empty,
          percentage: localRec.percentage,
          level: localRec.level,
          bySubject: localRec.bySubject,
          details: localRec.details,
        });
      } else {
        const srv = serverResultsRef.current.find((r) => r.month === selectedMonth);
        if (srv) {
          setExamResult({
            total: srv.total,
            correct: srv.correct,
            wrong: srv.wrong,
            empty: srv.empty,
            percentage: srv.percentage,
            level: srv.level,
            bySubject: srv.bySubject,
            details: [],
          });
        }
      }
      return;
    }
    setLoading(true);
    setAnswers({});
    setSubmitted(false);
    setExamResult(null);
    setShowResult(false);
    setTimerEnded(false);
    setTimerStarted(false);
    setCurrentIndex(0);
    setElapsedSec(0);
    subjectElapsedRef.current = {};
    fetch(`/api/exams-by-month?month=${selectedMonth}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.items) setQuestions(data.items);
        // Kaldığın yerden devam: yarım kalmış oturumu geri yükle
        if (urlResume) {
          pullExamSession(selectedMonth).then((session) => {
            if (session) {
              setAnswers(session.answers || {});
              const idx = Math.max(0, Math.min((session.current_index || 0), (data.items?.length || 1) - 1));
              setCurrentIndex(idx);
            }
          });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selectedMonth, urlResume]);

  const [timerStarted, setTimerStarted] = useState(false);

  // Toplam sınav süresi (görünmez sayaç) — süre bitince otomatik teslim
  const examActive = selectedMonth !== null && questions.length > 0 && !submitted && !timerEnded && timerStarted;
  useEffect(() => {
    if (!examActive) return;
    const id = setInterval(() => {
      const subj = currentSubjectRef.current;
      if (subj && !subjectPausedRef.current[subj]) {
        subjectElapsedRef.current[subj] = (subjectElapsedRef.current[subj] || 0) + 1;
        setSubjectElapsed({ ...subjectElapsedRef.current });
      }
      setElapsedSec((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(id);
  }, [examActive]);

  useEffect(() => {
    if (examActive && elapsedSec >= durationMinutes * 60) handleTimeEnd();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsedSec, examActive]);

  // Sunucu verisi geç geldiyse ve seçili ay tamamlanmışsa — aktif oturum yoksa sonucu göster
  useEffect(() => {
    if (selectedMonth === null || submitted) return;
    if (!completedMonths.includes(selectedMonth)) return;
    // Kullanıcı zaten başladıysa oturumu koru (sınav başlatmış ya da cevap vermiş)
    if (timerStarted || Object.keys(answers).length > 0) return;
    setQuestions([]);
    setLoading(false);
    setSubmitted(true);
    setShowResult(true);
    setTimerStarted(false);
    const localRec = loadExamHistory().filter((r) => r.month === selectedMonth).pop() ?? null;
    if (localRec) {
      setExamResult({
        total: localRec.total,
        correct: localRec.correct,
        wrong: localRec.wrong,
        empty: localRec.empty,
        percentage: localRec.percentage,
        level: localRec.level,
        bySubject: localRec.bySubject,
        details: localRec.details,
      });
    } else {
      const srv = serverResultsRef.current.find((r) => r.month === selectedMonth);
      if (srv) {
        setExamResult({
          total: srv.total,
          correct: srv.correct,
          wrong: srv.wrong,
          empty: srv.empty,
          percentage: srv.percentage,
          level: srv.level,
          bySubject: srv.bySubject,
          details: [],
        });
      }
    }
  }, [completedMonths, selectedMonth, submitted, timerStarted, answers]);

  const handleAnswer = useCallback((letter: string) => {
    if (submitted || timerEnded) return;
    const currentQ = questions[currentIndex];
    if (!currentQ) return;
    const nextAnswers = { ...answers, [currentQ.id]: letter };
    setAnswers(nextAnswers);
    // Sunucuya kaydet — cihaz değiştirdiğinde kaldığın yerden devam
    if (selectedMonth !== null) {
      pushExamSession(selectedMonth, nextAnswers, currentIndex);
    }
  }, [currentIndex, questions, answers, submitted, timerEnded, selectedMonth]);

  const nextQuestion = useCallback(() => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setShowResult(false);
    }
  }, [currentIndex, questions.length]);

  const prevQuestion = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
      setShowResult(false);
    }
  }, [currentIndex]);

  const selectedMonthInfo = useMemo(
    () => months.find((m) => m.month === selectedMonth),
    [months, selectedMonth]
  );

  const finishExam = useCallback(async () => {
    if (selectedMonth === null) return;
    setSubmitted(true);
    try {
      const res = await apiFetch("/api/exams-submit", {
        method: "POST",
        body: JSON.stringify({ month: selectedMonth, answers }),
      });
      const data = await res.json();
      if (data.correct !== undefined) {
        setExamResult(data);
        setShowResult(true);
        // Aylık deneme tamamlandı olarak kaydedilir; sıradaki deneme açılır
        setCompletedMonths((prev) => {
          const next = prev.includes(selectedMonth) ? prev : [...prev, selectedMonth];
          try {
            localStorage.setItem("lgs_completed_exams", JSON.stringify(next));
          } catch {
            // kayıt başarısız olsa bile arayüz güncel kalır
          }
          return next;
        });
        // Kalıcı deneme kaydı (Sonuçlar ve İlerleme sayfası için)
        const record: ExamRecord = {
          date: new Date().toISOString(),
          month: selectedMonth,
          monthName: selectedMonthInfo?.name || `${selectedMonth}_ay`,
          total: data.totalQuestions ?? questions.length,
          correct: data.correct,
          wrong: data.wrong,
          empty: data.empty,
          percentage: data.percentage,
          level: data.level,
          bySubject: data.bySubject,
          details: data.details,
        };
        saveExamRecord(record);
        // Seviye tespiti (0. ay) bittiyse döngü anchor'ını ayarla
        if (selectedMonth === 0) {
          setCycleAnchor(new Date());
        }
        // Pekiştirme görevlerini senkronize et (aylık deneme kaynaklı 3+ yanlış)
        syncReinforcementTasks();
      }
    } catch (e) {
      console.error("Aylık deneme değerlendirme hatası:", e);
    }
  }, [selectedMonth, answers, questions.length, selectedMonthInfo]);

  const handleTimeEnd = useCallback(() => {
    setTimerEnded(true);
    if (!submitted) finishExam();
  }, [submitted, finishExam]);

  const currentQuestion = questions[currentIndex];
  currentSubjectRef.current = currentQuestion?.subject ?? null;
  const durationMinutes = selectedMonthInfo?.durationMinutes || 155;
  const getSubjectName = (slug: string) => subjects.find((s) => s.slug === slug)?.name || slug;

  const currentDetail = useMemo(() => {
    if (!examResult || !currentQuestion) return null;
    return examResult.details.find((d) => d.questionId === currentQuestion.id);
  }, [examResult, currentQuestion]);

  // Render helpers - ternary yerine değişkenler
  const renderLoading = () => <div className="exam-loading">Aylık deneme yükleniyor...</div>;

  const renderEmpty = () => <div className="exam-empty">Bu deneme için soru bulunamadı.</div>;

  // O an çözülen dersin geri sayım kartı (öneri tempo: soru başına 1,5 dk)
  const renderSubjectTimer = () => {
    if (!currentQuestion) return null;
    const subj = currentQuestion.subject;
    const count = questions.filter((q) => q.subject === subj).length;
    const allotSec = Math.round(count * 1.5 * 60);
    const used = subjectElapsed[subj] ?? subjectElapsedRef.current[subj] ?? 0;
    const remaining = Math.max(0, allotSec - used);
    const mm = Math.floor(remaining / 60).toString().padStart(2, "0");
    const ss = (remaining % 60).toString().padStart(2, "0");
    const isPaused = pausedSubjects[subj] ?? subjectPausedRef.current[subj] ?? false;
    return (
      <div className="subject-timer" role="timer" aria-live="polite">
        <small>
          {getSubjectName(subj)} · {count} soru · {Math.round(allotSec / 60)} dk
        </small>
        <b className={remaining <= 60 ? "danger" : ""}>
          {mm}:{ss}
        </b>
        <div className="subject-timer-controls">
          <button
            className="btn btn-soft btn-sm"
            onClick={() => {
              const nextPaused = !isPaused;
              subjectPausedRef.current[subj] = nextPaused;
              setPausedSubjects({ ...subjectPausedRef.current });
            }}
            aria-label={isPaused ? "Devam et" : "Durdur"}
          >
            {isPaused ? "▶ Devam" : "⏸ Durdur"}
          </button>
          <button
            className="btn btn-soft btn-sm"
            onClick={() => {
              subjectElapsedRef.current[subj] = 0;
              setSubjectElapsed({ ...subjectElapsedRef.current });
            }}
            aria-label="Sıfırla"
          >
            ↻ Sıfırla
          </button>
        </div>
      </div>
    );
  };

  const renderExamQuestion = () => {
    if (!currentQuestion) return null;

    // Sayaç henüz başlatılmadıysa başlangıç ekranı göster
    if (!timerStarted) {
      return (
        <section className="exam-question" style={{ textAlign: "center", padding: 40 }}>
          <h2>📝 {selectedMonthInfo?.name || "Aylık Deneme"}</h2>
          <p style={{ marginTop: 12, color: "var(--metin-soluk)" }}>
            {questions.length} soru · {durationMinutes} dakika
          </p>
          <p style={{ marginTop: 8, color: "var(--metin-soluk)", fontSize: 14 }}>
            Süreyi başlattığında sayaç işlemeye başlar. Hazır olduğunda butona bas.
          </p>
          <button
            className="btn btn-primary"
            style={{ marginTop: 20, padding: "14px 32px", fontSize: 16 }}
            onClick={() => setTimerStarted(true)}
          >
            ▶ Süreyi Başlat
          </button>
        </section>
      );
    }

    return (
      <section className="exam-question">
        <div className="exam-question-header">
          <span className="pill is-mint">
            {selectedMonthInfo?.name || (selectedMonth === 0 ? "Seviye Tespit" : `${selectedMonth}. Ay`)}
          </span>
          <span className="pill is-gok">Soru {currentQuestion.questionNumber}</span>
        </div>

        <div className="exam-question-image">
          <img
            src={currentQuestion.imagePath}
            alt={`${selectedMonthInfo?.name} ${currentQuestion.subject} soru ${currentQuestion.questionNumber}`}
            loading="eager"
            onClick={() => setZoomOpen(true)}
          />
        </div>
        <p className="exam-image-hint">Görseli büyütmek için tıkla</p>

        <div className="exam-report-row">
          <button
            type="button"
            className={`exam-report-btn ${reportedIds.has(currentQuestion.id) ? "is-done" : ""}`}
            onClick={() => reportQuestion(currentQuestion)}
            disabled={reportedIds.has(currentQuestion.id)}
          >
            {reportedIds.has(currentQuestion.id)
              ? "✓ Öğretmene bildirildi"
              : "⚠ Soru eksik veya bozuk"}
          </button>
        </div>

        <div className="exam-answers-row">
          <div className="exam-answers">
            {["A", "B", "C", "D"].map((letter) => (
              <button
                key={letter}
                className={`exam-answer-btn ${answers[currentQuestion.id] === letter ? "selected" : ""} ${submitted || timerEnded ? "disabled" : ""}`}
                onClick={() => handleAnswer(letter)}
                disabled={submitted || timerEnded}
              >
                {letter}
              </button>
            ))}
          </div>
          {renderSubjectTimer()}
        </div>

        {showResult && examResult && currentDetail && (
          <div className="exam-result">
            <p>
              Cevabın: <b>{answers[currentQuestion.id] || "—"}</b>
              {currentDetail?.isCorrect !== undefined && (
                <span className={currentDetail.isCorrect ? "correct" : "wrong"}>
                  {currentDetail.isCorrect ? " ✓ Doğru" : " ✗ Yanlış"}
                </span>
              )}
            </p>
            <p className="muted-text">
              {currentDetail?.topic && `Konu: ${currentDetail.topic}`}
              {currentDetail?.unit && ` · Ünit: ${currentDetail.unit}`}
            </p>
          </div>
        )}

        <div className="exam-navigation">
          {currentIndex > 0 && (
            <button className="btn btn-soft" onClick={prevQuestion} disabled={submitted || timerEnded}>
              <Icon name="arrow" size={16} /> Önceki
            </button>
          )}
          {currentIndex < questions.length - 1 ? (
            <button className="btn btn-primary" onClick={nextQuestion} disabled={submitted || timerEnded}>
              Sonraki <Icon name="arrow" size={16} />
            </button>
          ) : (
            <button className="btn btn-primary" onClick={finishExam} disabled={submitted || timerEnded}>
              Denemeyi Bitir ve Değerlendir
            </button>
          )}
        </div>
      </section>
    );
  };

  const renderResultScreen = () => {
    if (!examResult) return null;
    const delta = examDelta();
    const score = calculateExamScore(examResult);
    return (
      <section className="exam-result-screen">
        <div className="result-header">
          <h2>Deneme Sonucu</h2>
          <span className={`result-level ${examResult.level.toLowerCase().replace(" ", "-")}`}>
            {examResult.level} — %{examResult.percentage}
            {delta !== 0 && (
              <em style={{ marginLeft: 10, fontStyle: "normal", fontSize: 13 }}>
                {delta > 0 ? "▲ +" : "▼ "}{delta} puan
              </em>
            )}
          </span>
        </div>
        <div className="result-stats">
          <div className="stat"><b>{examResult.correct}</b><small>Doğru</small></div>
          <div className="stat"><b>{examResult.wrong}</b><small>Yanlış</small></div>
          <div className="stat"><b>{examResult.empty}</b><small>Boş</small></div>
          <div className="stat lgs-score"><b>{score.overall.rawScore}</b><small>LGS Ham Puanı</small></div>
        </div>
        <div className="result-by-subject">
          <h3>Ders Bazında</h3>
          {Object.entries(examResult.bySubject).map(([subj, stats]) => (
            <div key={subj} className="subject-stat">
              <span>{getSubjectName(subj)}</span>
              <span>{stats.correct}/{stats.total} ( %{Math.round((stats.correct / stats.total) * 100)} )</span>
            </div>
          ))}
        </div>
        <div className="result-actions">
          <Link className="btn btn-primary" href="/pekistirme">
            Pekiştirme sorularına geç <Icon name="arrow" size={16} />
          </Link>
          <Link className="btn btn-soft" href="/sonuclar">
            Ayrıntılı analiz <Icon name="arrow" size={16} />
          </Link>
          <button className="btn btn-soft" onClick={() => {
            setSelectedMonth(null);
            setExamResult(null);
            setSubmitted(false);
            setShowResult(false);
          }}>
            Başka Deneme Seç
          </button>
        </div>
        <p className="muted-text" style={{ marginTop: 12 }}>
          {examResult.wrong > 0
            ? `${examResult.wrong} yanlış yaptın. 3+ yanlış olan üniteler için otomatik pekiştirme görevi oluştu.`
            : "Bu denemede yanlışın yok. Tebrikler!"}
        </p>
      </section>
    );
  };

  const renderExamInfo = () => (
    <section className="exam-info">
      <div className="card">
        <h2>Aylık Deneme Takvimi</h2>
        <p>
          Denemeler <b>her ay bir, cumartesi</b> yapılır. Her deneme sonrası yanlış
          yaptığın konular otomatik olarak <b>/pekistirme</b> sayfasına aktarılır;
          detaylı analiz için <b>/sonuclar</b> sayfasına geç.
        </p>
        <div className="denetim-akıs">
          <div className="denetim-adım"><b>1. Seviye Tespit</b><small>Kayıt olunca hemen</small></div>
          <Icon name="arrow" size={16} />
          <div className="denetim-adım"><b>2. Aylık Deneme</b><small>11 ay, kolaydan zora</small></div>
          <Icon name="arrow" size={16} />
          <div className="denetim-adım"><b>3. Pekiştirme</b><small>/pekistirme → 5 yeni soru</small></div>
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
          <Link className="btn btn-soft" href="/sonuclar">
            Sonuçlar ve İlerleme <Icon name="arrow" size={16} />
          </Link>
          <Link className="btn btn-soft" href="/pekistirme">
            Pekiştirme Soruları <Icon name="arrow" size={16} />
          </Link>
        </div>
      </div>
    </section>
  );

  // Main render logic - ternary yerine if/else
  const isCompleted = selectedMonth !== null && completedMonths.includes(selectedMonth);
  let mainContent: React.ReactNode;
  if (loading) {
    mainContent = renderLoading();
  } else if (submitted && examResult) {
    mainContent = null; // sonuç ekranı renderResultScreen() ile gösterilir
  } else if (selectedMonth !== null && isCompleted) {
    mainContent = null; // bitmiş deneme: sonuç ekranı zaten renderResultScreen()'de
  } else if (selectedMonth !== null && questions.length === 0) {
    mainContent = renderEmpty();
  } else if (selectedMonth !== null && questions.length > 0) {
    mainContent = renderExamQuestion();
  } else {
    mainContent = null;
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Aylık deneme takvimi</span>
          <h1>Aylık Denemeler</h1>
          <p>
            12 resmi MEB LGS denemesi — kolaydan zora, her ay 90 soru (155 dk).
            İlk sınav seviye tespiti için.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Çalışmaya başla <Icon name="arrow" size={18} />
        </Link>
      </header>

      <CycleBadge variant="aylik" />

      <section className="exam-controls">
        <div className="exam-filters">
          <label>
            <small>Deneme Dönemi</small>
            <select
              value={selectedMonth ?? ""}
              onChange={(e) => setSelectedMonth(e.target.value ? parseInt(e.target.value, 10) : null)}
              disabled={loading || submitted}
            >
              <option value="">Deneme seçin</option>
              {months.map((m) => {
                const done = completedMonths.includes(m.month);
                const locked = !isMonthUnlocked(m.month);
                return (
                  <option key={m.month} value={m.month} disabled={locked}>
                    {m.month === 0 ? "🎯 Seviye Tespit" : `📅 ${m.month}. Ay`} — {m.totalQuestions} soru, {m.durationMinutes} dk
                    {done ? " ✓ Tamamlandı" : locked ? " 🔒" : ""}
                  </option>
                );
              })}
            </select>
          </label>
        </div>

        {selectedMonth !== null && !loading && questions.length > 0 && (
          <div className="exam-progress">
            <small>Soru {currentIndex + 1} / {questions.length}</small>
            <div className="exam-progress-bar">
              <i style={{ width: `${((currentIndex + 1) / Math.max(questions.length, 1)) * 100}%` }} />
            </div>
          </div>
        )}
      </section>

      {mainContent}

      {renderResultScreen()}

      {renderExamInfo()}

      {zoomOpen && currentQuestion && (
        <div
          className="zoom-overlay"
          onClick={() => setZoomOpen(false)}
          role="button"
          aria-label="Görseli kapat"
        >
          <img
            src={currentQuestion.imagePath}
            alt={`${currentQuestion.subject} soru ${currentQuestion.questionNumber} — büyütülmüş`}
          />
        </div>
      )}
    </div>
  );
}