"use client";

import { Avatar } from "./avatar";
import { useProfile } from "./profile-provider";

/** Öğrencinin kayıtlı karakterini gösterir (sunucuda varsayılanla boyanır). */
export function CharacterAvatar({ size = 104 }: { size?: number }) {
  const { activeProfile, ready } = useProfile();
  return (
    <Avatar
      gender={ready && activeProfile ? activeProfile.gender : "boy"}
      variant={ready && activeProfile ? activeProfile.variant : 0}
      size={size}
      label="Seçtiğin karakter"
    />
  );
}