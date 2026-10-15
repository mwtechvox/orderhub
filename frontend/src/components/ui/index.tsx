import type { ButtonHTMLAttributes, ReactNode } from "react";
import { ApiError } from "@/lib/api-client";
import { initials } from "@/lib/formatters";
import Icon, { type IconName } from "./Icon";

export function Button({
  children,
  variant = "secondary",
  icon,
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "quiet" | "danger" | "icon";
  icon?: IconName;
}) {
  return (
    <button type={type} className={`button button-${variant} ${className}`} {...props}>
      {icon && <Icon name={icon} />} {children}
    </button>
  );
}

export function Avatar({
  name,
  size = "md",
  store = false,
}: {
  name?: string;
  size?: "sm" | "md" | "lg" | "xl";
  store?: boolean;
}) {
  return (
    <span className={`avatar avatar-${size} ${store ? "avatar-store" : "avatar-cyan"}`}>
      {store ? initials(name || "O") : initials(name)}
    </span>
  );
}

export function PlatformBadge({
  platform = "FACEBOOK_PAGE",
  compact = false,
}: {
  platform?: string;
  compact?: boolean;
}) {
  const label = platform === "FACEBOOK_PAGE" ? "Facebook" : platform;
  return (
    <span className={`platform-badge ${compact ? "compact" : ""}`}>
      <b>{platform === "FACEBOOK_PAGE" ? "f" : "•"}</b>
      {!compact && label}
    </span>
  );
}

export function StatusBadge({
  tone,
  children,
}: {
  tone: "success" | "warning" | "danger" | "neutral";
  children: ReactNode;
}) {
  return (
    <span className={`status-badge status-${tone}`}>
      <span className="status-dot" />
      {children}
    </span>
  );
}

export function LoadingState({ children = "Ачаалж байна…" }: { children?: ReactNode }) {
  return (
    <div className="state-card state-loading">
      <span className="loading-spinner" />
      {children}
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="state-card">
      <strong>{title}</strong>
      {description && <p>{description}</p>}
    </div>
  );
}

export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "Алдаа гарлаа. Дахин оролдоно уу.";
  return (
    <div className="feedback danger" role="alert">
      <Icon name="warning" />
      <span>
        <strong>Хүсэлт амжилтгүй</strong>
        <small>{message}</small>
      </span>
    </div>
  );
}

export function Pager({
  page,
  count,
  onChange,
}: {
  page: number;
  count: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / 25));
  if (pages <= 1) return null;
  return (
    <div className="pagination">
      <Button icon="arrow" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Өмнөх
      </Button>
      <span>
        <button className="active">{page}</button>
        <i>/</i>
        <button>{pages}</button>
      </span>
      <Button disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Дараах <span className="right-arrow">→</span>
      </Button>
    </div>
  );
}
