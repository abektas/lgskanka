"use client";

import { useProfile } from "./profile-provider";

/** Öğrencinin adını gösterir; sunucu tarafında varsayılan ad basılır (SEO ve ilk boyama için). */
export function Greeting() {
  const { profile } = useProfile();
  return <>{profile.name}</>;
}
