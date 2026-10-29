"use client";

import Link from "next/link";
import { Icon } from "../../components/icons";
import { GameCenter } from "../../components/game-center";
import { badges } from "../../data/content";
import { learner, xpRules } from "../../data/nav";
import { useBadgeProgress } from "../../components/use-badge-progress";

export function OdullerClient() {
  const nextLevelXp = learner.levelTarget - learner.levelXp;
  const badgeList = useBadgeProgress();
  const earned = badgeList.filter((badge) => badge.earned).length;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Gelişim ve mola</span>
          <h1>Ödüller</h1>
          <p>
            Ödüller doğru cevaptan çok <strong>düzenli çalışma, hata analizi ve gerçek gelişim</strong>{" "}
            davranışlarına bağlanır. Oyunlar çalışma hedefini tamamladıktan sonra ve süre sınırıyla
            açılır.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Görevi tamamla, hak kazan <Icon name="arrow" size={18} />
        </Link>
      </header>

      <div className="reward-grid">
        <article className="reward-card">
          <span className="reward-emoji" aria-hidden="true">
            ⭐
          </span>
          <b>{learner.xp} XP</b>
          <small>
            Bir sonraki seviye için {nextLevelXp} XP kaldı (Seviye {learner.level + 1})
          </small>
          <div
            className="bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={learner.levelTarget}
            aria-valuenow={learner.levelXp}
            aria-label="Seviye ilerlemesi"
          >
            <i style={{ width: `${Math.round((learner.levelXp / learner.levelTarget) * 100)}%` }} />
          </div>
        </article>

        <article className="reward-card">
          <span className="reward-emoji" aria-hidden="true">
            🏆
          </span>
          <b>
            {earned} / {badgeList.length} rozet
          </b>
          <small>Kalan rozetler gerçek davranışlara bağlı: seri, hata çözümü, mastery artışı.</small>
        </article>

        <article className="reward-card">
          <span className="reward-emoji" aria-hidden="true">
            🎮
          </span>
          <b>2 oyun hakkı · 10 dakika</b>
          <small>XP eşine göre açılanır (20 XP → 2 dk, 50 XP → 5 dk). Oyun öğrenmenin
            yerine geçmez.</small>
        </article>

        <article className="reward-card">
          <span className="reward-emoji" aria-hidden="true">
            🪑
          </span>
          <b>Çalışma odası · {learner.roomItems} eşya</b>
          <small>Hata analizi ve mini test başarıları odana yeni eşya ekler.</small>
        </article>
      </div>

      <section className="grid-2" aria-label="XP kuralları ve oyun ekonomisi">
        <article className="card">
          <div className="section-head">
            <h2>XP nasıl kazanılır?</h2>
            <span className="pill is-xp">Sabit ve denetlenebilir</span>
          </div>
          <div className="analysis-table">
            {xpRules.map((rule) => (
              <div className="analysis-row xp-row" key={rule.action}>
                <span>{rule.action}</span>
                <span className="xp-tag">+{rule.xp} XP</span>
              </div>
            ))}
          </div>
          <p className="muted-text" style={{ marginTop: 14, fontSize: 12.5 }}>
            Aynı soruyu tekrar tekrar çözmek XP kazandırmaz. Puan yalnızca ilk çözüm, hata analizi ve
            doğrulanmış tekrar başarısından gelir.
          </p>
        </article>

        <article className="card">
          <h2>Oyun ekonomisi</h2>
          <ul className="step-list">
            <li>
              <b>20 XP → 2 dakika</b> oyun süresi
            </li>
            <li>
              <b>50 XP → 5 dakika</b> oyun süresi
            </li>
            <li>
              <b>100 XP → bir sonraki seviyede yeni oyun</b> açılır
            </li>
            <li>
              <b>Günlük sınır:</b> en fazla 2 oturum / 10 dakika
            </li>
          </ul>
          <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
            Oyunlar yalnızca günlük çalışma hedefi tamamlandıktan sonra açılır; amaç öğrenme
            davranışını desteklemek.
          </p>
        </article>
      </section>

      <section aria-labelledby="rozetler">
        <div className="section-head">
          <h2 id="rozetler">Rozetler</h2>
          <span className="pill is-mint">{earned} / {badgeList.length} rozet</span>
        </div>
        <div className="badge-grid">
          {badgeList.map((badge) => (
            <article className={`badge-item${badge.earned ? "" : " is-locked"}`} key={badge.name}>
              <span className="badge-emoji" aria-hidden="true">
                {badge.icon}
              </span>
              <b>{badge.name}</b>
              <small>{badge.detail}</small>
              <span className="tag">{badge.earned ? "Kazanıldı" : "Kilitli"}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="card" aria-labelledby="oyun-merkezi">
        <div className="section-head">
          <h2 id="oyun-merkezi">Oyun merkezi</h2>
          <span className="pill is-gok">Günlük hak + süre sınırlı</span>
        </div>
        <GameCenter />
      </section>
    </div>
  );
}
