"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { AvatarGender } from "./avatar";

export type Profile = {
  name: string;
  gender: AvatarGender;
  variant: number;
};

const STORAGE_KEY = "lgs-ai-coach-profile";

const defaultProfile: Profile = { name: "Öğrenci", gender: "boy", variant: 0 };

export function isProfile(value: unknown): value is Profile {
  if (!value || typeof value !== "object") return false;
  const p = value as Partial<Profile>;
  return (
    typeof p.name === "string" &&
    (p.gender === "girl" || p.gender === "boy") &&
    typeof p.variant === "number"
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
        if (isProfile(parsed)) setProfile(parsed);
      }
    } catch {
      /* bozuk kayıt: varsayılan profille devam */
    }
    setReady(true);
  }, []);

  const saveProfile = useCallback((next: Profile) => {
    const clean: Profile = { ...next, name: next.name.trim() || defaultProfile.name };
    setProfile(clean);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(clean));
    } catch {
      /* depolama kapalıysa yalnızca bellekte tut */
    }
  }, []);

  const value = useMemo(() => ({ profile, ready, saveProfile }), [profile, ready, saveProfile]);

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile() {
  return useContext(ProfileContext);
}
