"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { AvatarGender } from "./avatar";
import { ENROLLMENT_CHANGED_EVENT, setEnrollmentDate, setCycleAnchor, getCycleAnchor } from "../lib/cycle";
import {
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  apiFetch,
  pullAnswerRecords,
  pushAnswerRecord,
  pullReinforcementTasks,
  pushReinforcementTasks,
  pullBadgeProgress,
  pullWeeklyTestHistory,
} from "../lib/sync";
import { hydrateAnswerLog, loadAnswerRecords } from "../lib/error-reason";

export type Profile = {
  id: string;
  name: string;
  gender: AvatarGender;
  variant: number;
  /** Sisteme kayıt tarihi (ISO). Çalışma döngüsü buradan başlar. */
  registeredAt: string;
  /** Giriş için kullanıcı adı. */
  username?: string;
};

type ProfileContextValue = {
  /** Giriş yapılmış öğrencinin profili. */
  activeProfile: Profile | null;
  /** Sunucuyla konuşulduktan sonra true. */
  ready: boolean;
  /** Giriş yapılmamışsa true → giriş ekranı gösterilir. */
  needsProfileSelection: boolean;
  /** Giriş yap (kullanıcı adı + şifre). Hata fırlatır. */
  login: (username: string, password: string) => Promise<Profile>;
  /** Yeni öğrenci kaydı. Hata fırlatır. */
  register: (data: {
    username: string;
    password: string;
    name: string;
    gender: AvatarGender;
    variant: number;
  }) => Promise<Profile>;
  /** Çıkış yap. */
  logout: () => void;
  /** Profil güncelle (isim, karakter, şifre). */
  updateProfile: (updates: {
    name?: string;
    gender?: AvatarGender;
    variant?: number;
    password?: string;
  }) => Promise<void>;
  /** Uyumluluk: mevcut profil tek profildir. */
  profiles: Profile[];
  createProfile: (p: Omit<Profile, "id" | "registeredAt">) => Promise<Profile>;
  switchProfile: (id?: string) => Promise<void>;
  deleteProfile: (id?: string) => Promise<void>;
  getStorageKey: (baseKey: string) => string;
  syncProfileToSupabase: () => Promise<void>;
};

const ProfileContext = createContext<ProfileContextValue>({
  activeProfile: null,
  ready: false,
  needsProfileSelection: false,
  login: async () => {
    throw new Error("login kullanılamıyor");
  },
  register: async () => {
    throw new Error("register kullanılamıyor");
  },
  logout: () => {},
  updateProfile: async () => {},
  profiles: [],
  createProfile: async () => {
    throw new Error("createProfile kullanılamıyor");
  },
  switchProfile: async () => {},
  deleteProfile: async () => {},
  getStorageKey: (k) => k,
  syncProfileToSupabase: async () => {},
});

function toProfile(student: {
  id: string;
  username?: string;
  name: string;
  gender: string;
  variant: number;
  registeredAt: string;
}): Profile {
  return {
    id: student.id,
    username: student.username,
    name: student.name,
    gender: student.gender === "girl" ? "girl" : "boy",
    variant: student.variant,
    registeredAt: student.registeredAt,
  };
}

/** Kayıt tarihini sunucudan geri yükle (yerel temizlense bile döngü doğru kalsın). */
function restoreEnrollmentDate(registeredAt: unknown) {
  if (!registeredAt) return;
  const reg = new Date(String(registeredAt));
  if (!Number.isNaN(reg.getTime())) setEnrollmentDate(reg);
}

/**
 * Sunucudan gelen kayıtlarla yerel aynaları tazele.
 * Cihaz değiştirdiğinde öğrenci kaldığı yerden devam eder.
 */
