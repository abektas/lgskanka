import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "../../components/icons";
import { GameCenter } from "../../components/game-center";
import { badges } from "../../data/content";
import { learner, xpRules } from "../../data/nav";
import { OdullerClient } from "./OdullerClient";

export const metadata: Metadata = {
  title: "Ödüller ve oyun merkezi",
  description:
    "XP kuralları, rozetler ve oyun merkezi. Ödüller doğru cevaptan çok düzenli çalışma, hata analizi ve gerçek gelişim davranışlarına bağlanır.",
  alternates: { canonical: "/oduller" },
};

export default function OdullerPage() {
  return <OdullerClient />;
}
