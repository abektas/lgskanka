"use client";

import { useState, FormEvent } from "react";
import { Avatar, type AvatarGender } from "./avatar";
import { Icon } from "./icons";
import { useProfile, type Profile } from "./profile-provider";

const variants = [0, 1, 2];

const variantLabels: Record<AvatarGender, string[]> = {
  boy: ["Kahverengi saçlı", "Siyah saçlı", "Kıvırcık"],
  girl: ["Uzun kahverengi", "Düz siyah", "Topuz kızıl"],
};

type Props = {
  /** true ise profil seçimi zorunlu (ilk açılış), false ise ayarlar sayfasından */
  required?: boolean;
  /** profili seçtikten sonra yönlendirilecek sayfa */
  onComplete?: () => void;
};

/**
 * Profil seçme/oluşturma ekranı.
 * İlk açılışta (profil yoksa) veya ayarlar sayfasından çağrılır.
 */
export function ProfileSelector({ required = true, onComplete }: Props) {
  const { profiles, activeProfile, createProfile, switchProfile, updateProfile, deleteProfile, ready } = useProfile();
  const [draft, setDraft] = useState<Omit<Profile, "id" | "registeredAt">>({
    name: "",
    gender: "boy",
    variant: 0,
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [saved, setSaved] = useState(false);

  // Düzenleme modunda profili forma yükle
  const startEdit = (profile: Profile) => {
    setDraft({ name: profile.name, gender: profile.gender, variant: profile.variant });
    setEditingId(profile.id);
    setShowForm(true);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (editingId) {
      updateProfile(draft);
    } else {
      createProfile(draft);
      setDraft({ name: "", gender: "boy", variant: 0 });
    }
    setEditingId(null);
    setShowForm(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    onComplete?.();
  };

  const handleSwitch = (id: string) => {
    switchProfile(id);
    onComplete?.();
  };

  const handleDelete = (id: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (confirm("Bu profili silmek istediğine emin misin? İlerleme verin de silinecek.")) {
      deleteProfile(id);
    }
  };

  if (!ready) return null;

  // Profil zaten seçilmişse ve required değilse (ayarlar sayfasında) liste göster
  const isFirstLaunch = required && profiles.length === 0;

  return (
    <div className={`profile-selector${isFirstLaunch ? " is-first-launch" : ""}`} role="dialog" aria-modal="true" aria-labelledby="selector-title">
      <div className="selector-backdrop" onClick={() => !isFirstLaunch && onComplete?.()} aria-hidden="true" />

      <div className="selector-panel">
        <header className="selector-head">
          <div>
            <span className="eyebrow" style={{ fontSize: 13, color: "var(--muted-foreground)" }}>
              {isFirstLaunch ? "Hoş geldin! 👋" : "Profiller"}
            </span>
            <h1 id="selector-title" style={{ marginTop: 4, marginBottom: 2 }}>
              {isFirstLaunch ? "LGS KANKA'ya hoş geldin" : "Profil seç veya yeni oluştur"}
            </h1>
            <p className="muted-text" style={{ fontSize: 14, margin: 0 }}>
              {isFirstLaunch
                ? "Kendine bir karakter yarat, adını yaz ve çalışmaya başla. Verin sadece bu cihazda kalır."
                : "Farklı öğrenciler için profiller oluştur, anında değiştir."}
            </p>
          </div>
          {!isFirstLaunch && (
            <button
              className="selector-close"
              onClick={() => onComplete?.()}
              aria-label="Kapat"
            >
              <Icon name="close" size={20} />
            </button>
          )}
        </header>

        {profiles.length > 0 && (
          <section className="selector-profiles" aria-label="Mevcut profiller">
            <h2 className="section-title" style={{ display: isFirstLaunch ? "none" : "block" }}>
              {isFirstLaunch ? "Karakterini seç" : "Mevcut profiller"}
            </h2>
            <div className="profile-cards" role="list">
              {profiles.map((profile) => (
                <article
                  key={profile.id}
                  className={`profile-card${activeProfile?.id === profile.id ? " is-active" : ""}`}
                  role="listitem"
                  onClick={() => !isFirstLaunch && handleSwitch(profile.id)}
                  aria-selected={activeProfile?.id === profile.id}
                >
                  <div className="profile-card-avatar">
                    <Avatar gender={profile.gender} variant={profile.variant} size={72} />
                  </div>
                  <div className="profile-card-info">
                    <b style={{ fontSize: 16 }}>{profile.name}</b>
                    <small className="muted-text">
                      {activeProfile?.id === profile.id ? "✓ Aktif" : "Tıkla ve başla"}
                    </small>
                  </div>
                  {!isFirstLaunch && (
                    <div className="profile-card-actions">
                      <button
                        className="icon-btn"
                        onClick={(e) => startEdit(profile)}
                        aria-label={`${profile.name} profilini düzenle`}
                      >
                        <Icon name="edit" size={16} />
                      </button>
                      {profiles.length > 1 && (
                        <button
                          className="icon-btn danger"
                          onClick={(e) => handleDelete(profile.id, e)}
                          aria-label={`${profile.name} profilini sil`}
                        >
                          <Icon name="trash" size={16} />
                        </button>
                      )}
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}

        <section className="selector-form-section" aria-label={editingId ? "Profili düzenle" : "Yeni profil oluştur"}>
          <h2 className="section-title" style={{ display: showForm || profiles.length === 0 ? "block" : "none" }}>
            {editingId ? "Profili düzenle" : "Yeni karakter oluştur"}
          </h2>

          <form className="selector-form" onSubmit={handleSubmit} style={{ display: showForm || profiles.length === 0 ? "block" : "none" }}>
            <div className="field">
              <label htmlFor="profile-name">Öğrenci adı</label>
              <input
                id="profile-name"
                value={draft.name}
                maxLength={24}
                placeholder="Örn. Elif, Ahmet..."
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                autoFocus
                required
              />
              <small>Kanka sana hitap ederken kullanacağı ad.</small>
            </div>

            <fieldset className="fieldset">
              <legend>Karakterin</legend>
              <div className="gender-tabs">
                {(["boy", "girl"] as AvatarGender[]).map((gender) => (
                  <button
                    key={gender}
                    type="button"
                    className={draft.gender === gender ? "is-active" : undefined}
                    aria-pressed={draft.gender === gender}
                    onClick={() => setDraft({ ...draft, gender, variant: 0 })}
                  >
                    {gender === "boy" ? "👦 Erkek" : "👧 Kız"}
                  </button>
                ))}
              </div>

              <div className="avatar-picker">
                {variants.map((variant) => (
                  <button
                    key={variant}
                    type="button"
                    className={`avatar-option${draft.variant === variant ? " is-active" : ""}`}
                    aria-pressed={draft.variant === variant}
                    onClick={() => setDraft({ ...draft, variant })}
                  >
                    <Avatar gender={draft.gender} variant={variant} size={88} />
                    <span>{variantLabels[draft.gender][variant]}</span>
                  </button>
                ))}
              </div>
              <small className="muted-text">Karakter daha sonra her zaman değiştirilebilir; ilerlemen kaybolmaz.</small>
            </fieldset>

            <div className="form-actions">
              {profiles.length > 0 && !editingId && (
                <button type="button" className="btn btn-ghost" onClick={() => setShowForm(true)}>
                  <Icon name="plus" size={16} /> Yeni profil
                </button>
              )}
              <button className="btn btn-primary btn-block" type="submit" disabled={!draft.name.trim()}>
                {saved ? (
                  <>
                    <Icon name="check" size={18} /> {editingId ? "Güncellendi" : "Kaydet ve başla"}
                  </>
                ) : (
                  editingId
                    ? "Güncelle"
                    : profiles.length === 0
                    ? "Karakteri oluştur ve başla"
                    : "Profil ekle"
                )}
              </button>
            </div>

            {editingId && (
              <button
                type="button"
                className="btn btn-ghost btn-block"
                style={{ marginTop: 8 }}
                onClick={() => {
                  setEditingId(null);
                  setShowForm(false);
                  setDraft({ name: "", gender: "boy", variant: 0 });
                }}
              >
                <Icon name="close" size={16} /> İptal
              </button>
            )}
          </form>

          {profiles.length > 0 && !showForm && !editingId && (
            <button className="btn btn-ghost btn-block" onClick={() => setShowForm(true)}>
              <Icon name="plus" size={16} /> Yeni profil ekle
            </button>
          )}
        </section>

        {isFirstLaunch && (
          <p className="selector-footnote">
            Verin (hata analizi, konu takibi, rozetler) yalnızca bu tarayıcıda saklanır. Sunucuya gönderilmez.
          </p>
        )}
      </div>
    </div>
  );
}