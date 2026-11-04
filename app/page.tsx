"use client";

import Link from "next/link";
import { Icon } from "../components/icons";
import { GameRightsCard } from "../components/dashboard-widgets";
import { CycleCard } from "../components/cycle-card";
import { Greeting } from "../components/greeting";
import { ContinueCard } from "../components/continue-card";
import { ScoreCounts } from "../components/score-counts";
import { subjects } from "../data/content";
import { errorTypes } from "../data/content";
import { gameEconomy } from "../data/nav";
import { useLearnerStats } from "../lib/learner-stats";
import { computeErrorBreakdown, computeSubjectAccuracy } from "../lib/results-analytics";
import { loadAnswerRecords } from "../lib/error-reason";

/** Hata türlerinin paylarından pasta grafiği üretir (gerçek veriden). */
function donutBackground(breakdown: Array<{ code: string; count: number; share: number }>) {
  const total = breakdown.reduce((sum, item) => sum + item.count, 0);
  let acc = 0;
  const stops = breakdown.map((item) => {
    const from = (acc / total) * 100;
    acc += item.count;
    const to = (acc / total) * 100;
    const meta = errorTypes.find((e) => e.code === item.code);
    return `${meta?.color ?? "#888"} ${from.toFixed(2)}% ${to.toFixed(2)}%`;
  });
  return `conic-gradient(${stops.join(", ")})`;
}

