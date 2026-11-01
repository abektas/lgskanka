"use client";

import { useState } from "react";
import { Avatar, type AvatarGender } from "./avatar";
import { useProfile } from "./profile-provider";

const BOY_VARIANTS = ["Kahverengi saçlı", "Siyah saçlı", "Kıvırcık"];
const GIRL_VARIANTS = ["Uzun kahverengi", "Düz siyah", "Topuz kızıl"];

/**
 * Giriş / kayıt ekranı.
 *
 * Tüm öğrenci verileri online olduğundan aynı cihazdan birden fazla
 * öğrenci şifresiyle giriş yapabilir; karışıklık olmaz.
 */
export function LoginScreen() {
  const { login, register } = useProfile();
  const [mode, setMode] = useState<"login" | "register" | "forgot">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [gender, setGender] = useState<AvatarGender>("boy");
  const [variant, setVariant] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const variants = gender === "boy" ? BOY_VARIANTS : GIRL_VARIANTS;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      if (mode === "login") {
        await login(username.trim(), password);
        // Giriş başarılı → sayfa yeniden yüklensin ki tüm veriler tazelensin
        window.location.reload();
      } else if (mode === "forgot") {
        // Şifreyi standart 1234'e sıfırla
        const res = await fetch("/api/auth/forgot", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: username.trim() }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Şifre sıfırlanamadı.");
        setPassword("1234");
        setMode("login");
        setNotice(
          `Şifren "1234" olarak sıfırlandı. Şimdi "Giriş yap"a basıp girebilirsin.`
        );
      } else {
        await register({
          username: username.trim(),
          password,
          name: name.trim(),
          gender,
          variant,
        });
        // Giriş başarılı → sayfa yeniden yüklensin ki tüm veriler tazelensin
        window.location.reload();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bir sorun oluştu.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="profile-selector" role="dialog" aria-modal="true" aria-label="Giriş">
      <div className="selector-panel" style={{ maxWidth: 460 }}>
        <div style={{ textAlign: "center", marginBottom: 18 }}>
          <div style={{ fontSize: 40, lineHeight: 1 }} aria-hidden="true">
            🎓
          </div>
          <h1 style={{ fontSize: 24, margin: "8px 0 4px" }}>LGS KANKA</h1>
          <p className="muted-text" style={{ fontSize: 13.5, margin: 0 }}>
            Çalışmaların her cihazda seninle. Kullanıcı adın ve şifrenle giriş yap.
          </p>
        </div>

        {/* Mod seçici */}
        <div className="subject-tabs" role="tablist" style={{ marginBottom: 16 }}>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={"subject-tab" + (mode === "login" ? " is-active" : "")}
            onClick={() => {
              setMode("login");
              setError(null);
              setNotice(null);
            }}
          >
            Giriş yap
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={"subject-tab" + (mode === "register" ? " is-active" : "")}
            onClick={() => {
              setMode("register");
              setError(null);
              setNotice(null);
            }}
          >
            Kayıt ol
          </button>
        </div>

        <form className="selector-form" onSubmit={submit}>
          <label className="form-field">
            <span>Kullanıcı adı</span>
            <input
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="örn. ayse123"
              autoComplete="username"
              required
              minLength={3}
              maxLength={24}
            />
          </label>

          {mode !== "forgot" && (
            <label className="form-field">
              <span>Şifre</span>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="En az 4 karakter"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
                minLength={4}
              />
            </label>
          )}

          {mode === "login" && (
            <button
              type="button"
              className="btn-link"
              style={{
                background: "none",
                border: "none",
                color: "var(--mor-600)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                padding: 0,
                textAlign: "left",
              }}
              onClick={() => {
                setMode("forgot");
                setError(null);
                setNotice(null);
              }}
            >
              Şifremi unuttum
            </button>
          )}

          {mode === "forgot" && (
            <p className="muted-text" style={{ fontSize: 13, margin: 0 }}>
              Kullanıcı adını yaz ve sıfırla — şifren standart <b>1234</b> olur,
              hemen giriş yapabilirsin.
            </p>
          )}

          {mode === "register" && (
            <>
              <label className="form-field">
                <span>Adın</span>
                <input
                  className="input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="örn. Ayşe"
                  required
                  maxLength={40}
                />
              </label>

              <div className="form-field">
                <span>Karakterin</span>
                <div className="subject-tabs" style={{ marginBottom: 8 }}>
                  <button
                    type="button"
                    className={"subject-tab" + (gender === "boy" ? " is-active" : "")}
                    onClick={() => {
                      setGender("boy");
                      setVariant(0);
                    }}
                  >
                    👦 Erkek
                  </button>
                  <button
                    type="button"
                    className={"subject-tab" + (gender === "girl" ? " is-active" : "")}
                    onClick={() => {
                      setGender("girl");
                      setVariant(0);
                    }}
                  >
                    👧 Kız
                  </button>
                </div>
                <div className="avatar-picker" role="radiogroup" aria-label="Karakter seç">
                  {variants.map((label, i) => (
                    <button
                      key={label}
                      type="button"
                      role="radio"
                      aria-checked={variant === i}
                      className={"avatar-option" + (variant === i ? " is-active" : "")}
                      onClick={() => setVariant(i)}
                    >
                      <Avatar gender={gender} variant={i} size={72} />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {error && (
            <p className="muted-text" style={{ color: "#c2410c", fontSize: 13, margin: 0 }}>
              {error}
            </p>
          )}

          {notice && (
            <p className="muted-text" style={{ color: "#0d7d5d", fontSize: 13, margin: 0, fontWeight: 600 }}>
              {notice}
            </p>
          )}

          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy
              ? "Bekle…"
              : mode === "login"
                ? "Giriş yap"
                : mode === "forgot"
                  ? "Şifremi 1234 yap"
                  : "Kayıt ol ve başla"}
          </button>

          {mode === "forgot" && (
            <button
              type="button"
              className="btn btn-soft"
              onClick={() => {
                setMode("login");
                setError(null);
                setNotice(null);
              }}
            >
              Vazgeç
            </button>
          )}
        </form>

        <p className="selector-footnote">
          Şifreni unutursan &quot;Şifremi unuttum&quot; ile şifreni 1234 yapabilirsin.
          Kullanıcı adın sana özeldir — aynı isimde başkaları olsa bile karışmaz.
        </p>
      </div>
    </div>
  );
}