"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { AvatarGender } from "./avatar";
import { setEnrollmentDate, ENROLLMENT_CHANGED_EVENT } from "../lib/cycle";
import {
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  apiFetch,
  pullAnswerRecords,
  pushAnswerRecord,
  pullReinforcementTasks,
  pushReinforcementTasks,
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

/**
 * Sunucudan gelen kayıtlarla yerel aynaları tazele.
 * Cihaz değiştirdiğinde öğrenci kaldığı yerden devam eder.
 */
async function hydrateMirrors(): Promise<void> {
  try {
    const [serverRecords, serverTasks] = await Promise.all([
      pullAnswerRecords(),
      pullReinforcementTasks(),
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

  // Kayıt tarihi → çalışma döngüsü
  useEffect(() => {
    if (activeProfile) {
      setEnrollmentDate(new Date(activeProfile.registeredAt));
    }
  }, [activeProfile?.registeredAt]);

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