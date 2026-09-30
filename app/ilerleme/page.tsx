import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { errorSummary, errorTypes, subjects, weeklyProgress } from "../../data/content";
import { learner, masteryBands } from "../../data/nav";

export const metadata: Metadata = {
  title: "İlerleme ve hata analizi",
  description:
    "Konu ve kazanım bazında ilerleme, son 5 haftanın başarı grafiği ve H1–H7 hata türü dağılımı. Öğrenciyi etiketlemeden öğrenme kararını iyileştiren analiz.",
  alternates: { canonical: "/ilerleme" },
};

function donutBackground() {
  const total = errorTypes.reduce((sum, item) => sum + item.share, 0);
  let acc = 0;
  const stops = errorTypes.map((item) => {
    const from = (acc / total) * 100;
    acc += item.share;
    const to = (acc / total) * 100;
    return `${item.color} ${from.toFixed(2)}% ${to.toFixed(2)}%`;
  });
  return `conic-gradient(${stops.join(", ")})`;
}

export default function IlerlemePage() {
  const topErrors = [...errorTypes].sort((a, b) => b.share - a.share);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Öğrenme analizi</span>
          <h1>İlerleme</h1>
          <p>
            Buradaki sayılar not değil, karar aracıdır: hangi konuda zayıfsın, hangi hata türü tekrar
            ediyor ve sıradaki adım ne olmalı?
          </p>
        </div>
        <Link className="btn btn-primary" href="/ai-koc">
          Koçun planı <Icon name="arrow" size={18} />
        </Link>
      </header>

      <div className="study-stats">
        <div>
          <small>Genel başarı</small>
          <b>%{weeklyProgress[weeklyProgress.length - 1].value}</b>
          <span className="delta">+{errorSummary.weekDelta} puan (bu hafta)</span>
        </div>
        <div>
          <small>Toplam soru</small>
          <b>{learner.totalSolved}</b>
          <span className="muted-text">{learner.solvedThisWeek} soru bu hafta</span>
        </div>
        <div>
          <small>Analiz edilen hata</small>
          <b>
            {errorSummary.resolved}/{errorSummary.total}
          </b>
          <span className="delta">%78&apos;i kapatıldı</span>
        </div>
      </div>

      <section className="grid-half" aria-label="Grafik ve hata dağılımı">
        <article className="card">
          <div className="section-head">
            <h2>Son 5 haftanın başarısı</h2>
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
              <span>İlk ölçüm %{weeklyProgress[0].value}</span>
              <span>Şimdi %{weeklyProgress[weeklyProgress.length - 1].value}</span>
            </div>
          </div>
        </article>

        <article className="card">
          <h2>Hata türü dağılımı</h2>
          <div className="donut-wrap">
            <div className="donut" style={{ background: donutBackground() }} aria-hidden="true">
              <div className="donut-center">
                {errorSummary.total}
                <small>toplam hata</small>
              </div>
            </div>
            <ul className="error-list">
              {topErrors.slice(0, 4).map((error) => (
                <li key={error.code}>
                  <span className="error-dot" style={{ background: error.color }} aria-hidden="true" />
                  {error.code} · {error.name}
                  <b>%{error.share}</b>
                </li>
              ))}
            </ul>
          </div>
        </article>
      </section>

      <section className="card" aria-labelledby="h-tablosu">
        <div className="section-head">
          <h2 id="h-tablosu">H1–H7 hata türleri ve yapılacaklar</h2>
          <span className="pill">İlk hata noktası yaklaşımı</span>
        </div>
        <div className="analysis-table">
          {topErrors.map((error) => (
            <div className="error-row" key={error.code}>
              <div className="error-row-head">
                <span className="code-tag" style={{ background: error.color }}>
                  {error.code}
                </span>
                <b>{error.name}</b>
                <em>%{error.share}</em>
              </div>
              <p className="muted-text">{error.definition}</p>
              <p className="advice-line">
                <strong>Çalışma önerisi:</strong> {error.advice}
              </p>
              <div
                className="bar"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={error.share}
                aria-label={`${error.code} oranı`}
              >
                <i style={{ width: `${Math.min(error.share * 2.2, 100)}%`, background: error.color }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid-half" aria-label="Ders bazlı durum ve mastery bantları">
        <article className="card">
          <h2>Derslere göre durum</h2>
          <div className="analysis-table">
            {subjects.map((subject) => (
              <div className="analysis-row" key={subject.slug}>
                <span>
                  <span aria-hidden="true">{subject.icon}</span> {subject.name}
                </span>
                <span className={`bar tone-${subject.tone}`} aria-hidden="true">
                  <i style={{ width: `${subject.score}%` }} />
                </span>
                <em>%{subject.score}</em>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h2>Mastery bantları</h2>
          <ul className="mastery-list">
            {masteryBands.map((band) => (
              <li key={band.range}>
                <span className={`mastery-band tone-bg-${band.tone}`}>{band.range}</span>
                <span>
                  <b>{band.label}</b>
                  <small>{band.advice}</small>
                </span>
              </li>
            ))}
          </ul>
          <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
            Sistem bir konuyu &ldquo;öğrenildi&rdquo; saymadan önce mini test ile doğrular; video izlemek
            tek başına öğrenme kanıtı değildir.
          </p>
        </article>
      </section>
    </div>
  );
}
