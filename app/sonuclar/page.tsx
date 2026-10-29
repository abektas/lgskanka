"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { errorTypes } from "../../data/content";
import { MasteryPanel } from "../../components/mastery-widgets";
import { loadAnswerRecords } from "../../lib/error-reason";
import { computeUnitMasteries } from "../../lib/mastery";
import { loadWeeklyTestHistory } from "../../lib/weekly-test-history";
import { loadExamHistory } from "../../lib/exam-history";
import { getAllTasks } from "../../lib/reinforcement";
import {
  computeErrorBreakdown,
  computeMasteryBands,
  computeOverallStats,
  computeSubjectAccuracy,
  computeUnifiedResults,
  computeWeakTopics,
  type UnifiedResult,
  type WeakTopic,
} from "../../lib/results-analytics";

export default function SonuclarPage() {
  const [ready, setReady] = useState(false);
  const [stats, setStats] = useState<ReturnType<typeof computeOverallStats> | null>(null);
  const [breakdown, setBreakdown] = useState<ReturnType<typeof computeErrorBreakdown>>([]);
  const [subjectAcc, setSubjectAcc] = useState<ReturnType<typeof computeSubjectAccuracy>>([]);
  const [weak, setWeak] = useState<WeakTopic[]>([]);
  const [results, setResults] = useState<UnifiedResult[]>([]);
  const [bands, setBands] = useState<ReturnType<typeof computeMasteryBands>>([]);
  const [dueCount, setDueCount] = useState(0);
  const [taskCount, setTaskCount] = useState(0);

  useEffect(() => {
    const records = loadAnswerRecords();
    const exams = loadExamHistory();
    const weekly = loadWeeklyTestHistory();
    setStats(computeOverallStats(records));
    setBreakdown(computeErrorBreakdown(records));
    setSubjectAcc(computeSubjectAccuracy(records));
    setWeak(computeWeakTopics(records, exams, weekly));
    setResults(computeUnifiedResults(exams, weekly));
    const masteries = computeUnitMasteries(records);
    setBands(computeMasteryBands(masteries));
    setDueCount(masteries.filter((m) => m.due).length);
    setTaskCount(getAllTasks().length);
    setReady(true);
  }, []);

  if (!ready || !stats) {
    return (
      <div className="page">
        <div className="exam-loading">Sonuçlar yükleniyor...</div>
      </div>
    );
  }

  const hasData = stats.totalAnswered > 0 || results.length > 0;
  const classifiedPct =
    stats.wrong > 0 ? Math.round((stats.classified / stats.wrong) * 100) : 0;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Öğrenme analizi</span>
          <h1>Sonuçlar ve İlerleme</h1>
          <p>
            Buradaki sayılar not değil, karar aracıdır: hangi konuda zayıfsın, hangi hata türünü
            tekrar ediyorsun ve sıradaki adım ne olmalı?
          </p>
        </div>
        <Link className="btn btn-primary" href="/pekistirme">
          Pekiştirme sorularına geç <Icon name="arrow" size={18} />
        </Link>
      </header>

      {!hasData && (
        <section className="card empty-state">
          <h2>📊 Henüz veri yok</h2>
          <p className="muted-text">
            Günlük çalışma, haftalık test veya aylık deneme çöz. Sonuçlar burada birikir ve
            eksik konuların otomatik olarak pekiştirme listesine aktarılır.
          </p>
          <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
            <Link className="btn btn-primary" href="/calis">
              Günlük Alıştırmaya Başla <Icon name="arrow" size={18} />
            </Link>
            <Link className="btn btn-soft" href="/haftalik-test">
              Haftalık Teste Git
            </Link>
          </div>
        </section>
      )}

      {hasData && (
        <>
          {/* ============ Genel durum ============ */}
          <div className="study-stats">
            <div>
              <small>Genel başarı</small>
              <b>%{stats.accuracy}</b>
              <span className="muted-text">
                {stats.totalCorrect}/{stats.totalAnswered} doğru
              </span>
            </div>
            <div>
              <small>Toplam soru</small>
              <b>{stats.totalAnswered}</b>
              <span className="muted-text">{stats.thisWeek} soru bu hafta</span>
            </div>
            <div>
              <small>Analiz edilen hata</small>
              <b>
                {stats.classified}/{stats.wrong}
              </b>
              <span className="delta">%{classifiedPct}&apos;i sınıflandırıldı</span>
            </div>
            <div>
              <small>Bekleyen görev</small>
              <b>{taskCount}</b>
              <span className="muted-text">{dueCount} ünite tekrar bekliyor</span>
            </div>
          </div>

          {/* ============ Değerlendirme geçmişi ============ */}
          <section className="card" aria-labelledby="sonuclar-gecmis">
            <div className="section-head">
              <h2 id="sonuclar-gecmis">Değerlendirme sonuçları</h2>
              <span className="pill is-mint">{results.length} değerlendirme</span>
            </div>
            {results.length === 0 ? (
              <p className="muted-text">
                Henüz haftalık test veya aylık deneme çözülmedi. İlk testten sonra burada
                karşılaştırmalı geçmiş oluşur.
              </p>
            ) : (
              <div className="analysis-table">
                {results.map((r) => (
                  <div className="analysis-row" key={r.id}>
                    <span>
                      <b>{r.title}</b>{" "}
                      <small>
                        {new Date(r.date).toLocaleDateString("tr-TR", {
                          day: "2-digit",
                          month: "long",
                          year: "numeric",
                        })}
                      </small>
                    </span>
                    <span className="bar" aria-hidden="true">
                      <i style={{ width: `${r.percentage}%` }} />
                    </span>
                    <em>
                      %{r.percentage} · {r.correct}/{r.total}
                    </em>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ============ Zayıf konular ve tekrar ============ */}
          <section className="card" aria-labelledby="zayif-konular">
            <div className="section-head">
              <h2 id="zayif-konular">Zayıf konular ve tekrar</h2>
              <span className="pill is-seftali">{weak.length} konu</span>
            </div>
            {weak.length === 0 ? (
              <p className="muted-text">
                Şu an zayıf konu tespit edilmedi. Test çözdükçe eksik konular burada listelenir.
              </p>
            ) : (
              <div className="eksik-konular">
                {weak.slice(0, 12).map((t) => (
                  <div key={t.key} className="eksik-konu-item">
                    <div>
                      <b>
                        {t.name}
                        {t.topic ? ` · ${t.topic}` : t.unitName ? ` · ${t.unitName}` : ""}
                      </b>
                      <span className="muted-text">
                        {t.wrongCount} yanlış · %{t.accuracy} doğruluk · {t.sources.join(", ")}
                      </span>
                    </div>
                    <Link href="/pekistirme" className="btn btn-soft btn-sm">
                      Tekrar çalış <Icon name="arrow" size={14} />
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ============ Başarı grafiği ============ */}
          {results.length > 1 && (
            <section className="card" aria-labelledby="basari-grafik">
              <div className="section-head">
                <h2 id="basari-grafik">Başarı gelişimi</h2>
                <span className="pill is-mint">Son {Math.min(results.length, 8)} değerlendirme</span>
              </div>
              <div className="chart">
                <div className="chart-bars" role="img" aria-label="Değerlendirme başarı yüzdeleri">
                  {results.slice(0, 8).reverse().map((r, index) => (
                    <div
                      className={`chart-col${index === Math.min(results.length, 8) - 1 ? " is-best" : ""}`}
                      key={r.id}
                    >
                      <i style={{ height: `${r.percentage}%` }} />
                      <span>{r.kind === "aylik" ? `${r.title.split(".")[0]}.` : "Hafta"}</span>
                    </div>
                  ))}
                </div>
                <div className="chart-legend">
                  <span>İlk: %{results[results.length - 1].percentage}</span>
                  <span>Şimdi: %{results[0].percentage}</span>
                </div>
              </div>
            </section>
          )}

          {/* ============ Hata türü dağılımı ============ */}
          <section className="card" aria-labelledby="h-dagilim">
            <div className="section-head">
              <h2 id="h-dagilim">Hata türü dağılımı</h2>
              <span className="pill">Senin öz-değerlendirmen</span>
            </div>
            {stats.classified === 0 ? (
              <p className="muted-text">
                Yanlış yaptığın sorularda hata türünü seçersen burada dağılım oluşur. Şu an{" "}
                {stats.wrong} yanlışın var, hiçbiri sınıflandırılmamış.
              </p>
            ) : (
              <div className="analysis-table">
                {breakdown
                  .filter((b) => b.count > 0)
                  .sort((a, b) => b.count - a.count)
                  .map((b) => {
                    const meta = errorTypes.find((e) => e.code === b.code);
                    return (
                      <div className="error-row" key={b.code}>
                        <div className="error-row-head">
                          <span className="code-tag" style={{ background: meta?.color ?? "var(--pembe)" }}>
                            {b.code}
                          </span>
                          <b>{b.label}</b>
                          <em>
                            {b.count} hata · %{b.share}
                          </em>
                        </div>
                        {meta && <p className="muted-text">{meta.definition}</p>}
                        {meta && (
                          <p className="advice-line">
                            <strong>Çalışma önerisi:</strong> {meta.advice}
                          </p>
                        )}
                        <div
                          className="bar"
                          role="progressbar"
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-valuenow={b.share}
                          aria-label={`${b.code} oranı`}
                        >
                          <i
                            style={{
                              width: `${Math.min(b.share * 2.2, 100)}%`,
                              background: meta?.color ?? "var(--pembe)",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </section>

          {/* ============ Ders bazlı durum ============ */}
          <section className="card" aria-labelledby="ders-durum">
            <div className="section-head">
              <h2 id="ders-durum">Derslere göre durum</h2>
            </div>
            {subjectAcc.length === 0 ? (
              <p className="muted-text">Henüz cevap kaydı yok.</p>
            ) : (
              <div className="analysis-table">
                {subjectAcc.map((s) => (
                  <div className="analysis-row" key={s.subject}>
                    <span>{s.name}</span>
                    <span className="bar" aria-hidden="true">
                      <i style={{ width: `${s.accuracy}%` }} />
                    </span>
                    <em>
                      %{s.accuracy} · {s.correct}/{s.total}
                    </em>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ============ Mastery bantları ============ */}
          <section className="card" aria-labelledby="mastery-bantlari">
            <div className="section-head">
              <h2 id="mastery-bantlari">Mastery bantları</h2>
            </div>
            <ul className="mastery-list">
              {bands.map((b) => (
                <li key={b.level}>
                  <span className={`mastery-band tone-bg-${b.tone}`}>{b.count} ünite</span>
                  <span>
                    <b>{b.label}</b>
                    <small>{b.advice}</small>
                  </span>
                </li>
              ))}
            </ul>
            <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
              Sistem bir konuyu &ldquo;öğrenildi&rdquo; saymadan önce mini test ile doğrular; video
              izlemek tek başına öğrenme kanıtı değildir.
            </p>
          </section>

          {/* ============ Tekrar zamanı gelen üniteler ============ */}
          <MasteryPanel />
        </>
      )}
    </div>
  );
}
