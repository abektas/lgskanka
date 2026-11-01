"use client";

import dynamic from "next/dynamic";

const ProfileGate = dynamic(
  () => import("./profile-gate").then((mod) => mod.ProfileGate),
  {
    ssr: false,
    loading: () => (
      <div style={{ display: "grid", placeItems: "center", minHeight: "100vh", background: "var(--zemin)" }}>
        <div className="spinner" />
      </div>
    ),
  }
);

export function ProfileGateWrapper({ children }: { children: React.ReactNode }) {
  return <ProfileGate>{children}</ProfileGate>;
}