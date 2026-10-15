"use client";

import type { Account } from "@/lib/types";

export const ALL_CHANNELS = "";

const platformLabels: Record<string, string> = {
  FACEBOOK_PAGE: "Facebook",
  INSTAGRAM: "Instagram",
};

export function platformLabel(platform: string) {
  return platformLabels[platform] ?? platform.replaceAll("_", " ");
}

export function PlatformBadge({ platform }: { platform: string }) {
  return (
    <span className={`platform-badge platform-${platform.toLowerCase()}`}>
      <span aria-hidden="true">{platform === "FACEBOOK_PAGE" ? "f" : "•"}</span>
      {platformLabel(platform)}
    </span>
  );
}

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "success" | "warning" | "danger" | "neutral";
}) {
  return <span className={`status-badge status-${tone}`}>{children}</span>;
}

export function ChannelSelector({
  value,
  platforms,
  onChange,
}: {
  value: string;
  platforms: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="filter-control">
      <span>Суваг</span>
      <select
        aria-label="Суваг"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value={ALL_CHANNELS}>Бүх суваг</option>
        {platforms.map((platform) => (
          <option key={platform} value={platform}>
            {platformLabel(platform)}
          </option>
        ))}
      </select>
    </label>
  );
}

export function AccountSelector({
  value,
  accounts,
  platform,
  onChange,
}: {
  value: string;
  accounts: Account[];
  platform: string;
  onChange: (value: string) => void;
}) {
  const options = platform
    ? accounts.filter((account) => account.platform === platform)
    : accounts;
  return (
    <label className="filter-control">
      <span>Хаяг</span>
      <select
        aria-label="Хаяг"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Бүх хаяг</option>
        {options.map((account) => (
          <option key={account.id} value={account.id}>
            {account.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}

export function FilterBar({ children }: { children: React.ReactNode }) {
  return <div className="filter-bar">{children}</div>;
}
