/**
 * Öğrenci avatarları — satır içi SVG (dosya yok, her boyutta net).
 * Cinsiyet başına 3 varyant: saç, ten ve kapüşonlu renkleri farklı.
 * Sunucu bileşeni olarak da kullanılabilir (durum tutmaz).
 */

export type AvatarGender = "girl" | "boy";

type Variant = {
  bg: [string, string];
  skin: string;
  shade: string;
  hair: string;
  hoodie: string;
  hoodieShade: string;
  style: "dalga" | "ayrik" | "topuz";
  longHair: boolean;
  label: string;
};

const variants: Record<AvatarGender, Variant[]> = {
  boy: [
    {
      bg: ["#E4ECFF", "#D6F5EC"],
      skin: "#F5C39B",
      shade: "#E5AB80",
      hair: "#5A3A28",
      hoodie: "#FFFFFF",
      hoodieShade: "#E7E9F7",
      style: "dalga",
      longHair: false,
      label: "kısa dalgalı kahverengi saç",
    },
    {
      bg: ["#FFEAF3", "#E6E9FF"],
      skin: "#E8AE80",
      shade: "#D29A6E",
      hair: "#241C1A",
      hoodie: "#C9F0E4",
      hoodieShade: "#A9DCCB",
      style: "ayrik",
      longHair: false,
      label: "siyah yan ayrık saç",
    },
    {
      bg: ["#FFF3D6", "#E3F3FF"],
      skin: "#F7CDA6",
      shade: "#E7B488",
      hair: "#C9832F",
      hoodie: "#D9D2FF",
      hoodieShade: "#BCB1F5",
      style: "topuz",
      longHair: false,
      label: "kıvırcık sarı saç",
    },
  ],
  girl: [
    {
      bg: ["#FFE6F0", "#E6ECFF"],
      skin: "#F7CBA6",
      shade: "#E8B388",
      hair: "#5B3626",
      hoodie: "#FFFFFF",
      hoodieShade: "#F0E4F2",
      style: "dalga",
      longHair: true,
      label: "uzun kahverengi saç",
    },
    {
      bg: ["#E9FBEF", "#FFF0DC"],
      skin: "#E8B189",
      shade: "#D29B76",
      hair: "#2A1F1C",
      hoodie: "#FFD6E7",
      hoodieShade: "#F5BBD4",
      style: "ayrik",
      longHair: true,
      label: "siyah düz saç",
    },
    {
      bg: ["#F0EBFF", "#DFF3FF"],
      skin: "#FBD9B6",
      shade: "#EDC297",
      hair: "#B9772C",
      hoodie: "#C9F0E4",
      hoodieShade: "#A6DCC9",
      style: "topuz",
      longHair: true,
      label: "topuzlu kızıl saç",
    },
  ],
};

const HAIR_CAP =
  "M50 104C48 62 72 40 100 40s52 22 50 64c-6-18-16-28-30-32-8 7-22 9-32 3-10-6-22-4-30 6-4 5-7 12-8 23Z";

type AvatarProps = {
  gender: AvatarGender;
  variant?: number;
  size?: number;
  className?: string;
  /** Ekran okuyucu için açıklama; boş bırakılırsa dekoratif sayılır. */
  label?: string;
};

export function Avatar({ gender, variant = 0, size = 88, className, label }: AvatarProps) {
  const v = variants[gender][variant % variants[gender].length];
  const gradientId = `avatar-${gender}-${variant % variants[gender].length}`;

  return (
    <svg
      className={className}
      width={size}
      height={size * 1.1}
      viewBox="0 0 200 220"
      role={label ? "img" : undefined}
      aria-label={label ? `${gender === "girl" ? "Kız" : "Erkek"} öğrenci avatarı: ${v.label}` : undefined}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor={v.bg[0]} />
          <stop offset="1" stopColor={v.bg[1]} />
        </linearGradient>
      </defs>

      <rect width="200" height="220" rx="52" fill={`url(#${gradientId})`} />

      {v.longHair && (
        <>
          <path d="M52 92c-14 26-12 60-4 82h18c-10-24-10-52-2-74Z" fill={v.hair} />
          <path d="M148 92c14 26 12 60 4 82h-18c10-24 10-52 2-74Z" fill={v.hair} />
        </>
      )}

      {/* kapüşonlu üst */}
      <path d="M32 220c0-34 30-54 68-54s68 20 68 54Z" fill={v.hoodie} />
      <path d="M32 220c0-34 30-54 68-54v54Z" fill={v.hoodieShade} opacity=".35" />
      <path d="M92 167c3 10 13 10 16 0" stroke={v.hoodieShade} strokeWidth="4" fill="none" strokeLinecap="round" />
      <path d="M88 176v20M112 176v20" stroke={v.hoodieShade} strokeWidth="4" strokeLinecap="round" />

      {/* boyun + kulaklar */}
      <rect x="88" y="132" width="24" height="34" rx="12" fill={v.shade} />
      <circle cx="52" cy="108" r="12" fill={v.skin} />
      <circle cx="148" cy="108" r="12" fill={v.skin} />

      {/* yüz */}
      <rect x="54" y="50" width="92" height="102" rx="46" fill={v.skin} />

      {/* saç */}
      <path d={HAIR_CAP} fill={v.hair} />
      {v.style === "topuz" && <circle cx="100" cy="34" r="21" fill={v.hair} />}
      {v.style === "ayrik" && (
        <path d="M104 44c18 4 30 16 34 34-2-22-14-38-34-44Z" fill={v.hair} opacity=".55" />
      )}
      {v.style === "dalga" && (
        <path d="M126 52c14 8 22 22 22 40-4-18-12-30-26-36Z" fill={v.hair} opacity=".5" />
      )}

      {/* kaşlar */}
      <path d="M70 96c4-4 12-4 16 0M114 96c4-4 12-4 16 0" stroke={v.hair} strokeWidth="4.5" strokeLinecap="round" />

      {/* gözler */}
      {[79, 121].map((cx) => (
        <g key={cx}>
          <ellipse cx={cx} cy={110} rx="9.5" ry="11.5" fill="#2A2344" />
          <circle cx={cx - 3} cy={105} r="3.2" fill="#FFFFFF" />
          <circle cx={cx + 3.4} cy={114} r="1.8" fill="#FFFFFF" opacity=".7" />
        </g>
      ))}

      {/* yanaklar + gülümseme */}
      <ellipse cx="63" cy="124" rx="10" ry="6.5" fill="#FF89B0" opacity=".35" />
      <ellipse cx="137" cy="124" rx="10" ry="6.5" fill="#FF89B0" opacity=".35" />
      <path d="M89 126c4 6 18 6 22 0" stroke="#B4574F" strokeWidth="4.4" fill="none" strokeLinecap="round" />
    </svg>
  );
}
