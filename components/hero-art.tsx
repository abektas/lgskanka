"use client";

import Image from "next/image";
import { useProfile } from "./profile-provider";

/**
 * Kahraman görseli: öğrencinin seçtiği karaktere göre kız/erkek çizimi.
 * Görsel sunucudan varsayılan olarak (erkek) gönderilir, profil hazır olunca değişir.
 */
export function HeroArt() {
  const { profile, ready } = useProfile();
  const isGirl = ready && profile.gender === "girl";
  const src = isGirl ? "/art/hero-girl.webp" : "/art/hero-boy.webp";

  return (
    <div className="hero-art">
      <p className="hero-bubble">
        Bugün 3 görevimiz var!
        <span>Birlikte başaracağız 🚀</span>
      </p>
      <Image
        key={src}
        src={src}
        alt={
          isGirl
            ? "Ders masasında dizüstü bilgisayarla çalışan, yanında kedisi uyuyan öğrenci karakteri"
            : "Ders masasında dizüstü bilgisayarla çalışan, yanında kedisi olan öğrenci karakteri"
        }
        width={434}
        height={536}
        priority
        sizes="(max-width: 900px) 78vw, 380px"
        style={{ width: "100%", height: "auto", maxWidth: 380, marginTop: "auto" }}
      />
    </div>
  );
}
