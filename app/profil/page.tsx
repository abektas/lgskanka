import type { Metadata } from "next";
import Link from "next/link";
import { CharacterAvatar } from "../../components/character-avatar";
import { Icon } from "../../components/icons";
import { ProfileForm } from "../../components/profile-form";
import { badges } from "../../data/content";
import { learner, gameEconomy } from "../../data/nav";

export const metadata: Metadata = {
  title: "Profil ve karakter",
  description:
    "Öğrenci profilini düzenle, karakterini seç, XP ve rozetlerini gör. Veri saklama ayarlarını yönet.",
  alternates: { canonical: "/profil" },
};

const unlockables = [
  {
    icon: "🪑",
    title: "Çalışma odası eşyaları",
    detail: `${learner.roomItems} / ${gameEconomy.tiers.length + 2} eşya açık`,
    earned: learner.roomItems > 0,
  },
  {
    icon: "🏆",
    title: "Rozetler",
    detail: `${badges.filter((b) => b.earned).length} / ${badges.length} rozet kazanıldı`,
    earned: badges.filter((b) => b.earned).length > 0,
  },
  {
    icon: "🎮",
    title: "Oyun hakları",
    detail: `Günlük ${learner.gameRights} hak · ${gameEconomy.dailyMinuteLimit} dk limit`,
    earned: learner.gameRights > 0,
  },
  {
    icon: "⭐",
    title: "Seviye ödülleri",
    detail: `Seviye ${learner.level} · ${gameEconomy.tiers.find((t) => t.xp <= learner.xp)?.label ?? "Henüz yok"}`,
    earned: learner.level > 1,
  },
];

export default function ProfilPage() {
  const earned = badges.filter((badge) => badge.earned);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Karakter ve ayarlar</span>
          <h1>Profil &amp; Karakter</h1>
          <p>
            Karakterin öğrenme ilerlemenin görsel temsilidir: seviye, rozet ve çalışma odası
            gelişiminle birlikte büyür.
          </p>
        </div>
        <Link className="btn btn-primary" href="/calis">
          Çalışmaya dön <Icon name="arrow" size={18} />
        </Link>
      </header>

      <div className="profile-grid">
        <ProfileForm />

        <div className="stack">
          <section className="card" aria-labelledby="karakter-durumu">
            <div className="section-head">
              <h2 id="karakter-durumu">Karakter durumu</h2>
              <span className="pill is-xp">Seviye {learner.level}</span>
            </div>
            <div className="character-summary">
              <CharacterAvatar size={104} />
              <ul className="mini-stats">
                <li>
                  <b>{learner.xp} XP</b>
                  <small>Toplam puan</small>
                </li>
                <li>
                  <b>{earned.length} rozet</b>
                  <small>Kazanılan</small>
                </li>
                <li>
                  <b>{learner.roomItems} eşya</b>
                  <small>Çalışma odası</small>
                </li>
                <li>
                  <b>{learner.streakDays} gün</b>
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
              Ödüller: çalışma odası eşyaları (hata analizi + mini test başarıları), rozetler (seri, mastery,
              hata çözümü), oyun hakları (XP eşine göre), seviye ödülleri.
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
