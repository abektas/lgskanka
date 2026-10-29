import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../components/icons";
import { GameRightsCard } from "../components/dashboard-widgets";
import { CycleCard } from "../components/cycle-card";
import { Greeting } from "../components/greeting";
import { HeroArt } from "../components/hero-art";
import { StudyTimer } from "../components/study-timer";
import { TaskList } from "../components/task-list";
import {
  errorSummary,
  errorTypes,
  subjects,
  weeklyProgress,
} from "../data/content";
import { learner } from "../data/nav";

export const metadata: Metadata = {
  title: { absolute: "LGS KANKA — 8. sınıf için kişisel çalışma arkadaşı" },
  description:
    "Günlük görevler, 12 aylık deneme takvimi, haftalık testler, ders bazlı ilerleme ve H1–H7 hata analizi tek ekranda. 8. sınıf öğrencileri için LGS çalışma paneli.",
  alternates: { canonical: "/" },
};

/** Hata türlerinin paylarından pasta grafiği üretir. */
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

export default function HomePage() {
  const topErrors = [...errorTypes].sort((a, b) => b.share - a.share).slice(0, 4);

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

      <section className="grid-2" aria-labelledby="bugunun-gorevleri">
        <div className="stack">
          <article className="card hero">
            <HeroArt />
            <div className="hero-tasks">
              <div className="section-head">
                <h2 id="bugunun-gorevleri">Bugünün görevleri</h2>
                <Link className="text-link" href="/calis">
                  Tümünü gör <Icon name="arrow" size={14} />
                </Link>
              </div>
              <TaskList />
            </div>
          </article>

          <section aria-labelledby="derslerim">
            <div className="section-head">
              <h2 id="derslerim">Derslerim</h2>
            </div>
            <div className="subjects-grid">
              {subjects.map((subject) => (
                <article className="subject-card" key={subject.slug}>
                  <div className="subject-top">
                    <span className={`subject-ico tone-bg-${subject.tone}`} aria-hidden="true">
                      {subject.icon}
                    </span>
                    {subject.name}
                  </div>
                  <div className="subject-score">
                    <b>%{subject.score}</b>
                    <span className={`delta${subject.delta < 0 ? " is-down" : ""}`}>
                      {subject.delta > 0 ? `+${subject.delta}` : subject.delta} puan
                    </span>
                  </div>
                  <div
                    className={`bar tone-${subject.tone}`}
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={subject.score}
                    aria-label={`${subject.name} başarısı`}
                  >
                    <i style={{ width: `${subject.score}%` }} />
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        <div className="stack">
          <StudyTimer />

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
              <span>1. Hafta %{weeklyProgress[0].value}</span>
              <span>
                Bu hafta %{weeklyProgress[weeklyProgress.length - 1].value}{" "}
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
            <div className="donut" style={{ background: donutBackground() }} aria-hidden="true">
              <div className="donut-center">
                {errorSummary.total}
                <small>toplam hata</small>
              </div>
            </div>
            <ul className="error-list">
              {topErrors.map((error) => (
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

      <section className="card mission-bar" aria-labelledby="haftalik-hedef">
        <span className="mission-emoji" aria-hidden="true">
          🎯
        </span>
        <div>
          <b id="haftalik-hedef">
            Haftalık hedef: {learner.solvedThisWeek} / {learner.weeklyGoal} soru
          </b>
          <small>
            {learner.weeklyGoal - learner.solvedThisWeek} soru kaldı · günde ortalama 4 soru yeterli
          </small>
          <div
            className="bar"
            style={{ marginTop: 10 }}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={learner.weeklyGoal}
            aria-valuenow={learner.solvedThisWeek}
            aria-label="Haftalık hedef ilerlemesi"
          >
            <i style={{ width: `${Math.round((learner.solvedThisWeek / learner.weeklyGoal) * 100)}%` }} />
          </div>
        </div>
        <Link className="btn btn-soft" href="/calis">
          Devam et
        </Link>
      </section>

      <section aria-label="Kazanımlarım">
        <div className="mini-grid">
          <div className="mini-card">
            <span className="mini-emoji" aria-hidden="true">
              🔥
            </span>
            <span>
              {learner.streakDays} günlük çalışma serisi
              <small>Yarın devam et, rozeti koru</small>
            </span>
          </div>
          <div className="mini-card">
            <span className="mini-emoji" aria-hidden="true">
              🏆
            </span>
            <span>
              {learner.badgeCount} rozet kazandın
              <small>2 rozet için çok yakınsın</small>
            </span>
          </div>
          <Link className="mini-card" href="/oduller" style={{ padding: 0 }}>
            <GameRightsCard />
          </Link>
          <Link className="mini-card" href="/profil">
            <span className="mini-emoji" aria-hidden="true">
              🪑
            </span>
            <span>
              Çalışma odası · {learner.roomItems} eşya
              <small>Yeni eşyalar aç</small>
            </span>
          </Link>
        </div>
      </section>
    </div>
  );
}
