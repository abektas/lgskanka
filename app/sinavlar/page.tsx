import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { errorSummary, examPlan, subjects } from "../../data/content";
import { learner } from "../../data/nav";

export const metadata: Metadata = {
  title: "Sınavlar ve deneme takvimi",
  description:
    "5 haftalık LGS deneme programı: haftalık deneme sınavı takvimi, sözel/sayısal bölüm ayrımı, deneme sonrası hata analizi ve çalışma önerileri.",
  alternates: { canonical: "/sinavlar" },
};

const statusLabels = {
  done: "Tamamlandı",
  active: "Bu hafta",
  upcoming: "Sırada",
} as const;

export default function SinavlarPage() {
  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Deneme programı</span>
          <h1>Sınavlar</h1>
          <p>
            Haftada bir deneme, ardından soru bazında hata analizi. Denemenin amacı not almak değil;
            hangi hata türünün puanını düşürdüğünü görmek.
          </p>
        </div>
        <Link className="btn btn-primary" href="/ilerleme">
          Sonuç analizim <Icon name="arrow" size={18} />
        </Link>
      </header>

      <div className="study-stats">
        <div>
          <small>Bu hafta çözülen soru</small>
          <b>{learner.solvedThisWeek} soru</b>
          <span className="delta">Hedef: 60 soru</span>
        </div>
        <div>
          <small>Toplam çözülen</small>
          <b>{learner.totalSolved} soru</b>
          <span className="muted-text">Son 5 hafta</span>
        </div>
        <div>
          <small>Analiz edilen hata</small>
          <b>{errorSummary.resolved}</b>
          <span className="delta">{errorSummary.total} hatanın %78&apos;i kapatıldı</span>
        </div>
      </div>

      <section aria-labelledby="takvim">
        <div className="section-head">
          <h2 id="takvim">5 haftalık deneme takvimi</h2>
          <span className="pill is-gok">Her hafta sonu, 09:30</span>
        </div>
        <div className="exam-list">
          {examPlan.map((exam) => (
            <article className={`exam-row is-${exam.status}`} key={exam.week}>
              <span className={`status-tag is-${exam.status}`}>{statusLabels[exam.status]}</span>
              <div>
                <b>
                  {exam.week} · {exam.subject}
                </b>
                <small className="muted-text">
                  {exam.date} · 90 dakika · 20 Türkçe, 20 Matematik, 20 Fen, 10 İngilizce
                </small>
              </div>
              {(exam.status === "active" || exam.status === "upcoming") && (
                <Link className="btn btn-soft btn-sm" href="/calis">
                  Hazırlan
                </Link>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="grid-half" aria-label="Deneme sonrası rutin ve ders ağırlıkları">
        <article className="card">
          <h2>Deneme sonrası 30 dakika</h2>
          <ol className="step-list">
            <li>
              <b>Sadece yanlışları değil, boşları da gözden geçir:</b> boş bırakma nedeni çoğu zaman H2
              (yöntem) veya H7 (dikkat/zaman) olur.
            </li>
            <li>
              <b>Her yanlışa H kodu seç:</b> koç öneri sunar, sen onaylarsın. Kodlar doğruysa haftalık
              plan doğru çıkar.
            </li>
            <li>
              <b>En çok tekrar eden koddan başla:</b> tek konu, 15 soru, tek oturum.
            </li>
            <li>
              <b>Yeni denemeye kadar 2 gün ara ver:</b> analizden önce dinlenme, öğrenmeyi pekiştirir.
            </li>
          </ol>
        </article>

        <article className="card">
          <h2>Derslere göre soru ağırlığı</h2>
          <div className="analysis-table">
            {subjects.map((subject) => (
              <div className="analysis-row" key={subject.slug}>
                <span>{subject.name}</span>
                <span className="bar tone-lavanta" aria-hidden="true">
                  <i style={{ width: `${subject.score}%` }} />
                </span>
                <em>%{subject.score}</em>
              </div>
            ))}
          </div>
          <p className="muted-text" style={{ marginTop: 14, fontSize: 12.5 }}>
            Yüzdeler son 5 haftanın deneme sonuçlarından hesaplanır.
          </p>
        </article>
      </section>
    </div>
  );
}
