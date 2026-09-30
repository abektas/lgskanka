"use client";

import { Avatar } from "./avatar";
import { useProfile } from "./profile-provider";

/** Öğrencinin kayıtlı karakterini gösterir (sunucuda varsayılanla boyanır). */
export function CharacterAvatar({ size = 104 }: { size?: number }) {
  const { profile, ready } = useProfile();
  return (
    <Avatar
      gender={ready ? profile.gender : "boy"}
      variant={ready ? profile.variant : 0}
      size={size}
      label="Seçtiğin karakter"
    />
  );
}