async function hydrateMirrors(): Promise<void> {
  try {
    const [serverRecords, serverTasks, serverBadges, serverWeeklyTests] = await Promise.all([
      pullAnswerRecords(),
      pullReinforcementTasks(),
      pullBadgeProgress(),
      pullWeeklyTestHistory(),
    ]);

    // Cevap kayıtları: sunucu kaynak gerçek veri
    const mapped = serverRecords.map((r: Record<string, unknown>) => ({
      questionId: String(r.question_id ?? ""),
      subject: String(r.subject ?? ""),
      unit: (r.unit as number | null) ?? null,
      unitName: (r.unit_name as string | null) ?? null,
      topic: (r.topic as string | null) ?? null,
      selectedAnswer: String(r.selected_answer ?? ""),
      correct: !!r.correct,
      errorReasonCode: (r.error_reason_code as string | null) ?? null,
      timeSpentSec: Number(r.time_spent_sec) || 0,
      source: String(r.source ?? "gunluk"),
      createdAt: String(r.created_at ?? new Date().toISOString()),
    }));
    hydrateAnswerLog(mapped);

    // Pekiştirme görevleri: localStorage anahtarına yaz (reinforcement.ts okur)
    if (serverTasks.length > 0) {
      const tasks = serverTasks.map((t: Record<string, unknown>) => ({
        id: String(t.id),
        subject: String(t.subject ?? ""),
        unit: (t.unit as number | null) ?? null,
        unitName: (t.unit_name as string | null) ?? null,
        topic: String(t.topic ?? ""),
        source: String(t.source ?? "gunluk"),
        wrongCount: Number(t.wrong_count) || 0,
        createdAt: String(t.created_at ?? new Date().toISOString()),
        questionIds: (t.question_ids as string[]) ?? [],
        answers: (t.answers as Record<string, string | null>) ?? {},
        correctness: (t.correctness as Record<string, boolean | null>) ?? {},
        status: String(t.status ?? "bekliyor"),
        updatedAt: String(t.updated_at ?? new Date().toISOString()),
      }));
      window.localStorage.setItem("lgs_reinforcement_tasks", JSON.stringify(tasks));
    }

    // Rozet ilerlemesi: localStorage'a yaz (use-badge-progress okur) — sadece sunucuda earned=true olanları
    if (serverBadges && Object.keys(serverBadges).length > 0) {
      const earnedOnly: Record<string, { earned: boolean; earned_at: string | null; progress: number }> = {};
      for (const [k, v] of Object.entries(serverBadges)) {
        if (v.earned) earnedOnly[k] = { earned: true, earned_at: v.earned_at ?? null, progress: v.progress ?? 0 };
      }
      if (Object.keys(earnedOnly).length > 0) {
        window.localStorage.setItem("lgs_badge_progress", JSON.stringify(earnedOnly));
        window.dispatchEvent(new Event("lgs-badge-progress-changed"));
        window.dispatchEvent(new Event("lgs-answer-records-changed"));
      }
    }

    // Haftalık test geçmişi: localStorage'a yaz (weekly-test-history.ts okur)
    if (serverWeeklyTests && serverWeeklyTests.length > 0) {
      const mappedTests = serverWeeklyTests.map((t: Record<string, unknown>) => ({
        date: String(t.date ?? new Date().toISOString()),
        total: Number(t.total) || 0,
        correct: Number(t.correct) || 0,
        wrong: Number(t.wrong) || 0,
        blank: Number(t.blank) || 0,
        byCategory: t.by_category ?? {},
        weakUnits: t.weak_units ?? [],
        questionIds: t.question_ids ?? [],
        wrongQuestionIds: t.wrong_question_ids ?? [],
      }));
      window.localStorage.setItem("lgs_weekly_test_history", JSON.stringify(mappedTests.slice(-52)));
    }

    // Sınav durumu (exam_results = ana kaynak): yerel boşsa sunucudan geri yükle.
    // Çıkışta yerel temizlendiğinde veya cihaz değiştiğinde öğrenci kayıp yaşamaz.
    try {
      const statusRes = await apiFetch("/api/exams-status");
      if (statusRes.ok) {
        const status = await statusRes.json();
        const results: Array<Record<string, unknown>> = Array.isArray(status?.results)
          ? status.results
          : [];
        const completedMonths: number[] = Array.isArray(status?.completedMonths)
          ? status.completedMonths
          : [];

        // Tamamlanan aylar (deneme dropdown'ındaki ✓ işaretleri)
        let localDone: number[] = [];
        try {
          localDone = JSON.parse(window.localStorage.getItem("lgs_completed_exams") || "[]");
        } catch {
          localDone = [];
        }
        if ((!Array.isArray(localDone) || localDone.length === 0) && completedMonths.length > 0) {
          window.localStorage.setItem("lgs_completed_exams", JSON.stringify(completedMonths));
        }

        // Deneme geçmişi (Sonuçlar sayfası) — yerel yoksa sunucudan kur
        let localHistory: unknown[] = [];
        try {
          localHistory = JSON.parse(window.localStorage.getItem("lgs_exam_history") || "[]");
        } catch {
          localHistory = [];
        }
        if ((!Array.isArray(localHistory) || localHistory.length === 0) && results.length > 0) {
          const mapped = results.map((r) => ({
            date: String(r.completedAt ?? new Date().toISOString()),
            month: Number(r.month) || 0,
            monthName: String(r.monthName ?? ""),
            total: Number(r.total) || 0,
            correct: Number(r.correct) || 0,
            wrong: Number(r.wrong) || 0,
            empty: Number(r.empty) || 0,
            percentage: Number(r.percentage) || 0,
            level: String(r.level ?? ""),
            bySubject: r.bySubject ?? {},
            details: [],
          }));
          window.localStorage.setItem("lgs_exam_history", JSON.stringify(mapped.slice(-24)));
        }

        // Döngü anchor'u: seviye tespitinin (month 0) bitiş anından geri yükle
        if (getCycleAnchor() === null) {
          const m0 = results.find((r) => Number(r.month) === 0);
          const done = m0 ? new Date(String(m0.completedAt)) : null;
          if (done && !Number.isNaN(done.getTime())) setCycleAnchor(done);
        }
      }
    } catch {
      /* sınav durumu alınamazsa yerel ile devam */
    }
  } catch {
    /* ağ hatası: yerel ayna ile devam */
  }
}

