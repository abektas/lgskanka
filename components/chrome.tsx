"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Avatar } from "./avatar";
import { Icon } from "./icons";
import { SearchBox } from "./search-box";
import { useProfile } from "./profile-provider";
import { learner, navItems } from "../data/nav";
import { useLearnerStats } from "../lib/learner-stats";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function Sidebar() {
  const pathname = usePathname();
  const stats = useLearnerStats();

  return (
    <aside className="side" aria-label="Ana menü">
      <div className="side-brand">
        <span className="side-brand-mark" aria-hidden="true">
          🎓
        </span>
        <span>
          <b>LGS KANKA</b>
          <small>Senin yol arkadaşın</small>
        </span>
      </div>

      <nav className="side-nav" aria-label="Sayfalar">
        {navItems.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link${active ? " is-active" : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className="nav-ico" aria-hidden="true">
                <Icon name={item.icon} size={18} />
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="side-card">
        <span className="side-emoji" aria-hidden="true">
          🏅
        </span>
        <b>Bugün harika gidiyorsun!</b>
        <small>
          {(stats?.streakDays ?? learner.streakDays)} günlük serin var. Hedefine bir adım daha yaklaştın.
        </small>
      </div>

      <p className="side-foot">
        Öğrenme verisi (hata türü, konu, mastery) tarayıcıda saklanır; ham görüntü/ses tutulmaz.
      </p>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  const items = navItems.filter((item) => item.mobile);

  return (
    <nav className="mobile-nav" aria-label="Hızlı menü">
      {items.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={active ? "is-active" : undefined}
            aria-current={active ? "page" : undefined}
          >
            <Icon name={item.icon} size={20} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function TopBar({ query }: { query?: string }) {
  const { activeProfile, ready } = useProfile();
  const stats = useLearnerStats();
  const streakDays = stats?.streakDays ?? learner.streakDays;
  const xp = stats?.xp ?? learner.xp;
  const level = stats?.level ?? learner.level;
  const levelXp = stats?.levelXp ?? learner.levelXp;
  const levelTarget = stats?.levelTarget ?? learner.levelTarget;
  const percent = Math.round((levelXp / Math.max(1, levelTarget)) * 100);

  return (
    <div className="topbar">
      <SearchBox initialQuery={query} />

      <div className="topbar-stats">
        <span className="pill is-flame">
          <span aria-hidden="true">🔥</span> {streakDays} gün seri
        </span>
        <span className="pill is-xp">
          <span aria-hidden="true">⭐</span> {xp} XP
        </span>

        <div className="level">
          <div className="level-text">
            <b>Seviye {level}</b>
            <span className="level-xp">
              {levelXp} / {levelTarget} XP
            </span>
          </div>
          <div
            className="bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={levelTarget}
            aria-valuenow={levelXp}
            aria-label="Seviye ilerlemesi"
          >
            <i style={{ width: `${percent}%` }} />
          </div>
        </div>

        <Link href="/profil" className="avatar-btn" aria-label="Profilim ve karakterim">
          <Avatar
            gender={ready && activeProfile ? activeProfile.gender : "boy"}
            variant={ready && activeProfile ? activeProfile.variant : 0}
            size={40}
            className="topbar-avatar"
          />
        </Link>
      </div>
    </div>
  );
}