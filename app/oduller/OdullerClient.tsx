"use client";

import Link from "next/link";
import { Icon } from "../../components/icons";
import { GameCenter } from "../../components/game-center";
import { badges } from "../../data/content";
import { gameEconomy, xpRules } from "../../data/nav";
import { useBadgeProgress } from "../../components/use-badge-progress";
import { useLearnerStats } from "../../lib/learner-stats";

export function OdullerClient() {
  const stats = useLearnerStats();
  const xp = stats?.xp ?? 0;
  const level = stats?.level ?? 1;
  const levelXp = stats?.levelXp ?? 0;
  const levelTarget = stats?.levelTarget ?? 0;
  const nextLevelXp = levelTarget - levelXp;
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
          <b>{xp} XP</b>
          <small>
            Bir sonraki seviye için {nextLevelXp} XP kaldı (Seviye {level + 1})
          </small>
          <div
            className="bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={levelTarget}
            aria-valuenow={levelXp}
            aria-label="Seviye ilerlemesi"
          >
            <i style={{ width: `${Math.round((levelXp / Math.max(1, levelTarget)) * 100)}%` }} />
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
          <b>{gameEconomy.dailySessionLimit} oyun hakkı · {gameEconomy.dailyMinuteLimit} dakika</b>
          <small>XP eşiğine göre günlük süre artar (20 XP → 5 dk, 50 XP → 8 dk, 100 XP → 10 dk). Oyun öğrenmenin
            yerine geçmez.</small>
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
              <b>20 XP → 5 dakika</b> oyun süresi
            </li>
            <li>
              <b>50 XP → 8 dakika</b> oyun süresi
            </li>
            <li>
              <b>100 XP → 10 dakika</b> oyun süresi
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
