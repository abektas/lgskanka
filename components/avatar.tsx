import Image from "next/image";

export type AvatarGender = "girl" | "boy";

const avatarImages: Record<AvatarGender, string[]> = {
  boy: [
    "/avatars/profile-boy-1.webp",
    "/avatars/profile-boy-2.webp",
    "/avatars/profile-boy-3.webp",
  ],
  girl: [
    "/avatars/profile-girl-1.webp",
    "/avatars/profile-girl-2.webp",
    "/avatars/profile-girl-3.webp",
  ],
};

const appearanceLabels: Record<AvatarGender, string[]> = {
  boy: ["kahverengi dalgalı saçlı", "siyah yan ayrık saçlı", "kıvırcık sarı saçlı"],
  girl: ["uzun kahverengi saçlı", "düz siyah saçlı", "topuz kızıl saçlı"],
};

type AvatarProps = {
  gender: AvatarGender;
  variant?: number;
  size?: number;
  className?: string;
  /** Ekran okuyucu için açıklama; boş bırakılırsa dekoratif sayılır. */
  label?: string;
};

/** Öğrenci karakterini seçilen 3D portreyle gösterir. */
export function Avatar({ gender, variant = 0, size = 88, className, label }: AvatarProps) {
  const index = ((Math.trunc(variant) % avatarImages[gender].length) + avatarImages[gender].length) % avatarImages[gender].length;

  return (
    <Image
      className={["student-avatar", className].filter(Boolean).join(" ")}
      src={avatarImages[gender][index]}
      width={size}
      height={size}
      alt={label ? `${label}: ${appearanceLabels[gender][index]}` : ""}
      aria-hidden={label ? undefined : true}
      draggable={false}
    />
  );
}
