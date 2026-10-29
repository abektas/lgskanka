"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { AvatarGender } from "./avatar";
import { getEnrollmentDate, setEnrollmentDate } from "../lib/cycle";

export type Profile = {
  name: string;
  gender: AvatarGender;
  variant: number;
  /** Sisteme kayıt tarihi (ISO). Çalışma döngüsü buradan başlar. */
  registeredAt?: string;
};

const STORAGE_KEY = "lgs-ai-coach-profile";

const defaultProfile: Profile = { name: "Öğrenci", gender: "boy", variant: 0 };

export function isProfile(value: unknown): value is Profile {
  if (!value || typeof value !== "object") return false;
  const p = value as Partial<Profile>;
  return (
    typeof p.name === "string" &&
    (p.gender === "girl" || p.gender === "boy") &&
    typeof p.variant === "number" &&
    (p.registeredAt === undefined || typeof p.registeredAt === "string")
  );
}

type ProfileContextValue = {
  profile: Profile;
  /** localStorage okunduktan sonra true olur (ilk boyamada yanlış içerik göstermemek için). */
  ready: boolean;
  saveProfile: (next: Profile) => void;
};

const ProfileContext = createContext<ProfileContextValue>({
  profile: defaultProfile,
  ready: false,
  saveProfile: () => {},
});

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile>(defaultProfile);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        if (isProfile(parsed)) {
          // Eski kayıtlar: registeredAt yoksa mevcut döngü tarihini koru,
          // yoksa bugünü kayıt tarihi say.
          const registeredAt =
            parsed.registeredAt ?? getEnrollmentDate().toISOString();

          if (!parsed.registeredAt) {
            const migrated = { ...parsed, registeredAt };
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(migrated));
          }

          setProfile({ ...parsed, registeredAt });
          // Kayıtlı öğrencinin döngüsü kayıt tarihinden başlar.
          setEnrollmentDate(new Date(registeredAt));
        }
      }
    } catch {
      /* bozuk kayıt: varsayılan profille devam */
    }
    setReady(true);
  }, []);

  const saveProfile = useCallback((next: Profile) => {
    // İlk kayıt = sisteme kaydolma. Döngü bugünden başlar.
    const registeredAt =
      next.registeredAt ?? new Date().toISOString();

    const clean: Profile = {
      ...next,
      name: next.name.trim() || defaultProfile.name,
      registeredAt,
    };
    setProfile(clean);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(clean));
    } catch {
      /* depolama kapalıysa yalnızca bellekte tut */
    }
    // Döngü başlangıcını kayıt tarihine sabitle
    setEnrollmentDate(new Date(registeredAt));
  }, []);

  const value = useMemo(() => ({ profile, ready, saveProfile }), [profile, ready, saveProfile]);

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile() {
  return useContext(ProfileContext);
}
