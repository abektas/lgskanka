"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { ScoreCounts } from "../../components/score-counts";
import { CycleBadge } from "../../components/cycle-badge";
import { errorTypes } from "../../data/content";
import { ERROR_REASON_OPTIONS, loadAnswerRecords, saveAnswerRecord } from "../../lib/error-reason";
import { apiFetch } from "../../lib/sync";
import { computeUnitMasteries, formatDueLabel, subjectName } from "../../lib/mastery";
import {
  CATEGORY_LABELS,
  SUBJECT_QUOTA,
  composeWeeklyTest,
  type TestCategory,
  type TestItem,
} from "../../lib/weekly-test";
import {
  loadWeeklyTestHistory,
  saveWeeklyTestRecord,
  recentWeeklyTests,
  weeklyTestAverage,
  weeklyTestDelta,
  type WeeklyTestRecord,
} from "../../lib/weekly-test-history";
import { syncReinforcementTasks } from "../../lib/reinforcement";
import {
  isWeeklyTestOpen,
  levelTestCompletedAt,
  upcomingWeeklyTestSaturday,
  computeCycleState,
} from "../../lib/cycle";

const SUBJECT_SLUGS = Object.keys(SUBJECT_QUOTA);

type QuestionResult = { id: string; subject: string; category: TestCategory; correct: boolean };

