"use client";

/**
 * Öğretmen (admin) paneli — gizli sayfa (/ogretmen).
 * Öğretmen anahtarı (ADMIN_RESET_SECRET) ile açılır; öğrenciler bu sayfayı göremez.
 */

import { useEffect, useMemo, useState } from "react";
import { Icon } from "../../components/icons";

const ADMIN_KEY_STORAGE = "lgs_admin_key";

type StudentRow = {
  id: string;
  username: string;
  name: string;
  gender: string;
  variant: number;
  registered_at: string;
  total_answered: number;
  total_correct: number;
  last_activity: string | null;
  exam_count: number;
  last_exam_month: number | null;
  last_exam_percentage: number | null;
  last_exam_level: string | null;
  open_tasks: number;
  active_exams: Array<{
    month: number;
    label: string;
    answered: number;
    total: number;
    updatedAt: string;
  }>;
  today_solved: number;
  today_correct: number;
  today_target: number;
};

type StudentDetail = {
  studentId: string;
  totalAnswered: number;
  totalCorrect: number;
  weakTopics: Array<{ label: string; count: number }>;
  exams: Array<{
    month: number;
    month_name: string;
    correct: number;
    wrong: number;
    empty: number;
    percentage: number;
    level: string;
    completed_at: string;
  }>;
  tasks: Array<{
    id: string;
    subject: string;
    unit_name: string | null;
    topic: string | null;
    status: string;
    wrong_count: number;
  }>;
  examSessions: Array<{
    month: number;
    label: string;
    answered: number;
    total: number;
    currentIndex: number;
    updatedAt: string;
  }>;
  studySessions: Array<{
    session_date: string;
    solved: number;
    correct: number;
    target: number;
  }>;
};

type QuestionReport = {
  id: string;
  source: string;
  month: number | null;
  month_name: string | null;
  question_id: string | null;
  question_number: number | null;
  subject: string | null;
  image_path: string | null;
  reason: string | null;
  status: string;
  created_at: string;
  students?: { name: string; username: string } | null;
};