export default function HomePage() {
  const stats = useLearnerStats();
  const records = loadAnswerRecords();
  const topErrors = (stats?.errorBreakdown ?? [])
    .slice()
    .sort((a, b) => b.count - a.count)
    .slice(0, 4);
  const weeklyProgress = stats?.weeklyProgress ?? [];
  const badgeCount = stats?.badgeCount ?? 0;
  const streakDays = stats?.streakDays ?? 0;
  const subjectAccuracy = new Map(computeSubjectAccuracy(records).map((item) => [item.subject, item]));

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Bugünün planı</span>
          <h1>
            Merhaba <Greeting /> 👋
          </h1>
          <p>
            Bugün hedeflerine birlikte devam edelim. Türkçe, Matematik, Fen 5'er; İngilizce,
            İnkılap, Din 3'er — toplam 24 soru, sonra hata analizi.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Çalışmaya başla <Icon name="arrow" size={18} />
        </Link>
      </header>

      <ContinueCard />

      <section className="card next-step" aria-labelledby="simdi-ne-yapmaliyim">
        <div className="next-step-head">
          <div>
            <span className="eyebrow">En önemli soru</span>
            <h2 id="simdi-ne-yapmaliyim">Şimdi ne yapmalıyım?</h2>
          </div>
          <Link className="btn btn-primary" href="/calis">
            Planı başlat <Icon name="arrow" size={18} />
          </Link>
        </div>
        <ol className="next-step-list">
          <li>
            <span className="topic-index" aria-hidden="true">
              1
            </span>
            Günlük alıştırma: Türkçe, Matematik, Fen 5'er; İngilizce, İnkılap, Din 3'er = 24 soru
            <span className="step-xp">+10 XP</span>
          </li>
          <li>
            <span className="topic-index" aria-hidden="true">
              2
            </span>
            Yanlışların H türünü seç (H1–H7 hata analizi)
            <span className="step-xp">+5 XP</span>
          </li>
          <li>
            <span className="topic-index" aria-hidden="true">
              3
            </span>
            Pekiştirme sayfasından zayıf konularda 5 soruluk mini çalışma
            <span className="step-xp">+15 XP</span>
          </li>
          <li>
            <span className="topic-index" aria-hidden="true">
              4
            </span>
            Hafta sonu (cumartesi): 45 soruluk haftalık test (Tr 10, Mat 10, Fen 10, İnk 5, Din 5, Eng 5)
            <span className="step-xp">+30 XP</span>
          </li>
        </ol>
        <p className="muted-text" style={{ fontSize: 12.5 }}>
          Plan yaklaşık 40 dakika sürer. Uzun görünüyorsa sadece 1. adımı yap: küçük başlangıç da
          seriyi korur.
        </p>
      </section>

      <section className="grid-2" aria-label="Derslerim ve çalışma döngüsü">
        <div className="stack">
          <section aria-labelledby="derslerim">
            <div className="section-head">
              <h2 id="derslerim">Derslerim</h2>
            </div>
            <div className="subjects-grid">
              {subjects.map((subject) => (
                <article className="subject-card" key={subject.slug}>
                  <div className="subject-top">
                    <div className={`subject-ico tone-bg-${subject.tone}`} aria-hidden="true">
                      {subject.icon}
                    </div>
                    {subject.name}
                  </div>
                  <div className="subject-score">
                    {subjectAccuracy.has(subject.slug) ? (
                      <>
                        <b>%{subjectAccuracy.get(subject.slug)!.accuracy}</b>
                        <ScoreCounts
                          correct={subjectAccuracy.get(subject.slug)!.correct}
                          wrong={subjectAccuracy.get(subject.slug)!.total - subjectAccuracy.get(subject.slug)!.correct}
                          blank={null}
                          total={subjectAccuracy.get(subject.slug)!.total}
                        />
                      </>
                    ) : (
                      <>
                        <b>—</b>
                        <span className="muted-text">Henüz yanıt yok</span>
                      </>
                    )}
                  </div>
                  <div
                    className={`bar tone-${subject.tone}`}
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={subjectAccuracy.get(subject.slug)?.accuracy ?? 0}
                    aria-label={`${subject.name} başarısı`}
                  >
                    <i style={{ width: `${subjectAccuracy.get(subject.slug)?.accuracy ?? 0}%` }} />
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        <div className="stack">
          <CycleCard />
        </div>
      </section>

      <section className="grid-half" aria-label="İlerleme ve hata analizi">
        <article className="card">
          <div className="section-head">
            <h2>İlerleme grafiği</h2>
            <span className="pill is-mint">Son 5 hafta · +21 puan</span>
          </div>
          <div className="chart">
            <div className="chart-bars" role="img" aria-label="Son 5 haftanın başarı yüzdeleri">
              {weeklyProgress.map((week, index) => (
                <div
                  className={`chart-col${index === weeklyProgress.length - 1 ? " is-best" : ""}`}
                  key={week.label}
                >
                  <i style={{ height: `${week.value}%` }} />
                  <span>{week.label.replace(" Hafta", ".")}</span>
                </div>
              ))}
            </div>
            <div className="chart-legend">
              <span>1. Hafta %{weeklyProgress[0]?.value ?? 0}</span>
              <span>
                Bu hafta %{weeklyProgress[weeklyProgress.length - 1]?.value ?? 0}{" "}
                <strong>(en yüksek)</strong>
              </span>
            </div>
          </div>
        </article>

        <article className="card">
          <div className="section-head">
            <h2>Hata analizi özeti</h2>
            <Link className="text-link" href="/sonuclar">
              Detay <Icon name="arrow" size={14} />
            </Link>
          </div>
          <div className="donut-wrap">
            <div className="donut" style={{ background: donutBackground(stats?.errorBreakdown ?? []) }} aria-hidden="true">
              <div className="donut-center">
                {stats?.totalSolved ?? 0}
                <small>toplam çözülen</small>
              </div>
            </div>
            <ul className="error-list">
              {(stats?.errorBreakdown ?? [])
                .slice()
                .sort((a, b) => b.count - a.count)
                .slice(0, 4)
                .map((error) => {
                  const meta = errorTypes.find((e) => e.code === error.code);
                  return (
                    <li key={error.code}>
                      <span className="error-dot" style={{ background: meta?.color ?? "#888" }} aria-hidden="true" />
                      {error.code} · {meta?.name ?? error.code}
                      <b>%{error.share}</b>
                    </li>
                  );
                })}
            </ul>
          </div>
        </article>
      </section>


      <section aria-label="Kazanımlarım">
        <div className="mini-grid">
          <div className="mini-card">
            <span className="mini-emoji" aria-hidden="true">
              🔥
            </span>
            <span>
              {streakDays} günlük çalışma serisi
              <small>Yarın devam et, rozeti koru</small>
            </span>
          </div>
          <div className="mini-card">
            <span className="mini-emoji" aria-hidden="true">
              🏆
            </span>
            <span>
              {badgeCount} rozet kazandın
              <small>2 rozet için çok yakınsın</small>
            </span>
          </div>
          <Link className="mini-card" href="/oduller" style={{ padding: 0 }}>
            <GameRightsCard />
          </Link>
        </div>
      </section>
    </div>
  );
}