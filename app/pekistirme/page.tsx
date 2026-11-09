"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { subjects } from "../../data/content";
import { saveAnswerRecord } from "../../lib/error-reason";
import { pushReinforcementTasks, apiFetch } from "../../lib/sync";
import {
  syncReinforcementTasks,
  loadReinforcementTasks,
  getTasksBySubject,
  updateTaskStatus,
  assignQuestionsToTask,
  getAllTasks,
  getCompletedTaskCount,
  getPendingTaskCount,
} from "../../lib/reinforcement";
import {
  computeCycleState,
  type CycleState,
} from "../../lib/cycle";
import { loadAnswerRecords } from "../../lib/error-reason";
import { loadWeeklyTestHistory } from "../../lib/weekly-test-history";
import { composeTelafiTest, TELAFI_QUOTA, type TestQuestion } from "../../lib/weekly-test";

const SOURCE_LABELS: Record<string, string> = {
  gunluk: "Günlük Çalışma",
  haftalik: "Haftalık Değerlendirme",
  aylik: "Aylık Deneme",
};

const SOURCE_TONES: Record<string, string> = {
  gunluk: "pembe",
  haftalik: "mavi",
  aylik: "seftali",
};

const STATUS_LABELS: Record<string, string> = {
  bekliyor: "Bekliyor",
  "devam-ediyor": "Devam Ediyor",
  tamamlandi: "Tamamlandı",
};

const STATUS_TONES: Record<string, string> = {
  bekliyor: "limon",
  "devam-ediyor": "mavi",
  tamamlandi: "mint",
};

function sourcePill(source: string) {
  const tone = SOURCE_TONES[source] || "limon";
  return (
    <span className={"pill is-" + tone} style={{ fontSize: 11, marginLeft: 8 }}>
      {SOURCE_LABELS[source] || source}
    </span>
  );
}

