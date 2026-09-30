/**
 * Satır içi SVG ikon seti.
 * Emoji yerine ölçeklenebilir, renklenebilir ve erişilebilir ikonlar (currentColor kullanır).
 */

export type IconName =
  | "home"
  | "target"
  | "robot"
  | "book"
  | "trophy"
  | "compass"
  | "star"
  | "chart"
  | "user"
  | "flame"
  | "bolt"
  | "play"
  | "camera"
  | "mic"
  | "gamepad"
  | "check"
  | "arrow"
  | "sparkle"
  | "shield";

const paths: Record<IconName, string> = {
  home: "M4 11.5 12 4.5l8 7M6.5 10.5V19h11v-8.5",
  target: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Zm0 4.5a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0 2.6a1.4 1.4 0 1 0 0 2.8 1.4 1.4 0 0 0 0-2.8Z",
  robot:
    "M12 3.6v2.1M7.4 5.7h9.2a2.6 2.6 0 0 1 2.6 2.6v6.4a2.6 2.6 0 0 1-2.6 2.6H7.4a2.6 2.6 0 0 1-2.6-2.6V8.3a2.6 2.6 0 0 1 2.6-2.6ZM3.2 10.2v3.4M20.8 10.2v3.4M9.4 10.6v1.6M14.6 10.6v1.6M9.8 14.6c1.5 1.1 2.9 1.1 4.4 0M12 17.5v3",
  book: "M4.5 5.2A1.7 1.7 0 0 1 6.2 3.5H19v14.2H6.2a1.7 1.7 0 0 0-1.7 1.7V5.2Zm0 12.6h14.5v2.7H6.2",
  trophy:
    "M8 4.3h8v4a4 4 0 0 1-8 0v-4ZM8 6H5.4v1.6a3 3 0 0 0 3 3M16 6h2.6v1.6a3 3 0 0 1-3 3M12 12.3v4M8.6 19.7h6.8M12 16.3v3.4",
  compass: "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17Zm3.4 5.1-2 5.8-5.8 2 2-5.8 5.8-2Z",
  star: "m12 3.8 2.6 5.3 5.9.8-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8L3.5 9.9l5.9-.8L12 3.8Z",
  chart: "M4.5 19.5h15M7.5 16V9.5M12 16V5.5M16.5 16v-4",
  user: "M12 11.8a3.9 3.9 0 1 0 0-7.8 3.9 3.9 0 0 0 0 7.8ZM5 20c.7-3.4 3.5-5.4 7-5.4S18.3 16.6 19 20",
  flame: "M12 20c3.3 0 5.5-2 5.5-5 0-4.4-5.5-6.4-4.4-11.8-2.6 1-4.9 3.5-4.9 6 0 1.3.5 2.2 1.2 2.9-1.4 0-2.5-1.2-2.6-2.6C6 11 6.5 12.9 6.5 15c0 3 2.2 5 5.5 5Z",
  bolt: "M13.4 3.5 6.8 13.4h4l-1.2 7.1 6.6-9.9h-4l1.2-7.1Z",
  play: "M8.5 5.8 18 12l-9.5 6.2V5.8Z",
  camera:
    "M4 8.6A2.1 2.1 0 0 1 6.1 6.5h1.3l1.2-2h6.8l1.2 2h1.3A2.1 2.1 0 0 1 20 8.6v8.3a2.1 2.1 0 0 1-2.1 2.1H6.1A2.1 2.1 0 0 1 4 16.9V8.6Zm8 7.9a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Z",
  mic: "M12 4.2a2.6 2.6 0 0 1 2.6 2.6v4.4a2.6 2.6 0 0 1-5.2 0V6.8A2.6 2.6 0 0 1 12 4.2ZM6.6 11.2a5.4 5.4 0 0 0 5.4 5.4 5.4 5.4 0 0 0 5.4-5.4M12 16.6v3.2M9.2 19.8h5.6",
  gamepad:
    "M8.4 8.2h7.2a5.4 5.4 0 0 1 5.4 5.4v.6a3.4 3.4 0 0 1-6.2 1.9l-.5-.8H9.7l-.5.8A3.4 3.4 0 0 1 3 14.2v-.6a5.4 5.4 0 0 1 5.4-5.4ZM7.3 11.6v2M6.3 12.6h2M15.7 11.9h.01M17.8 12.9h.01",
  check: "m5.5 12.8 4.2 4.2 8.8-9.6",
  arrow: "M5 12h13.5M13 6.5l5.5 5.5-5.5 5.5",
  sparkle: "M12 3.8 13.6 9l5.2 1.6-5.2 1.6L12 17.4l-1.6-5.2L5.2 10.6 10.4 9 12 3.8ZM18.5 16.2l.6 1.9 1.9.6-1.9.6-.6 1.9-.6-1.9-1.9-.6 1.9-.6.6-1.9Z",
  shield: "M12 3.6 19 6v6c0 4-2.9 7-7 8.4C7 19 4 16 4 12V6l8-2.4Z",
};

type IconProps = {
  name: IconName;
  size?: number;
  className?: string;
  /** Bilgi verici ikonlarda ekran okuyucular için etiket; dekoratifse boş bırakın. */
  label?: string;
};

export function Icon({ name, size = 22, className, label }: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={label ? undefined : true}
      role={label ? "img" : undefined}
      aria-label={label}
      focusable="false"
    >
      <path d={paths[name]} />
    </svg>
  );
}
