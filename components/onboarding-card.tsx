"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Icon } from "../components/icons";
import { useProfile } from "../components/profile-provider";
import { getEnrollmentDate } from "../lib/cycle";

/** Ana sayfa onboarding kartı — seviye tespit sınavı henüz yapılmamışsa gösterilir. */
export function OnboardingCard() {
  const { activeProfile, ready, getStorageKey } = useProfile();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [enrollmentDate, setEnrollmentDate] = useState<Date | null>(null);

  useEffect(() => {
    if (!ready || !activeProfile) return;

    // Kayıt tarihini al
    const enrolled = getEnrollmentDate();
    setEnrollmentDate(enrolled);

    // Profil-scoped tamamlanmış sınavları kontrol et
    const storageKey = getStorageKey("completed_exams");
    try {
      const raw = window.localStorage.getItem(storageKey);
      const completed: number[] = raw ? JSON.parse(raw) : [];
      // Ay 0 (seviye tespit) tamamlanmamışsa onboarding göster
      if (!completed.includes(0)) {
        setShowOnboarding(true);
      }
    } catch {
      setShowOnboarding(true); // Hata durumunda güvenli tarafta olsun
    }
  }, [ready, activeProfile, getStorageKey]);

  if (!showOnboarding || !activeProfile) return null;

  const daysSinceEnrollment = enrollmentDate
    ? Math.max(
        0,
        Math.floor(
          (new Date().setHours(0, 0, 0, 0) - new Date(enrollmentDate).setHours(0, 0, 0, 0)) /
            86400000
        )
      )
    : 0;

  return (
    <section className="card onboarding-card" aria-labelledby="onboarding-title">
      <div className="onboarding-icon" aria-hidden="true">🎯</div>
      <div className="onboarding-content">
        <h2 id="onboarding-title">Hoş geldin, {activeProfile.name}!</h2>
        <p className="onboarding-subtitle">
          Kayıt tarihinden itibaren <strong>{daysSinceEnrollment} gün</strong> geçti.
          LGS'ye hazırlığın seviyesini tespit etmek için <strong>Seviye Tespit Sınavı</strong> ile başla.
        </p>
        <p className="onboarding-desc">
          Bu 90 dakikalık deneme (90 soru), güncel müfredata uygun olarak hazırlanmıştır.
          Sonuçların pekiştirme planını ve haftalık/aylık takvimi şekillendirecek.
        </p>
        <Link className="btn btn-primary btn-lg" href="/aylik-denemeler?month=0">
          <Icon name="play" size={20} />
          Seviye Tespit Sınavını Başlat
        </Link>
        <p className="onboarding-note">
          Daha sonra <Link href="/aylik-denemeler">Aylık Denemeler sayfasından</Link> da erişebilirsin.
        </p>
      </div>
    </section>
  );
}