function statusPill(status: string) {
  return (
    <span className={"pill is-" + (STATUS_TONES[status] || "limon")} style={{ fontSize: 11 }}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

function QuestionMini({ qid, idx, task, question, open, onAnswer, onNext, onReport, reported, onZoom }: {
  qid: string;
  idx: number;
  task: any;
  question: any;
  open: boolean;
  onAnswer: (letter: string) => void;
  onNext: () => void;
  onReport: () => void;
  reported: boolean;
  onZoom: (src: string) => void;
}) {
  const answer = task.answers?.[qid];
  const isCorrect = task.correctness?.[qid];
  let statusClass = "pending";
  if (isCorrect === true) statusClass = "correct";
  else if (isCorrect === false) statusClass = "wrong";
  let statusText = "Bekliyor";
  if (answer) statusText = isCorrect ? "✓ Doğru" : "✗ Yanlış";

  if (!open) return null;

  return (
    <section className="exam-question task-question-card">
      {question ? (
        <>
          <div className="exam-question-header">
            <span className="pill is-gok">Soru {idx + 1} / {task.questionIds.length}</span>
            <span className={"q-status " + statusClass}>{statusText}</span>
          </div>
          <div className="exam-question-image">
            <img
              src={question.imagePath}
              alt={`${question.subject} pekiştirme soru ${idx + 1}`}
              loading="eager"
              onClick={() => onZoom(question.imagePath)}
            />
          </div>
          <p className="exam-image-hint">Görseli büyütmek için tıkla</p>
          <div className="exam-report-row">
            <button
              type="button"
              className={"exam-report-btn " + (reported ? "is-done" : "")}
              onClick={onReport}
              disabled={reported}
            >
              {reported ? "✓ Öğretmene bildirildi" : "⚠ Soru eksik veya bozuk"}
            </button>
          </div>
          {answer ? (
            <div className="exam-result">
              <p style={{ fontWeight: 700 }}>
                Cevabın: <b>{answer}</b>
                {isCorrect ? <span className="correct"> ✓ Doğru</span> : <span className="wrong"> ✗ Yanlış</span>}
              </p>
              <button type="button" className="btn btn-soft" onClick={onNext}>
                {idx === task.questionIds.length - 1 ? "Görevi tamamla" : "Sonraki soru"}
                <Icon name="arrow" size={16} />
              </button>
            </div>
          ) : (
            <div className="exam-answers">
              {["A", "B", "C", "D"].map((letter) => (
                <button
                  key={letter}
                  className="exam-answer-btn"
                  onClick={() => onAnswer(letter)}
                >
                  {letter}
                </button>
              ))}
            </div>
          )}
        </>
      ) : (
        <p className="muted-text">Soru yükleniyor…</p>
      )}
    </section>
  );
}

export default function PekistirmePage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeSubject, setActiveSubject] = useState<string | null>(null);

  // Telafi (pazar) testi
  const [telafiItems, setTelafiItems] = useState<{ question: TestQuestion; category: "telafi" | "genel" }[] | null>(null);
  const [telafiLoading, setTelafiLoading] = useState(false);
  const [cycle, setCycle] = useState<CycleState | null>(null);
  // Görev soruları: qid → herkese açık soru (görsel vb.)
  const [questionBank, setQuestionBank] = useState<Record<string, any>>({});
  const [openQid, setOpenQid] = useState<string | null>(null);
  const [reportedIds, setReportedIds] = useState<Set<string>>(new Set());
  const [zoomSrc, setZoomSrc] = useState<string | null>(null);

  // Pazar telafi testi verilerini çek
  useEffect(() => {
    const c = computeCycleState();
    setCycle(c);
  }, []);

  useEffect(() => {
    if (!cycle || cycle.dayType !== "telafi") return;
    setTelafiLoading(true);
    Promise.all(
      subjects.map((s) =>
        fetch(`/api/study?subject=${s.slug}&limit=${(TELAFI_QUOTA as Record<string, number>)[s.slug]}&sort=unit_difficulty`)
          .then((r) => r.json())
          .then((d) => (d.items || []) as TestQuestion[])
      )
    )
      .then((batches) => {
        const pool = batches.flat();
        const history = loadWeeklyTestHistory();
        const latestWeekly = history[0];
        const weeklyWrongIds = new Set<string>();
        if (latestWeekly?.wrongQuestionIds) {
          for (const id of latestWeekly.wrongQuestionIds) {
            weeklyWrongIds.add(id);
          }
        }
        const dailyRecords = loadAnswerRecords().filter((r) => {
          const daysDiff = ((Date.now() - new Date(r.createdAt).getTime()) / (24 * 60 * 60 * 1000));
          return daysDiff <= 7 && !r.correct;
        });
        const composed = composeTelafiTest(
          pool,
          dailyRecords,
          weeklyWrongIds,
          new Date()
        );
        setTelafiItems(composed);
        setTelafiLoading(false);
      })
      .catch(() => setTelafiLoading(false));
  }, []);

  useEffect(() => {
    // Load existing tasks first (persisted), then sync for new weak units
    const existing = loadReinforcementTasks();
    setTasks(existing);
    // Sync in background to add any newly detected weak units
    const synced = syncReinforcementTasks();
    setTasks(synced);
    setLoading(false);
  }, []);

  /** Görevin atanmış sorularının görsellerini getir (eski görevler dahil). */
  const loadTaskQuestions = (task: any) => {
    const missing = (task.questionIds || []).filter((qid: string) => !questionBank[qid]);
    if (missing.length === 0) return;
    const unitParam = task.unit === null || task.unit === undefined ? "" : "&unit=" + task.unit;
    apiFetch("/api/study?subject=" + task.subject + unitParam + "&limit=50&sort=unit_difficulty")
      .then((r) => r.json())
      .then((data: any) => {
        const wanted = new Set<string>(task.questionIds || []);
        const items: any[] = data.items || [];
        setQuestionBank((prev) => {
          const next = { ...prev };
          for (const q of items) if (wanted.has(q.id)) next[q.id] = q;
          return next;
        });
      })
      .catch(() => {});
  };

  /** "Soru eksik veya bozuk" bildirimi — öğretmen paneline düşer. */
  const reportQuestion = (q: any) => {
    if (!q || reportedIds.has(q.id)) return;
    setReportedIds((prev) => new Set(prev).add(q.id));
    apiFetch("/api/question-reports", {
      method: "POST",
      body: JSON.stringify({
        source: "pekistirme",
        monthName: q.sourceBook,
        questionId: q.id,
        questionNumber: q.questionNumber,
        subject: q.subject,
        imagePath: q.imagePath,
      }),
    }).catch(() => {
      setReportedIds((prev) => {
        const next = new Set(prev);
        next.delete(q.id);
        return next;
      });
    });
  };

  const handleStartTask = (task: any) => {
    if (task.questionIds.length > 0) {
      updateTaskStatus(task.id, "devam-ediyor");
      loadTaskQuestions(task);
      const firstUnanswered =
        task.questionIds.find((qid: string) => !task.answers?.[qid]) ?? task.questionIds[0];
      setOpenQid(firstUnanswered);
      setTasks(syncReinforcementTasks());
      pushReinforcementTasks(getAllTasks());
      return;
    }
    const unitParam = task.unit === null || task.unit === undefined ? "" : "&unit=" + task.unit;
    apiFetch("/api/study?subject=" + task.subject + unitParam + "&limit=50&sort=unit_difficulty")
      .then((r) => r.json())
      .then((data: any) => {
        const items: any[] = data.items || [];
        const unitItems =
          task.unit === null || task.unit === undefined
            ? items
            : items.filter((q: any) => q.unit === task.unit);
        // Daha önce sunulmuş sorular tekrar atanmaz; havuz tükenirse geri döner.
        const served = new Set<string>(task.servedQuestionIds ?? []);
        const fresh = unitItems.filter((q: any) => !served.has(q.id));
        const pool = fresh.length >= 5 ? fresh : unitItems;
        const selected = pool.slice(0, 5).map((q: any) => q.id);
        if (selected.length > 0) {
          assignQuestionsToTask(task.id, selected);
          updateTaskStatus(task.id, "devam-ediyor");
          setQuestionBank((prev) => {
            const next = { ...prev };
            for (const q of unitItems) if (selected.includes(q.id)) next[q.id] = q;
            return next;
          });
          setOpenQid(selected[0]);
          setTasks(syncReinforcementTasks());
          pushReinforcementTasks(getAllTasks());
        }
      })
      .catch(() => {});
  };

  const handleSelectSubject = (subjectSlug: string) => {
    setActiveSubject(subjectSlug);
    const subjectTasks = getTasksBySubject(subjectSlug);
    const task = subjectTasks.find((item: any) => item.status !== "tamamlandi") ?? subjectTasks[0];
    if (!task) {
      setOpenQid(null);
      return;
    }
    if (task.status === "tamamlandi" && task.questionIds.length > 0) {
      loadTaskQuestions(task);
      setOpenQid(task.questionIds.find((qid: string) => !task.answers?.[qid]) ?? task.questionIds[0]);
      return;
    }
    handleStartTask(task);
  };

  const handleNextQuestion = (task: any, currentQid: string) => {
    const currentIndex = task.questionIds.indexOf(currentQid);
    const nextUnanswered = task.questionIds
      .slice(currentIndex + 1)
      .find((qid: string) => !task.answers?.[qid]);
    const anyUnanswered = task.questionIds.find((qid: string) => !task.answers?.[qid]);
    setOpenQid(nextUnanswered ?? anyUnanswered ?? null);
  };

  const handleAnswer = (taskId: string, questionId: string, answer: string) => {
    apiFetch("/api/study", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: questionId, answer }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (typeof data.correct === "boolean") {
          // Save answer record for reinforcement tracking with metadata from API
          const qmeta = data.question || {};
          saveAnswerRecord({
            questionId,
            source: "pekistirme",
            subject: qmeta.subject || "",
            unit: qmeta.unit ?? null,
            unitName: qmeta.unitName ?? null,
            topic: qmeta.topic ?? null,
            selectedAnswer: answer,
            correct: data.correct,
            errorReasonCode: null,
            timeSpentSec: 0,
            createdAt: new Date().toISOString(),
          });

          updateTaskStatus(
            taskId,
            "devam-ediyor",
            { [questionId]: answer },
            { [questionId]: data.correct }
          );
          // 5 sorunun tamamı cevaplandıysa görev tamamlanır.
          const updated = loadReinforcementTasks().find((t) => t.id === taskId);
          if (
            updated &&
            updated.questionIds.length > 0 &&
            updated.questionIds.every((qid: string) => updated.answers?.[qid])
          ) {
            updateTaskStatus(taskId, "tamamlandi");
          }
          setTasks(syncReinforcementTasks());
          pushReinforcementTasks(getAllTasks());
        }
      })
      .catch(() => {});
  };

  // Büyütülmüş görsel açıkken ESC ile kapat
  useEffect(() => {
    if (!zoomSrc) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoomSrc(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomSrc]);

  if (loading) {
    return (
      <div className="page">
        <div className="exam-loading">Pekiştirme görevleri yükleniyor...</div>
      </div>
    );
  }

  const completedCount = getCompletedTaskCount();
  const pendingCount = getPendingTaskCount();
  const allTasks = getAllTasks();
  const activeSubjectInfo = subjects.find((s) => s.slug === activeSubject);

  // Telafi day → show only telafi test within the page layout
  const isTelafiDay = cycle?.dayType === "telafi";

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Eksiklik giderme merkezi</span>
          <h1>Pekiştirme Soruları</h1>
          <p>
            Günlük, haftalık ve aylık değerlendirmelerde tespit edilen eksikliklerin giderildiği
            merkezi alan.
            {pendingCount > 0 && <span style={{ marginLeft: 12 }}> — {pendingCount} bekleyen görev</span>}
            {completedCount > 0 && <span style={{ marginLeft: 8 }}>✓ {completedCount} tamamlandı</span>}
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Günlük Alıştırmaya Dön <Icon name="arrow" size={18} />
        </Link>
      </header>

      {/* Pazar Telafi Testi */}
      {cycle?.dayType === "telafi" && (
        <section className="telafi-section" aria-labelledby="telafi-heading">
          <header className="telafi-header">
            <h2 id="telafi-heading">📅 Pazar Telafi Testi</h2>
            <p className="muted-text">
              Bu hafta günlük çalışmalardaki ve haftalık testteki yanlışlarını kapatmak için
              24 soruluk telafi testi. Her ders: Türkçe 5, Matematik 5, Fen 5, İnkılap 3, Din 3, İngilizce 3.
            </p>
            {telafiLoading && <span className="telafi-loading">Sorular hazırlanıyor...</span>}
          </header>

          {telafiItems && telafiItems.length > 0 && (
            <div className="telafi-grid">
              {telafiItems.map((item, idx) => (
                <article key={item.question.id} className="telafi-card">
                  <div className="telafi-card-header">
                    <span className="telafi-index">Soru {idx + 1}</span>
                    <span className={`telafi-category ${item.category}`}>
                      {item.category === "telafi" ? "↩️ Bu hafta yanlış yaptığın" : "🔁 Genel tekrar"}
                    </span>
                  </div>
                  <div className="telafi-question">
                    <img
                      src={item.question.imagePath}
                      alt={`Telafi soru ${idx + 1}`}
                      loading="lazy"
                    />
                  </div>
                  <div className="telafi-meta">
                    <span>{item.question.subject}</span>
                    {item.question.unitName && <span>· Ünite {item.question.unitName}</span>}
                  </div>
                </article>
              ))}
            </div>
          )}
          {!telafiLoading && !telafiItems && (
            <p className="muted-text" style={{ textAlign: "center", padding: 24 }}>
              Bu hafta telafi edilecek yanlış yok — harika!
            </p>
          )}
        </section>
      )}

      {allTasks.length === 0 && (
        <section className="card empty-state">
          <h2>🎉 Henüz pekiştirme görevi yok!</h2>
          <p className="muted-text">
            Günlük çalışmalar, haftalık testler veya aylık denemelerde bir ünitede 3+ yanlış
            yaptığınızda buraya otomatik olarak pekiştirme görevi eklenecek.
          </p>
          <Link className="btn btn-primary" href="/calis" style={{ marginTop: 16 }}>
            Günlük Alıştırmaya Başla <Icon name="arrow" size={18} />
          </Link>
        </section>
      )}

      <nav className="subject-tabs" aria-label="Ders seçimi">
        {subjects.map((subject) => {
          const count = getTasksBySubject(subject.slug).length;
          return (
            <button
              key={subject.slug}
              className={"subject-tab " + (activeSubject === subject.slug ? "active" : "")}
              onClick={() => handleSelectSubject(subject.slug)}
              style={{ "--subject-tone": "var(--" + subject.tone + ")" } as React.CSSProperties}
            >
              <span className="subject-tab-icon">{subject.icon}</span>
              <span>{subject.name}</span>
              {count > 0 && <span className="subject-tab-count">{count}</span>}
            </button>
          );
        })}
      </nav>

      {activeSubject ? (
        <section className="subject-panel" id={activeSubject}>
          <div className="panel-header">
            <h2>
              <span
                className={
                  "subject-ico tone-bg-" + (activeSubjectInfo?.tone || "pembe")
                }
              >
                {activeSubjectInfo?.icon}
              </span>
              {activeSubjectInfo?.name}
            </h2>
            <span className="pill is-mint">{getTasksBySubject(activeSubject).length} görev</span>
          </div>

          {getTasksBySubject(activeSubject).length === 0 ? (
            <div className="empty-panel">
              <p className="muted-text">Bu derste henüz pekiştirme görevi yok.</p>
              <p className="muted-text" style={{ marginTop: 4 }}>
                Günlük · haftalık · aylık değerlendirmelerde 3+ yanlış yapıldığında görevler burada oluşur.
              </p>
            </div>
          ) : (
            getTasksBySubject(activeSubject).map((task: any) => (
              <article key={task.id} className={"task-card " + task.status}>
                <div className="task-header">
                  <div className="task-info">
                    <h3>{task.topic}</h3>
                    <div className="task-meta">
                      <span>{task.unitName ? "Ünite " + task.unitName : "Genel"}</span>
                      {sourcePill(task.source)}
                      {statusPill(task.status)}
                      <span
                        className="task-wrong"
                        style={{ color: "var(--metin-soluk)", fontSize: 12 }}
                      >
                        {task.wrongCount} yanlış → tetiklendi
                      </span>
                    </div>
                  </div>
                  <div className="task-actions">
                    {task.status === "bekliyor" && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleStartTask(task)}
                      >
                        {task.questionIds.length > 0 ? "Devam Et" : "Başla"}
                      </button>
                    )}
                    {task.status === "devam-ediyor" && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleStartTask(task)}
                      >
                        Çözmeye Devam Et
                      </button>
                    )}
                    {task.status === "tamamlandi" && (
                      <span className="btn btn-soft btn-sm" style={{ cursor: "default" }}>
                        ✓ Tamamlandı
                      </span>
                    )}
                  </div>
                </div>

                {task.status !== "bekliyor" && task.questionIds.length > 0 && (
                  <div className="task-questions">
                    {task.questionIds.map((qid: string, idx: number) => (
                      <QuestionMini
                        key={qid}
                        qid={qid}
                        idx={idx}
                        task={task}
                        question={questionBank[qid]}
                        open={openQid === qid}
                        onAnswer={(letter) => handleAnswer(task.id, qid, letter)}
                        onNext={() => handleNextQuestion(task, qid)}
                        onReport={() => reportQuestion(questionBank[qid])}
                        reported={reportedIds.has(qid)}
                        onZoom={(src) => setZoomSrc(src)}
                      />
                    ))}
                  </div>
                )}
              </article>
            ))
          )}
        </section>
      ) : (
        <div className="empty-panel" style={{ textAlign: "center", padding: 40 }}>
          <p className="muted-text">
            Yukarıdan bir ders seçerek pekiştirme görevlerini görüntüleyin.
          </p>
        </div>
      )}
      {zoomSrc && (
        <div className="zoom-overlay" onClick={() => setZoomSrc(null)} role="button" aria-label="Görseli kapat">
          <img src={zoomSrc} alt="Pekiştirme sorusu — büyütülmüş" />
        </div>
      )}
    </div>
  );
}