/**
 * Eski yerel verileri (localStorage) ilk girişten sonra sunucuya taşı.
 * Bir kez çalışır; sonra temizlenir.
 */
async function migrateLegacyLocalData(): Promise<void> {
  try {
    const MIGRATED = "lgs_legacy_migrated";
    if (window.localStorage.getItem(MIGRATED)) return;

    const legacyRecords = loadAnswerRecords();
    if (legacyRecords.length > 0) {
      for (const r of legacyRecords) {
        pushAnswerRecord({ ...r, source: "gunluk" });
      }
      // Ateşle-unut çağrılar gönderildi; kısa bekleme sonrası işaretle
    }
    window.localStorage.setItem(MIGRATED, "1");
    window.localStorage.removeItem("lgs-ai-coach-profiles");
    window.localStorage.removeItem("lgs-ai-coach-active-profile");
    window.localStorage.removeItem("lgs-ai-coach-profile");
  } catch {
    /* yok say */
  }
}

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [activeProfile, setActiveProfile] = useState<Profile | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const handleEnrollmentChange = () => {
      setActiveProfile((p) => (p ? { ...p } : null));
    };
    window.addEventListener(ENROLLMENT_CHANGED_EVENT, handleEnrollmentChange);
    return () => window.removeEventListener(ENROLLMENT_CHANGED_EVENT, handleEnrollmentChange);
  }, []);

  // Açılışta token varsa öğrenciyi sunucudan getir
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!getAuthToken()) {
        setReady(true);
        return;
      }
      try {
        const res = await apiFetch("/api/auth/me");
        const data = await res.json();
        if (!cancelled && res.ok && data.student) {
          setActiveProfile(toProfile(data.student));
          restoreEnrollmentDate(data.student.registeredAt);
          await migrateLegacyLocalData();
          await hydrateMirrors();
        } else if (!cancelled) {
          clearAuthToken();
        }
      } catch {
        if (!cancelled) clearAuthToken();
      }
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const afterAuth = useCallback(async (token: string, student: Record<string, unknown>) => {
    setAuthToken(token);
    setActiveProfile(
      toProfile({
        id: String(student.id),
        username: student.username as string,
        name: String(student.name),
        gender: String(student.gender),
        variant: Number(student.variant) || 0,
        registeredAt: String(student.registeredAt),
      })
    );
    // Kayıt tarihini sunucudan geri yükle (yerel temizlense bile döngü doğru kalsın)
    restoreEnrollmentDate(student.registeredAt);
    await migrateLegacyLocalData();
    await hydrateMirrors();
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Giriş yapılamadı.");
      await afterAuth(data.token, data.student);
      return toProfile(data.student as Parameters<typeof toProfile>[0]);
    },
    [afterAuth]
  );

  const register = useCallback(
    async (input: {
      username: string;
      password: string;
      name: string;
      gender: AvatarGender;
      variant: number;
    }) => {
      const res = await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(input),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Kayıt yapılamadı.");
      await afterAuth(data.token, data.student);
      return toProfile(data.student as Parameters<typeof toProfile>[0]);
    },
    [afterAuth]
  );

  const logout = useCallback(() => {
    clearAuthToken();
    // Öğrenciye özel yerel verileri temizle: paylaşılan cihazda sıradaki öğrenci
    // öncekinin kayıtlarını görmesin. Sunucu ana kaynaktır; girişte geri yüklenir.
    const STUDENT_SCOPED_KEYS = [
      "lgs_answer_log",
      "lgs_reinforcement_tasks",
      "lgs_exam_history",
      "lgs_weekly_test_history",
      "lgs_completed_exams",
      "lgs_cycle_anchor",
      "lgs_enrollment_date",
      "lgs_badge_progress",
      "lgs_streak",
      "lgs-ai-coach-tasks",
      "lgs-ai-coach-game-session",
      "lgs-ai-coach-pomodoro-v1",
    ];
    try {
      for (const key of STUDENT_SCOPED_KEYS) window.localStorage.removeItem(key);
    } catch {
      /* depolama kapalıysa yok say */
    }
    setActiveProfile(null);
  }, []);

  const updateProfile = useCallback(
    async (updates: {
      name?: string;
      gender?: AvatarGender;
      variant?: number;
      password?: string;
    }) => {
      const res = await apiFetch("/api/auth/me", {
        method: "PATCH",
        body: JSON.stringify(updates),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Profil güncellenemedi.");
      if (data.student) setActiveProfile(toProfile(data.student));
    },
    []
  );

  // Uyumluluk sarmalayıcıları
  const createProfile = useCallback(async () => {
    throw new Error("Önce giriş yap / kayıt ol");
  }, []);
  const switchProfile = useCallback(async () => {
    logout();
  }, [logout]);
  const deleteProfile = useCallback(async () => {}, []);
  const getStorageKey = useCallback(
    (baseKey: string) => (activeProfile ? `lgs-${activeProfile.id}-${baseKey}` : baseKey),
    [activeProfile]
  );
  const syncProfileToSupabase = useCallback(async () => {}, []);

  const needsProfileSelection = ready && !activeProfile;

  const value = useMemo(
    () => ({
      activeProfile,
      ready,
      needsProfileSelection,
      login,
      register,
      logout,
      updateProfile,
      profiles: activeProfile ? [activeProfile] : [],
      createProfile,
      switchProfile,
      deleteProfile,
      getStorageKey,
      syncProfileToSupabase,
    }),
    [
      activeProfile,
      ready,
      needsProfileSelection,
      login,
      register,
      logout,
      updateProfile,
      createProfile,
      switchProfile,
      deleteProfile,
      getStorageKey,
      syncProfileToSupabase,
    ]
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile() {
  return useContext(ProfileContext);
}