function fmtDate(s: string | null): string {
  if (!s) return "—";
  const d = new Date(s);
  return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit", year: "2-digit" }) +
    " " + d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

function pct(correct: number, total: number): string {
  if (!total) return "—";
  return `%${Math.round((correct / total) * 100)}`;
}

export default function OgretmenPage() {
  const [key, setKey] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<StudentDetail | null>(null);
  const [detailFor, setDetailFor] = useState<StudentRow | null>(null);
  const [resetUser, setResetUser] = useState("");
  const [resetPass, setResetPass] = useState("");
  const [resetMsg, setResetMsg] = useState<string | null>(null);
  const [reports, setReports] = useState<QuestionReport[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const saved = localStorage.getItem(ADMIN_KEY_STORAGE);
    if (saved) {
      setKey(saved);
      loadOverview(saved);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadOverview(adminKey: string) {
    setLoading(true);
    setError(null);
    try {
      const [res, repRes] = await Promise.all([
        fetch("/api/admin/overview", {
          headers: { "x-admin-key": adminKey },
        }),
        fetch("/api/question-reports", {
          headers: { "x-admin-key": adminKey },
        }),
      ]);
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Yetkilendirme hatası");
        setStudents([]);
      } else {
        setStudents(data.students || []);
      }
      const repData = await repRes.json().catch(() => ({}));
      if (repRes.ok) setReports(repData.reports || []);
    } catch {
      setError("Sunucuya ulaşılamadı.");
    } finally {
      setLoading(false);
    }
  }

  function saveKey() {
    const k = keyInput.trim();
    if (!k) return;
    localStorage.setItem(ADMIN_KEY_STORAGE, k);
    setKey(k);
    loadOverview(k);
  }

  function logoutKey() {
    localStorage.removeItem(ADMIN_KEY_STORAGE);
    setKey("");
    setKeyInput("");
    setStudents([]);
    setDetail(null);
    setDetailFor(null);
    setError(null);
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) => {
      if (prev.size === filtered.length) return new Set();
      return new Set(filtered.map((s) => s.id));
    });
  }

  async function deleteSelected() {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    const ok = window.confirm(
      `${ids.length} öğrenci ve tüm kayıtları (cevaplar, denemeler, bildirimler) kalıcı olarak silinecek. Emin misin?`
    );
    if (!ok) return;
    try {
      const res = await fetch("/api/admin/overview", {
        method: "DELETE",
        headers: { "Content-Type": "application/json", "x-admin-key": key },
        body: JSON.stringify({ ids }),
      });
      const data = await res.json();
      if (res.ok) {
        setSelectedIds(new Set());
        await loadOverview(key);
      } else {
        alert(data.error || "Silme başarısız oldu.");
      }
    } catch {
      alert("Sunucuya ulaşılamadı.");
    }
  }

  async function openDetail(row: StudentRow) {
    setDetailFor(row);
    setDetail(null);
    try {
      const res = await fetch(`/api/admin/overview?id=${row.id}`, {
        headers: { "x-admin-key": key },
      });
      const data = await res.json();
      if (res.ok) setDetail(data);
    } catch {
      /* yoksay */
    }
  }

  async function resetPassword() {
    setResetMsg(null);
    try {
      const res = await fetch("/api/admin/overview", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-admin-key": key },
        body: JSON.stringify({ username: resetUser.trim(), newPassword: resetPass }),
      });
      const data = await res.json();
      if (res.ok) {
        setResetMsg(`✅ ${resetUser} için şifre güncellendi.`);
        setResetPass("");
      } else {
        setResetMsg(`❌ ${data.error || "Hata oluştu"}`);
      }
    } catch {
      setResetMsg("❌ Sunucuya ulaşılamadı.");
    }
  }

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return students;
    return students.filter(
      (s) => s.name.toLowerCase().includes(q) || s.username.toLowerCase().includes(q)
    );
  }, [students, search]);

  const stats = useMemo(() => {
    const total = students.length;
    const active7 = students.filter((s) => {
      if (!s.last_activity) return false;
      return Date.now() - new Date(s.last_activity).getTime() < 7 * 24 * 3600 * 1000;
    }).length;
    const levelStarted = students.filter(
      (s) => s.exam_count > 0 || s.active_exams.some((a) => a.month === 0)
    ).length;
    const avg = total
      ? Math.round(
          (students.reduce((a, s) => a + s.total_correct, 0) /
            Math.max(1, students.reduce((a, s) => a + s.total_answered, 0))) *
            100
        )
      : 0;
    return { total, active7, levelStarted, avg };
  }, [students]);

  // ---- Anahtar girilmemişse giriş ekranı ----
  if (!key) {
    return (
      <main className="stack page-enter">
        <header>
          <p className="section-label">Gizli sayfa</p>
          <h1>Öğretmen Paneli</h1>
          <p className="lead">
            Bu sayfa sadece öğretmen içindir. Devam etmek için öğretmen anahtarını gir.
          </p>
        </header>
        <section className="card">
          <div className="field">
            <label htmlFor="admin-key">Öğretmen anahtarı</label>
            <input
              id="admin-key"
              type="password"
              className="input"
              autoComplete="off"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveKey()}
              placeholder="Anahtar"
            />
          </div>
          {error && <p className="error-text">{error}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
            <button className="btn btn-primary" onClick={saveKey}>
              <Icon name="shield" />
              Panele gir
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="stack page-enter">
      <header>
        <p className="section-label">Gizli sayfa</p>
        <h1>Öğretmen Paneli</h1>
        <p className="lead">Öğrencilerinin ilerlemesini buradan takip edebilirsin.</p>
      </header>

      {/* Özet kartlar */}
      <section className="card" aria-label="Genel durum">
        <div className="admin-stats">
          <div>
            <span className="admin-stat-value">{stats.total}</span>
            <span className="admin-stat-label">Kayıtlı öğrenci</span>
          </div>
          <div>
            <span className="admin-stat-value">{stats.active7}</span>
            <span className="admin-stat-label">Son 7 gün aktif</span>
          </div>
          <div>
            <span className="admin-stat-value">{stats.levelStarted}</span>
            <span className="admin-stat-label">Seviye tespitine başlayıp bitiren/başlayan</span>
          </div>
          <div>
            <span className="admin-stat-value">%{stats.avg}</span>
            <span className="admin-stat-label">Ortalama doğruluk</span>
          </div>
        </div>
      </section>

      {/* Şifre sıfırlama */}
      <section className="card">
        <h2 style={{ margin: "0 0 12px", fontSize: 18 }}>Şifre sıfırlama</h2>
        <div className="admin-reset-row">
          <div className="field">
            <label htmlFor="reset-user">Kullanıcı adı</label>
            <input
              id="reset-user"
              className="input"
              value={resetUser}
              onChange={(e) => setResetUser(e.target.value)}
              placeholder="örn. @lgsdeneme1 veya lgsdeneme1"
            />
          </div>
          <div className="field">
            <label htmlFor="reset-pass">Yeni şifre</label>
            <input
              id="reset-pass"
              type="text"
              className="input"
              value={resetPass}
              onChange={(e) => setResetPass(e.target.value)}
              placeholder="En az 4 karakter"
            />
          </div>
          <button
            className="btn btn-secondary"
            onClick={resetPassword}
            disabled={!resetUser.trim() || resetPass.length < 4}
            style={{ alignSelf: "end" }}
          >
            Sıfırla
          </button>
        </div>
        {resetMsg && <p style={{ margin: "10px 0 0", fontSize: 13 }}>{resetMsg}</p>}
      </section>

      {/* Öğrenci listesi */}
      <section className="card">
        <div className="admin-list-head">
          <h2 style={{ margin: 0, fontSize: 18 }}>Öğrenciler</h2>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input
              className="input"
              style={{ width: 220 }}
              placeholder="İsim veya kullanıcı adı ara"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button
              className="btn btn-secondary"
              onClick={deleteSelected}
              disabled={selectedIds.size === 0}
              title="İşaretlenen öğrencileri sil"
            >
              <Icon name="trash" />
              Seçilenleri sil{selectedIds.size > 0 ? ` (${selectedIds.size})` : ""}
            </button>
            <button className="btn btn-secondary" onClick={() => loadOverview(key)}>
              <Icon name="chart" />
              Yenile
            </button>
            <button className="btn btn-secondary" onClick={logoutKey}>
              <Icon name="close" />
              Anahtarı temizle
            </button>
          </div>
        </div>

        {loading && <p className="muted">Yükleniyor…</p>}
        {error && <p className="error-text">{error}</p>}

        {!loading && !error && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th style={{ width: 36 }}>
                    <input
                      type="checkbox"
                      aria-label="Tümünü seç"
                      checked={filtered.length > 0 && selectedIds.size === filtered.length}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th>Öğrenci</th>
                  <th>Son aktivite</th>
                  <th>Çözülen</th>
                  <th>Doğru</th>
                  <th>Deneme</th>
                  <th>Pekiştirme</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={s.name + " seç"}
                        checked={selectedIds.has(s.id)}
                        onChange={() => toggleSelect(s.id)}
                      />
                    </td>
                    <td>
                      <strong>{s.name}</strong>
                      <span className="muted"> @{s.username}</span>
                    </td>
                    <td>{fmtDate(s.last_activity)}</td>
                    <td>
                      {s.total_answered}
                      {s.today_solved > 0 && (
                        <div className="muted" style={{ fontSize: 11 }}>
                          bugün {s.today_solved}/{s.today_target} · {s.today_correct} doğru
                        </div>
                      )}
                    </td>
                    <td>{pct(s.total_correct, s.total_answered)}</td>
                    <td>
                      {s.active_exams.map((a) => (
                        <div key={a.month} style={{ fontSize: 12 }}>
                          <strong>{a.label}</strong> yarım kaldı ({a.answered}/{a.total})
                        </div>
                      ))}
                      {s.exam_count > 0 && (
                        <div style={{ fontSize: 12 }}>
                          {s.exam_count} sınav · son:{" "}
                          {s.last_exam_month === 0 ? "Seviye" : s.last_exam_month + ". Ay"}{" "}
                          {s.last_exam_level ? "(" + s.last_exam_level + ")" : ""}
                        </div>
                      )}
                      {s.exam_count === 0 && s.active_exams.length === 0 && "—"}
                    </td>
                    <td>{s.open_tasks > 0 ? `${s.open_tasks} açık` : "—"}</td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => openDetail(s)}
                      >
                        Detay
                      </button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={8} className="muted">
                      Kayıtlı öğrenci yok.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Bildirilen sorular (bozuk/eksik) */}
      <section className="card">
        <div className="admin-list-head">
          <h2 style={{ margin: 0, fontSize: 18 }}>Bildirilen sorular (bozuk/eksik)</h2>
          <button className="btn btn-secondary" onClick={() => loadOverview(key)}>
            <Icon name="chart" />
            Yenile
          </button>
        </div>
        {reports.length === 0 ? (
          <p className="muted">Bildirim yok — öğrenciler "Soru eksik veya bozuk" derse burada listelenir.</p>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Sınav</th>
                  <th>Soru</th>
                  <th>Görsel dosyası</th>
                  <th>Bildirim tarihi</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.students?.name || "—"}</strong>
                      <span className="muted"> @{r.students?.username || "?"}</span>
                    </td>
                    <td>{r.month_name || (r.month === 0 ? "Seviye Tespit" : r.month !== null ? r.month + ". Ay" : "—")}</td>
                    <td>
                      Soru {r.question_number ?? "?"}
                      {r.subject ? ` · ${r.subject}` : ""}
                    </td>
                    <td>
                      <code style={{ fontSize: 11, wordBreak: "break-all" }}>
                        {r.image_path || r.question_id || "—"}
                      </code>
                    </td>
                    <td>{fmtDate(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Öğrenci detayı */}
      {detailFor && (
        <section className="card">
          <div className="admin-list-head">
            <h2 style={{ margin: 0, fontSize: 18 }}>
              {detailFor.name} — detay
            </h2>
            <button className="btn btn-secondary" onClick={() => setDetailFor(null)}>
              <Icon name="close" />
              Kapat
            </button>
          </div>

          {!detail && <p className="muted">Yükleniyor…</p>}

          {detail && (
            <>
              <div className="admin-stats" style={{ marginTop: 12 }}>
                <div>
                  <span className="admin-stat-value">{detail.totalAnswered}</span>
                  <span className="admin-stat-label">Toplam çözüm</span>
                </div>
                <div>
                  <span className="admin-stat-value">
                    {pct(detail.totalCorrect, detail.totalAnswered)}
                  </span>
                  <span className="admin-stat-label">Doğru oranı</span>
                </div>
                <div>
                  <span className="admin-stat-value">{detail.exams.length}</span>
                  <span className="admin-stat-label">Tamamlanan deneme</span>
                </div>
                <div>
                  <span className="admin-stat-value">{detail.tasks.length}</span>
                  <span className="admin-stat-label">Pekiştirme görevi</span>
                </div>
              </div>

              <h3 style={{ fontSize: 16, margin: "18px 0 8px" }}>Zayıf konular</h3>
              {detail.weakTopics.length === 0 ? (
                <p className="muted">Henüz yanlış çözüm yok.</p>
              ) : (
                <ul className="admin-weak-list">
                  {detail.weakTopics.map((t) => (
                    <li key={t.label}>
                      <span>{t.label}</span>
                      <span className="admin-weak-count">{t.count} yanlış</span>
                    </li>
                  ))}
                </ul>
              )}

              <h3 style={{ fontSize: 16, margin: "18px 0 8px" }}>Deneme sonuçları</h3>
              {detail.exams.length === 0 ? (
                <p className="muted">Henüz deneme tamamlanmamış.</p>
              ) : (
                <ul className="admin-weak-list">
                  {detail.exams.map((e) => (
                    <li key={e.completed_at}>
                      <span>
                        {e.month === 0 ? "Seviye Tespit" : e.month + ". Ay Denemesi"} —{" "}
                        {fmtDate(e.completed_at)}
                      </span>
                      <span className="admin-weak-count">
                        {e.correct}D / {e.wrong}Y / {e.empty}B · %{e.percentage} · {e.level}
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <h3 style={{ fontSize: 16, margin: "18px 0 8px" }}>Yarım kalan denemeler</h3>
              {(detail.examSessions || []).length === 0 ? (
                <p className="muted">Yarım kalan deneme yok.</p>
              ) : (
                <ul className="admin-weak-list">
                  {detail.examSessions.map((e) => (
                    <li key={e.month + e.updatedAt}>
                      <span>
                        <strong>{e.label}</strong> — son işlem {fmtDate(e.updatedAt)}
                      </span>
                      <span className="admin-weak-count">
                        {e.answered}/{e.total} soru işaretlendi
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <h3 style={{ fontSize: 16, margin: "18px 0 8px" }}>Günlük çalışma (son günler)</h3>
              {(detail.studySessions || []).length === 0 ? (
                <p className="muted">Henüz günlük çalışma kaydı yok.</p>
              ) : (
                <ul className="admin-weak-list">
                  {detail.studySessions.map((r) => (
                    <li key={r.session_date}>
                      <span>{r.session_date}</span>
                      <span className="admin-weak-count">
                        {r.solved}/{r.target} soru · {r.correct} doğru
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      )}
    </main>
  );
}