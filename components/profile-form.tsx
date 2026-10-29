"use client";

import { useEffect, useState } from "react";
import { Avatar, type AvatarGender } from "./avatar";
import { Icon } from "./icons";
import { useProfile, type Profile } from "./profile-provider";

const SETTINGS_KEY = "lgs-ai-coach-settings";

type Settings = {
  dataRetention: boolean;
};

const defaultSettings: Settings = {
  dataRetention: true,
};

const variants = [0, 1, 2];

const variantLabels: Record<AvatarGender, string[]> = {
  boy: ["Kahverengi saçlı", "Siyah saçlı", "Kıvırcık"],
  girl: ["Uzun kahverengi", "Düz siyah", "Topuz kızıl"],
};

const settingRows: { key: keyof Settings; title: string; detail: string }[] = [
  {
    key: "dataRetention",
    title: "Öğrenme verisi saklansın",
    detail: "Hata türü, konu ve mastery gibi türetilmiş sonuçlar tarayıcıda kalır. Kapatırsan tüm yerel kayıtlar silinir.",
  },
];

/** Profil & karakter formu: ad, cinsiyet, karakter seçimi ve gizlilik ayarları. */
export function ProfileForm() {
  const { profile, ready, saveProfile } = useProfile();
  const [draft, setDraft] = useState<Profile>(profile);
  const [settings, setSettings] = useState<Settings>(defaultSettings);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (ready) setDraft(profile);
  }, [ready, profile]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SETTINGS_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<Settings>;
        setSettings({ ...defaultSettings, ...parsed });
      }
    } catch {
      /* varsayılan ayarlarla devam */
    }
  }, []);

  function toggleSetting(key: keyof Settings) {
    setSettings((previous) => {
      const next = { ...previous, [key]: !previous[key] };
      try {
        window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
      } catch {
        /* depolama kapalıysa yalnızca bellekte tut */
      }
      return next;
    });
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    saveProfile(draft);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2600);
  }

  return (
    <form className="card" onSubmit={onSubmit}>
      <div className="section-head">
        <h2>Öğrenci bilgileri</h2>
        <span className="pill is-mint">Adın yalnızca bu cihazda saklanır</span>
      </div>

      <div className="field">
        <label htmlFor="ogrenci-adi">Öğrenci adı</label>
        <input
          id="ogrenci-adi"
          value={draft.name}
          maxLength={24}
          placeholder="Örn. Elif"
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
        />
        <small>Kankan sana hitap ederken kullanacağı ad. Boş bırakırsan &ldquo;Öğrenci&rdquo; yazar.</small>
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
              <Avatar gender={draft.gender} variant={variant} size={92} />
              <span>{variantLabels[draft.gender][variant]}</span>
            </button>
          ))}
        </div>
        <small className="muted-text">
          Karakter daha sonra her zaman değiştirilebilir; ilerlemen ve rozetlerin kaybolmaz.
        </small>
      </fieldset>

      <button className="btn btn-primary btn-block" type="submit">
        {saved ? (
          <>
            <Icon name="check" size={18} /> Kaydedildi
          </>
        ) : (
          "Karakteri kaydet"
        )}
      </button>

      <div className="settings-block">
        <h3>Gizlilik ve bildirimler</h3>
        {settingRows.map((row) => (
          <div className="switch-row" key={row.key}>
            <span>
              <b>{row.title}</b>
              <small className="muted-text">{row.detail}</small>
            </span>
            <button
              type="button"
              className="switch"
              role="switch"
              aria-checked={settings[row.key]}
              aria-label={row.title}
              onClick={() => toggleSetting(row.key)}
            />
          </div>
        ))}
      </div>
    </form>
  );
}