export default function HaftalikTestPage() {
  const [items, setItems] = useState<TestItem[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [checkState, setCheckState] = useState<"pending" | "correct" | "wrong" | null>(null);
  const [errorReason, setErrorReason] = useState<string | null>(null);
  const [results, setResults] = useState<QuestionResult[]>([]);
  const [finished, setFinished] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [savedRecord, setSavedRecord] = useState<WeeklyTestRecord | null>(null);
  const [pastRecords, setPastRecords] = useState<WeeklyTestRecord[]>([]);
  const questionStartRef = useRef<number>(Date.now());
  const [reportedIds, setReportedIds] = useState<Set<string>>(new Set());

  // Haftalık test açılış kapısı — seviye tespit + cumartesi kontrolü
  const [gateOpen, setGateOpen] = useState<{
    open: boolean;
    reason: "level" | "date" | "week4" | null;
    nextSaturday: Date | null;
  } | null>(null);

  useEffect(() => {
    const doneAt = levelTestCompletedAt();
    const nextSat = upcomingWeeklyTestSaturday();
    const open = isWeeklyTestOpen();
    let reason: "level" | "date" | "week4" | null = null;
    if (!open) {
      if (!levelTestCompletedAt()) reason = "level";
      else if (new Date().getDay() !== 6) reason = "date";
      else if (computeCycleState(new Date()).weekendTest !== "haftalik") reason = "week4";
    }
    setGateOpen({ open, reason, nextSaturday: nextSat });
  }, []);

  // Bu hafta test zaten bitmişse (yerel kayıt) — soruları açma, sonucu göster
  useEffect(() => {
    if (!isWeeklyTestOpen()) return;
    const history = loadWeeklyTestHistory();
    if (history.length === 0) return;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    // Bu haftanın cumartesini bul
    const day = today.getDay();
    const thisSaturday = new Date(today);
    thisSaturday.setDate(today.getDate() + (day === 6 ? 0 : (6 - day)));
    thisSaturday.setHours(0, 0, 0, 0);
    // Bu cumartesi tarihine eşit kayıt var mı?
    const thisWeekRecord = history.find((r) => {
      const recDate = new Date(r.date);
      recDate.setHours(0, 0, 0, 0);
      return recDate.getTime() === thisSaturday.getTime();
    });
    if (thisWeekRecord) {
      setFinished(true);
      setSavedRecord(thisWeekRecord);
      setPastRecords(history.slice(-5).reverse());
    }
  }, []);

  /** "Soru eksik veya bozuk" bildirimi — öğretmen paneline düşer. */
  const reportQuestion = useCallback(
    async (q: { id: string; subject: string; questionNumber: number; imagePath: string }) => {
      if (reportedIds.has(q.id)) return;
      setReportedIds((prev) => new Set(prev).add(q.id));
      try {
        await apiFetch("/api/question-reports", {
          method: "POST",
          body: JSON.stringify({
            source: "haftalik",
            monthName: "Haftalık Test",
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

  // Havuzu çek, kural tabanlı 45 soruluk testi kur (hafta içi yapamadıklarından)
  useEffect(() => {
    // Kapalıysa veya henüz karar yoksa veri çekmeyi atla
    if (!gateOpen || !gateOpen.open) return;

    let cancelled = false;
    Promise.all(
      SUBJECT_SLUGS.map((s) =>
        fetch(`/api/study?subject=${s}&limit=100`)
          .then((r) => r.json())
          .then((d) =>
            ((d.items || []) as Array<Record<string, unknown>>).map((q) => ({
              id: String(q.id),
              subject: String(q.subject),
              unit: (q.unit as number | null) ?? null,
              unitName: (q.unitName as string | null) ?? null,
              topic: (q.topic as string | null) ?? null,
              questionNumber: Number(q.questionNumber) || 0,
              imagePath: String(q.imagePath),
            }))
          )
      )
    )
      .then((batches) => {
        if (cancelled) return;
        const pool = batches.flat();
        const composed = composeWeeklyTest(pool, computeUnitMasteries(), loadAnswerRecords());
        setItems(composed);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [gateOpen]);

  // Soru değişince süre sayacı sıfırlanır
  useEffect(() => {
    questionStartRef.current = Date.now();
  }, [idx, finished]);

  const current = items ? items[idx] : null;

  const handleAnswer = (letter: string) => {
    if (!current || checkState) return;
    setSelected(letter);
    setCheckState("pending");
    setErrorReason(null);
    const q = current.question;
    const startedAt = questionStartRef.current;
    apiFetch("/api/study", {
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
        setResults((prev) => [
          ...prev,
          { id: q.id, subject: q.subject, category: current.category, correct: data.correct },
        ]);
        if (data.correct) {
          saveAnswerRecord({
            questionId: q.id,
            source: "haftalik",
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

  // Yanlışta öz-değerlendirme → H kodu (plan §7, AI'sız)
  const selectErrorReason = (code: string | null) => {
    setErrorReason(code ?? "SKIPPED");
    const q = current?.question;
    if (!q || !selected) return;
    saveAnswerRecord({
      questionId: q.id,
      source: "haftalik",
      subject: q.subject,
      unit: q.unit,
      unitName: q.unitName,
      topic: q.topic,
      selectedAnswer: selected,
      correct: false,
      errorReasonCode: code,
      timeSpentSec: Math.max(0, Math.round((Date.now() - questionStartRef.current) / 1000)),
      createdAt: new Date().toISOString(),
    });
  };

  const next = () => {
    if (!items) return;
    if (idx < items.length - 1) {
      setIdx(idx + 1);
      setSelected(null);
      setCheckState(null);
      setErrorReason(null);
    } else {
      // Test bitti → kalıcı kaydet + pekiştirme görevlerini senkronize et
      const correct = results.filter((r) => r.correct).length;
      const wrong = results.length - correct;
      const blank = items.length - results.length;
      const byCat: Record<TestCategory, { total: number; correct: number }> = {
        zayif: { total: 0, correct: 0 },
        yeni: { total: 0, correct: 0 },
        karma: { total: 0, correct: 0 },
      };
      for (const r of results) {
        byCat[r.category].total++;
        if (r.correct) byCat[r.category].correct++;
      }
      const weakUnits = computeUnitMasteries()
        .filter((m) => m.level === "zayıf" || m.level === "gelişiyor" || m.due)
        .map((m) => ({
          subject: m.subject,
          unit: m.unit,
          unitName: m.unitName,
          accuracy: m.accuracy,
          level: m.level,
          due: !!m.due,
        }));
      const record: WeeklyTestRecord = {
        date: new Date().toISOString(),
        total: items.length,
        correct,
        wrong,
        blank,
        byCategory: byCat,
        weakUnits,
        questionIds: items.map((it) => it.question.id),
        wrongQuestionIds: results.filter((r) => !r.correct).map((r) => r.id),
      };
      const updatedHistory = saveWeeklyTestRecord(record);
      setSavedRecord(record);
      setPastRecords(updatedHistory.slice(-5).reverse());
      // Pekiştirme görevlerini güncelle (haftalık kaynaklı 3+ yanlış)
      syncReinforcementTasks();
      setFinished(true);
    }
  };

  if (gateOpen === null) {
    return <div className="page"><div className="exam-loading">Hazırlanıyor...</div></div>;
  }
  if (!gateOpen.open) {
    const nextSat = gateOpen.nextSaturday;
    const nextStr = nextSat ? nextSat.toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long" }) : "belirlenemedi";
    return (
      <div className="page">
        <div className="exam-empty" style={{ textAlign: "center", padding: 40 }}>
          {gateOpen.reason === "level" ? (
            <>
              <h2>Önce Seviye Tespit Sınavı'nı Tamamla</h2>
              <p className="muted-text" style={{ margin: "12px 0 24px" }}>
                Sonuçlar çalışma planını ve haftalık testleri şekillendirecek.
              </p>
              <Link className="btn btn-primary" href="/aylik-denemeler?month=0">
                Seviye Tespit Sınavına Başla <Icon name="arrow" size={18} />
              </Link>
            </>
          ) : gateOpen.reason === "week4" ? (
            <>
              <h2>Bu Hafta Aylık Deneme Haftası</h2>
              <p className="muted-text" style={{ margin: "12px 0 24px" }}>
                4. hafta aylık deneme haftasıdır. Haftalık test bir sonraki haftaya bırakılır.
              </p>
            </>
          ) : (
            <>
              <h2>Haftalık Test {nextStr} Açılır</h2>
              <p className="muted-text" style={{ margin: "12px 0 24px" }}>
                Bugün günlük çalışmana devam edebilirsin.
              </p>
              <Link className="btn btn-soft" href="/calis">Günlük Çalışmaya Git</Link>
            </>
          )}
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="page">
        <div className="exam-empty">Test verisi şu anda yüklenemedi.</div>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="page">
        <div className="exam-loading">Haftalık test hazırlanıyor...</div>
      </div>
    );
  }

  if (finished) {
    // savedRecord'dan (geçmişten yüklendi) veya results'tan (bu oturum) istatistikleri al
    let correct = 0;
    let wrong = 0;
    let blank = 0;
    let total = 0;
    let byCat = (cat: TestCategory) => ({ total: 0, correct: 0 });
    let delta = 0;
    let avg5 = 0;

    if (results.length > 0) {
      correct = results.filter((r) => r.correct).length;
      wrong = results.length - correct;
      total = items?.length ?? results.length;
      blank = total - results.length;
      byCat = (cat: TestCategory) => {
        const list = results.filter((r) => r.category === cat);
        return { total: list.length, correct: list.filter((r) => r.correct).length };
      };
    } else if (savedRecord) {
      correct = savedRecord.correct;
      wrong = savedRecord.wrong;
      blank = savedRecord.blank;
      total = savedRecord.total;
      byCat = (cat: TestCategory) => {
        const v = savedRecord.byCategory[cat];
        return { total: v?.total ?? 0, correct: v?.correct ?? 0 };
      };
    }
    delta = weeklyTestDelta();
    avg5 = weeklyTestAverage(5);
    const weak = computeUnitMasteries().filter((m) => m.level === "zayıf" || m.level === "gelişiyor" || m.due);

    return (
      <div className="page">
        <header className="page-head">
          <div>
            <span className="eyebrow">Haftalık test</span>
            <h1>Test Sonucu</h1>
            <p>
              <ScoreCounts correct={correct} wrong={wrong} blank={blank} total={total} />
              {delta !== 0 && (
                <span style={{ marginLeft: 12, color: delta > 0 ? "var(--mint)" : "var(--kirmizi)" }}>
                  {delta > 0 ? "▲" : "▼"} {delta > 0 ? "+" : ""}{delta} puan (bir önceki teste göre)
                </span>
              )}
            </p>
          </div>
          <Link className="btn btn-primary" href="/pekistirme">
            Pekiştirme sorularına geç <Icon name="arrow" size={18} />
          </Link>
        </header>

        <section className="summary-actions" aria-label="Sonraki adımlar">
          <Link className="btn btn-soft" href="/calis">Zayıf konulara çalış</Link>
          <Link className="btn btn-soft" href="/sonuclar">Ayrıntılı analiz</Link>
          <Link className="btn btn-soft" href="/sonuclar">İlerlemesini Gör</Link>
        </section>

        <section className="grid-half" aria-label="Kategori dökümü">
          <article className="card">
            <h2>Kategori dökümü</h2>
            <div className="analysis-table">
              {(["zayif", "yeni", "karma"] as const).map((cat) => {
                const c = byCat(cat);
                return (
                  <div className="analysis-row" key={cat}>
                    <span>{CATEGORY_LABELS[cat]}</span>
                    <span className="bar" aria-hidden="true">
                      <i style={{ width: `${c.total ? (c.correct / c.total) * 100 : 0}%` }} />
                    </span>
                    <em>
                      <ScoreCounts correct={c.correct} wrong={c.total - c.correct} blank={null} total={c.total} />
                    </em>
                  </div>
                );
              })}
            </div>
          </article>
          <article className="card">
            <h2>Tekrar zamanı gelen üniteler</h2>
            {weak.length === 0 ? (
              <p className="muted-text">Şu an tekrar zamanı gelen ünite yok.</p>
            ) : (
              <ul className="mastery-list">
                {weak.slice(0, 6).map((m) => (
                  <li key={`${m.subject}-${m.unit ?? "x"}`}>
                    <span>
                      <b>{subjectName(m.subject)}</b>
                      {m.unitName ? <small> · {m.unitName}</small> : null}
                    </span>
                    <small>
                      %{m.accuracy} · {m.level} · tekrar: {formatDueLabel(m.nextReviewAt)}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </article>
        </section>

        {pastRecords.length > 0 && (
          <section className="card" aria-label="Geçmiş haftalık testler">
            <div className="section-head">
              <h2>Geçmiş haftalık testler</h2>
              <span className="pill is-mint">Son {pastRecords.length} test · ort. %{avg5}</span>
            </div>
            <div className="analysis-table">
              {pastRecords.map((r) => {
                const pct = r.total > 0 ? Math.round((r.correct / r.total) * 100) : 0;
                return (
                  <div className="analysis-row" key={r.date}>
                    <span>{new Date(r.date).toLocaleDateString("tr-TR", { day: "2-digit", month: "long" })}</span>
                    <span className="bar" aria-hidden="true">
                      <i style={{ width: `${pct}%` }} />
                    </span>
                    <em>
                      {pct}% · <ScoreCounts correct={r.correct} wrong={r.wrong} blank={r.blank} total={r.total} />
                    </em>
                  </div>
                );
              })}
            </div>
            <p className="muted-text" style={{ marginTop: 12 }}>
              Geçmiş testler tarayıcıda saklanır. Zayıf konular her testte otomatik olarak
              pekiştirme listesine eklenir.
            </p>
          </section>
        )}

        <section className="card empty-state" aria-label="Tavsiye">
          <h3>📌 Bu testten çıkarman gereken</h3>
          <p className="muted-text">
            {wrong > 0
              ? `${wrong} yanlış yaptın. Bu konularda 3+ yanlış varsa otomatik pekiştirme görevi oluştu. /pekistirme sayfasından çalış.`
              : "Tebrikler! Bu testte yanlışın yok. Zayıf üniteler için tekrar zamanlamasına devam et."}
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Haftalık test</span>
          <h1>
            Soru {idx + 1} / {items.length}
          </h1>
          <p>
            {items[idx].question.subject && subjectName(items[idx].question.subject)}
            {items[idx].question.unitName ? ` · ${items[idx].question.unitName}` : ""} ·{" "}
            {CATEGORY_LABELS[items[idx].category]}
          </p>
        </div>
      </header>

      <CycleBadge variant="haftalik" />

      <section className="exam-question" id="sorular">
        <div className="exam-question-image">
          <img
            src={current!.question.imagePath}
            alt={`Haftalık test soru ${idx + 1}`}
            loading="eager"
            onClick={() => setZoomOpen(true)}
          />
        </div>
        <p className="exam-image-hint">Görseli büyütmek için tıkla</p>

        <div className="exam-report-row">
          <button
            type="button"
            className={`exam-report-btn ${reportedIds.has(current!.question.id) ? "is-done" : ""}`}
            onClick={() => reportQuestion(current!.question)}
            disabled={reportedIds.has(current!.question.id)}
          >
            {reportedIds.has(current!.question.id)
              ? "✓ Öğretmene bildirildi"
              : "⚠ Soru eksik veya bozuk"}
          </button>
        </div>

        <div className="exam-answers">
          {["A", "B", "C", "D"].map((letter) => (
            <button
              key={letter}
              className={`exam-answer-btn ${selected === letter ? "selected" : ""} ${checkState ? "disabled" : ""}`}
              onClick={() => handleAnswer(letter)}
              disabled={!!checkState}
            >
              {letter}
            </button>
          ))}
        </div>

        {checkState && (
          <div className="exam-result">
            <p>
              Cevabın: <b>{selected}</b>
              {checkState === "correct" && <span className="correct"> ✓ Doğru</span>}
              {checkState === "wrong" && <span className="wrong"> ✗ Yanlış</span>}
            </p>
            {checkState === "wrong" && errorReason === null && (
              <div className="error-reason">
                <p className="muted-text">Yanlışını anlamamıza yardım et — sana en yakın olanı seç:</p>
                <div className="error-reason-options">
                  {ERROR_REASON_OPTIONS.map((opt) => (
                    <button key={opt.id} className="btn btn-soft" onClick={() => selectErrorReason(opt.code)}>
                      {opt.label}
                    </button>
                  ))}
                  <button className="btn btn-soft" onClick={() => selectErrorReason(null)}>
                    Geç
                  </button>
                </div>
              </div>
            )}
            {errorReason && errorReason !== "SKIPPED" && (
              <div className="error-reason-result">
                <b>
                  {errorReason} · {errorTypes.find((e) => e.code === errorReason)?.name}
                </b>
                <p className="muted-text">{errorTypes.find((e) => e.code === errorReason)?.advice}</p>
              </div>
            )}
          </div>
        )}

        {checkState && (
          <button className="btn btn-soft" onClick={next}>
            {idx < items.length - 1 ? "Sonraki soru" : "Testi bitir"} <Icon name="arrow" size={16} />
          </button>
        )}
      </section>

      {zoomOpen && current && (
        <div className="zoom-overlay" onClick={() => setZoomOpen(false)} role="button" aria-label="Görseli kapat">
          <img src={current.question.imagePath} alt={`Haftalık test soru ${idx + 1} — büyütülmüş`} />
        </div>
      )}
    </div>
  );
}