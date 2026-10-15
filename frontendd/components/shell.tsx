"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, createContext, useContext } from "react";
import { api, post, resetAuth, setCompany } from "@/lib/api";
import type { Company, Me, Page } from "@/lib/types";
import { ErrorNotice } from "./ui";
const CompanyContext = createContext("");
const ManagementContext = createContext(false);
export const useCompany = () => useContext(CompanyContext);
export const useCanManageIntegration = () => useContext(ManagementContext);
export default function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const cache = useQueryClient();
  const [chosen, setActive] = useState("");
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/api/auth/me/"),
    retry: false,
  });
  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: async () => {
      const data = await api<Page<Company>>("/api/companies/");
      setCompany(
        data.results.find((c) => c.id === me.data?.active_company)?.id ??
          data.results[0]?.id ??
          null,
      );
      return data;
    },
    enabled: !!me.data,
  });
  useEffect(() => {
    if (me.isError) router.replace("/login");
  }, [me.isError, router]);
  const active =
    chosen ||
    companies.data?.results.find((c) => c.id === me.data?.active_company)?.id ||
    companies.data?.results[0]?.id ||
    "";
  async function switchCompany(id: string) {
    setSwitching(true);
    setError(null);
    try {
      const selected = await post<{
        ok: boolean;
        role: Me["active_company_role"];
      }>(`/api/companies/${id}/select/`);
      await cache.cancelQueries();
      cache.removeQueries({
        predicate: (q) => !["me", "companies"].includes(String(q.queryKey[0])),
      });
      setCompany(id);
      setActive(id);
      cache.setQueryData<Me>(["me"], (old) =>
        old
          ? { ...old, active_company: id, active_company_role: selected.role }
          : old,
      );
    } catch (err) {
      setError(err);
    } finally {
      setSwitching(false);
    }
  }
  if (!me.data || !companies.data)
    return (
      <main className="loading">
        Ачаалж байна…
        <ErrorNotice error={companies.error} />
      </main>
    );
  return (
    <div className="app-shell">
      <AppSidebar pathname={pathname} />
      <div className="main-area">
        <AppHeader
          pathname={pathname}
          active={active}
          companies={companies.data.results}
          switching={switching}
          username={me.data.username}
          onCompanyChange={switchCompany}
          onLogout={async () => {
            try {
              await post("/api/auth/logout/");
              resetAuth();
              cache.clear();
              router.replace("/login");
            } catch (err) {
              setError(err);
            }
          }}
        />
        <ErrorNotice error={error} />
        {companies.data.results.length === 0 ? (
          <CreateCompany onCreated={() => void companies.refetch()} />
        ) : active && !switching ? (
          <ManagementContext.Provider
            value={
              me.data.active_company_role === "OWNER" ||
              me.data.active_company_role === "ADMIN"
            }
          >
            <CompanyContext.Provider value={active}>
              <main className="content" key={active}>
                {children}
              </main>
            </CompanyContext.Provider>
          </ManagementContext.Provider>
        ) : (
          <p>Ачаалж байна…</p>
        )}
      </div>
    </div>
  );
}

type NavigationItem = [href: string, icon: string, label: string];

const navigation: { label: string; items: NavigationItem[] }[] = [
  {
    label: "Харилцагч",
    items: [
      ["/inbox", "✦", "Мессеж"],
      ["/posts", "▤", "Нийтлэл"],
    ],
  },
  { label: "Тохиргоо", items: [["/settings/integrations", "⚙", "Холболтууд"]] },
];

export function AppSidebar({ pathname }: { pathname: string }) {
  return (
    <aside className="sidebar">
      <Link className="brand" href="/inbox">
        <span className="brand-icon">O</span>OrderHub
      </Link>
      <nav aria-label="Үндсэн цэс">
        {navigation.map((group) => (
          <section className="nav-group" key={group.label}>
            <p className="eyebrow">{group.label}</p>
            {group.items.map(([href, icon, label]) => (
              <Link
                key={href}
                href={href}
                className={pathname.startsWith(href) ? "active" : ""}
              >
                <span aria-hidden="true">{icon}</span>
                {label}
              </Link>
            ))}
          </section>
        ))}
      </nav>
      <div className="sidebar-footer">
        <span className="status-dot" /> Social workspace
      </div>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navigation
          .flatMap((group) => group.items)
          .map(([href, icon, label]) => (
            <Link
              key={href}
              href={href}
              className={pathname.startsWith(href) ? "active" : ""}
            >
              <span aria-hidden="true">{icon}</span>
              <small>{label}</small>
            </Link>
          ))}
      </nav>
    </aside>
  );
}

export function AppHeader({
  pathname,
  active,
  companies,
  switching,
  username,
  onCompanyChange,
  onLogout,
}: {
  pathname: string;
  active: string;
  companies: Company[];
  switching: boolean;
  username: string;
  onCompanyChange: (id: string) => Promise<void>;
  onLogout: () => Promise<void>;
}) {
  const title = pathname.startsWith("/posts")
    ? "Нийтлэл"
    : pathname.startsWith("/settings")
      ? "Холболтууд"
      : "Мессеж";
  return (
    <header className="topbar">
      <div className="topbar-context">
        <span className="eyebrow">ORDERHUB / {title}</span>
        <strong>{title}</strong>
      </div>
      <div className="topbar-actions">
        <label className="company-switcher">
          <span className="sr-only">Компани</span>
          <select
            aria-label="Компани"
            value={active}
            disabled={switching}
            onChange={(e) => void onCompanyChange(e.target.value)}
          >
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </label>
        <span className="user-name">{username}</span>
        <button className="quiet" onClick={() => void onLogout()}>
          Гарах
        </button>
      </div>
    </header>
  );
}
function CreateCompany({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<unknown>(null);
  return (
    <form
      className="card onboarding"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await post("/api/companies/", { name, slug });
          onCreated();
        } catch (err) {
          setError(err);
        }
      }}
    >
      <h1>Компаниа үүсгэх</h1>
      <label>
        Нэр
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label>
        Товч нэр (латин үсэг)
        <input
          required
          pattern="[a-z0-9-]+"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
        />
      </label>
      <button className="primary">Үүсгэх</button>
      <ErrorNotice error={error} />
    </form>
  );
}
