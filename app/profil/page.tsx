"use client";

import Link from "next/link";
import { CharacterAvatar } from "../../components/character-avatar";
import { Icon } from "../../components/icons";
import { ProfileForm } from "../../components/profile-form";
import { ProfileSelector } from "../../components/profile-selector";
import { useProfile } from "../../components/profile-provider";
import { badges } from "../../data/content";
import { gameEconomy } from "../../data/nav";
import { useLearnerStats } from "../../lib/learner-stats";

function buildUnlockables(level: number, xp: number, badgeCount: number) {
  return [
  {
    icon: "🏆",
    title: "Rozetler",
    detail: `${badgeCount} / ${badges.length} rozet kazanıldı`,
    earned: badgeCount > 0,
  },
  {
    icon: "🎮",
    title: "Oyun hakları",
    detail: `Günlük ${gameEconomy.dailySessionLimit} hak · ${gameEconomy.dailyMinuteLimit} dk limit`,
    earned: true,
  },
  {
    icon: "⭐",
    title: "Seviye ödülleri",
    detail: `Seviye ${level} · ${gameEconomy.tiers.find((t) => t.xp <= xp)?.label ?? "Henüz yok"}`,
    earned: level > 1,
  },
  ];
}

export default function ProfilPage() {
  const { profiles, activeProfile, switchProfile } = useProfile();
  const stats = useLearnerStats();
  const level = stats?.level ?? 1;
  const xp = stats?.xp ?? 0;
  const streakDays = stats?.streakDays ?? 0;
  const badgeCount = stats?.badgeCount ?? 0;
  const unlockables = buildUnlockables(level, xp, badgeCount);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Karakter ve ayarlar</span>
          <h1>Profil & Karakter</h1>
          <p>
            Karakterin öğrenme ilerlemenin görsel temsilidir: seviye, rozet ve çalışma odası
            gelişiminle birlikte büyür.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Çalışmaya dön <Icon name="arrow" size={18} />
        </Link>
      </header>

      {profiles.length > 1 && (
        <section className="card" aria-labelledby="profile-switcher" style={{ marginBottom: 20 }}>
          <div className="section-head">
            <h2 id="profile-switcher">Profiller</h2>
            <Link className="text-link" href="/profil" onClick={(e) => e.preventDefault()}>
              <ProfileSelector required={false} />
            </Link>
          </div>
          <div className="profile-cards" role="list" style={{ display: "grid", gap: 10 }}>
            {profiles.map((profile) => (
              <article
                key={profile.id}
                className={`profile-card${activeProfile?.id === profile.id ? " is-active" : ""}`}
                role="listitem"
                onClick={() => switchProfile(profile.id)}
                aria-selected={activeProfile?.id === profile.id}
                style={{ cursor: "pointer" }}
              >
                <div className="profile-card-avatar">
                  <CharacterAvatar size={56} />
                </div>
                <div className="profile-card-info">
                  <b style={{ fontSize: 15 }}>{profile.name}</b>
                  <small className="muted-text">
                    {activeProfile?.id === profile.id ? "✓ Aktif" : "Tıkla ve değiştir"}
                  </small>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      <div className="profile-grid">
        <ProfileForm />

        <div className="stack">
          <section className="card" aria-labelledby="karakter-durumu">
            <div className="section-head">
              <h2 id="karakter-durumu">Karakter durumu</h2>
              <span className="pill is-xp">Seviye {level}</span>
            </div>
            <div className="character-summary">
              <CharacterAvatar size={104} />
              <ul className="mini-stats">
                              <li>
                                <b>{xp} XP</b>
                                <small>Toplam puan</small>
                              </li>
                              <li>
                                <b>{badgeCount} rozet</b>
                                <small>Kazanılan</small>
                              </li>
                              <li>
                                <b>{streakDays} gün</b>
                                <small>Çalışma serisi</small>
                              </li>
                            </ul>
            </div>
            <p className="muted-text" style={{ marginTop: 14, fontSize: 12.5 }}>
              Karakterin seçtiğin görünümle ana sayfada ve üst menüde görünür.
            </p>
          </section>

          <section className="card" aria-labelledby="kisisellestirme">
            <h2 id="kisisellestirme">Kazanılan ödüller</h2>
            <div className="customize-grid">
              {unlockables.map((item) => (
                <div className={`customize-item${item.earned ? "" : " is-locked"}`} key={item.title}>
                  <span className="customize-emoji" aria-hidden="true">
                    {item.icon}
                  </span>
                  <b>{item.title}</b>
                  <small>{item.detail}</small>
                  {item.earned ? (
                    <span className="tag" style={{ marginTop: 6, fontSize: 11 }}>Açık</span>
                  ) : (
                    <span className="tag" style={{ marginTop: 6, fontSize: 11 }}>Kilitli</span>
                  )}
                </div>
              ))}
            </div>
            <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
              Ödüller: rozetler (seri, mastery, hata çözümü), oyun hakları (XP eşine göre), seviye ödülleri.
            </p>
          </section>

          <section className="card" aria-labelledby="gizlilik">
            <h2 id="gizlilik">Verin ve gizlilik</h2>
            <ul className="privacy-list">
              <li>
                <b>Öğrenme verisi:</b> yalnızca türetilmiş sonuçlar (hata türü, konu, mastery) tarayıcıda
                saklanır; ham görüntü ve ses tutulmaz.
              </li>
              <li>
                <b>Yerel depolama:</b> profil, ayarlar ve görev durumu yalnızca bu tarayıcıda kalır;
                sunucuya gönderilmez.
              </li>
              <li>
                <b>Veri silme:</b> Profil sayfasındaki &ldquo;Öğrenme verisi saklansın&rdquo; ayarını
                kapatırsan tüm yerel kayıtlar silinir.
              </li>
            </ul>
            <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
              Ebeveyn onayı: üretim sürümünde 18 yaş altı kullanımlar için onay akışı zorunludur.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}