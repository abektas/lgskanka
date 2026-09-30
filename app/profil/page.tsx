import type { Metadata } from "next";
import Link from "next/link";
import { CharacterAvatar } from "../../components/character-avatar";
import { Icon } from "../../components/icons";
import { ProfileForm } from "../../components/profile-form";
import { badges } from "../../data/content";
import { learner } from "../../data/nav";

export const metadata: Metadata = {
  title: "Profil ve karakter",
  description:
    "Öğrenci profilini düzenle, karakterini seç, XP ve rozetlerini gör. Ses ve çözüm fotoğrafı için gizlilik ayarlarını yönet.",
  alternates: { canonical: "/profil" },
};

const customization = [
  { icon: "👕", title: "Kıyafetler", detail: "3 eşya açık · LGS kapüşonlusu, okul forması" },
  { icon: "💇", title: "Saç modelleri", detail: "Karakter seçiminde 3 model hazır" },
  { icon: "🎧", title: "Aksesuarlar", detail: "Kulaklık, gözlük, sırt çantası" },
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
            <h2 id="kisisellestirme">Özelleştirme</h2>
            <div className="customize-grid">
              {customization.map((item) => (
                <div className="customize-item" key={item.title}>
                  <span className="customize-emoji" aria-hidden="true">
                    {item.icon}
                  </span>
                  <b>{item.title}</b>
                  <small>{item.detail}</small>
                </div>
              ))}
            </div>
            <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
              Yeni kıyafet ve aksesuarlar çalışma hedefleri, hata çözümü ve mastery artışıyla açılır.
            </p>
          </section>

          <section className="card" aria-labelledby="gizlilik">
            <h2 id="gizlilik">Verin ve gizlilik</h2>
            <ul className="privacy-list">
              <li>
                <b>Ses kaydı:</b> yalnızca analiz için kullanılır, en fazla 60 saniye; analiz
                tamamlandığında kalıcı olarak silinir.
              </li>
              <li>
                <b>Çözüm fotoğrafı:</b> profilde veya veritabanında saklanmaz, yedeklere dâhil edilmez.
              </li>
              <li>
                <b>Öğrenme verisi:</b> yalnızca türetilmiş sonuçlar (hata türü, konu, mastery) saklanır;
                ham görüntü ve ses tutulmaz.
              </li>
              <li>
                <b>Ebeveyn onayı:</b> üretim sürümünde 18 yaş altı kullanımlar için onay akışı
                zorunludur.
              </li>
            </ul>
            <p className="muted-text" style={{ marginTop: 12, fontSize: 12.5 }}>
              Bu sürümde profil, ayarlar ve görev durumu yalnızca senin tarayıcında saklanır; sunucuya
              gönderilmez.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
