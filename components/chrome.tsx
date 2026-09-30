"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Avatar } from "./avatar";
import { Icon } from "./icons";
import { SearchBox } from "./search-box";
import { useProfile } from "./profile-provider";
import { learner, navItems } from "../data/nav";

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="side" aria-label="Ana menü">
      <div className="side-brand">
        <span className="side-brand-mark" aria-hidden="true">
          🎓
        </span>
        <span>
          <b>LGS AI KOÇ</b>
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
          {learner.streakDays} günlük serin var. Hedefine bir adım daha yaklaştın.
        </small>
      </div>

      <p className="side-foot">
        Ses ve fotoğraflar yalnızca analiz için kullanılır, analiz bitince silinir.
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
  const { profile, ready } = useProfile();
  const percent = Math.round((learner.levelXp / learner.levelTarget) * 100);

  return (
    <div className="topbar">
      <SearchBox initialQuery={query} />

      <div className="topbar-stats">
        <span className="pill is-flame">
          <span aria-hidden="true">🔥</span> {learner.streakDays} gün seri
        </span>
        <span className="pill is-xp">
          <span aria-hidden="true">⭐</span> {learner.xp} XP
        </span>

        <div className="level">
          <div className="level-text">
            <b>Seviye {learner.level}</b>
            <span className="level-xp">
              {learner.levelXp} / {learner.levelTarget} XP
            </span>
          </div>
          <div
            className="bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={learner.levelTarget}
            aria-valuenow={learner.levelXp}
            aria-label="Seviye ilerlemesi"
          >
            <i style={{ width: `${percent}%` }} />
          </div>
        </div>

        <Link href="/profil" className="avatar-btn" aria-label="Profilim ve karakterim">
          <Avatar
            gender={ready ? profile.gender : "boy"}
            variant={ready ? profile.variant : 0}
            size={40}
            className="topbar-avatar"
          />
        </Link>
      </div>
    </div>
  );
}
