import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { demoExamResults, demoExamSubjects, errorSummary, examPlan, subjects } from "../../data/content";
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

const latestDemoExam = demoExamResults[demoExamResults.length - 1];
const demoTargetScore = 495.2;
const formatExamNumber = (value: number, digits = 2) =>
  new Intl.NumberFormat("tr-TR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);

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

      <section className="exam-results" aria-labelledby="latest-result-title">
        <div className="exam-results-heading">
          <div>
            <span className="eyebrow">Deneme sonrası</span>
            <h2 id="latest-result-title">LGS deneme analizin</h2>
            <p>Netlerini, puan tahminini ve hedefe olan mesafeni birlikte takip et.</p>
          </div>
          <span className="exam-demo-badge"><span aria-hidden="true">●</span> Örnek görünüm</span>
        </div>

        <div className="exam-result-identity">
          <b>Genel deneme · 5. deneme</b>
          <span>Bu alandaki değerler arayüz örneğidir; henüz kişisel deneme kaydına bağlı değildir.</span>
        </div>

        <div className="exam-result-metrics">
          <article className="exam-metric is-score">
            <small>Tahmini LGS puanı</small>
            <strong>{formatExamNumber(latestDemoExam.score)} <span>/ 500</span></strong>
            <p>MEB resmî puanı değildir.</p>
          </article>
          <article className="exam-metric is-net">
            <small>Toplam net</small>
            <strong>{formatExamNumber(latestDemoExam.net)} <span>/ 90 net</span></strong>
            <p>Sözel 44,67 · Sayısal 29,33</p>
          </article>
          <article className="exam-metric is-rank">
            <small>Tahmini başarı dilimi</small>
            <strong>İlk %{formatExamNumber(latestDemoExam.percentile)}</strong>
            <p>Kesin sıralama için ülke geneli sonuç gerekir.</p>
          </article>
          <article className="exam-metric is-target">
            <small>Örnek hedefe kalan</small>
            <strong>{formatExamNumber(demoTargetScore - latestDemoExam.score, 1)} <span>puan</span></strong>
            <p>Örnek hedef puan: {formatExamNumber(demoTargetScore, 1)}</p>
          </article>
        </div>

        <div className="exam-results-detail">
          <article className="card exam-trend-card">
            <div className="section-head">
              <div>
                <h3>Denemelerde net gelişimi</h3>
                <p>Son 5 örnek deneme · 90 soru üzerinden</p>
              </div>
              <span className="pill is-mint">+{formatExamNumber(latestDemoExam.net - demoExamResults[0].net)} net</span>
            </div>
            <div className="chart exam-trend" role="img" aria-label="Beş örnek denemedeki net gelişimi: 62,33 netten 74 nete yükseliş">
              <div className="chart-bars exam-trend-bars">
                {demoExamResults.map((exam, index) => (
                  <div className={`chart-col${index === demoExamResults.length - 1 ? " is-best" : ""}`} key={exam.label} title={`${exam.label}: ${exam.net.toFixed(2)} net`}>
                    <small className="exam-net-value">{formatExamNumber(exam.net, 1)}</small>
                    <i style={{ height: `${(exam.net / 90) * 100}%` }} />
                    <span>{exam.label}</span>
                  </div>
                ))}
              </div>
              <div className="chart-legend"><span>Net</span><span>Her doğru 1 net · 3 yanlış 1 doğruyu götürür</span></div>
            </div>
          </article>

          <article className="card exam-subject-card">
            <div className="section-head">
              <div>
                <h3>Ders ders netlerin</h3>
                <p>Örnek son deneme dağılımı</p>
              </div>
            </div>
            <div className="exam-subject-list">
              {demoExamSubjects.map((subject) => (
                <div className="exam-subject-row" key={subject.name}>
                  <span>{subject.name}</span>
                  <b>{formatExamNumber(subject.net)} <small>/ {subject.total}</small></b>
                  <span className="exam-subject-track" aria-hidden="true"><i style={{ width: `${(subject.net / subject.total) * 100}%` }} /></span>
                </div>
              ))}
            </div>
          </article>
        </div>
        <p className="exam-results-note" role="note">
          Net hesabı: doğru − yanlış / 3. Puan ve yüzdelik dilim yalnızca örnek simülasyondur; resmî MEB sonucu veya gerçek başarı sıralaması değildir.
        </p>
      </section>

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
