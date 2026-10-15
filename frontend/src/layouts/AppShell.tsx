import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post, setActiveCompany } from "@/lib/api-client";
import type { Company, Me, Page } from "@/types/api";
import { Avatar, Button, ErrorNotice, LoadingState } from "@/components/ui";
import Icon, { type IconName } from "@/components/ui/Icon";
import { useAuth } from "@/features/auth/AuthContext";
import { WorkspaceProvider } from "@/features/companies/WorkspaceContext";

const navigation: { to: string; label: string; icon: IconName }[] = [
  { to: "/inbox", label: "Мессеж", icon: "message" },
  { to: "/posts", label: "Нийтлэл", icon: "posts" },
  { to: "/settings/integrations", label: "Холболтууд", icon: "link" },
];

const titles: Record<string, string> = {
  inbox: "Мессеж",
  posts: "Нийтлэл",
  settings: "Холболтууд",
};

export default function AppShell() {
  const { user, setUser, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const [error, setError] = useState<unknown>(null);
  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: () => api<Page<Company>>("/api/companies/"),
  });
  const active =
    companies.data?.results.find((item) => item.id === user?.active_company) ??
    companies.data?.results[0];
  if (!user || companies.isLoading) return <LoadingState />;
  if (companies.error)
    return (
      <main className="fatal-state">
        <ErrorNotice error={companies.error} />
      </main>
    );
  if (!active)
    return (
      <CreateCompany
        onCreated={async () => {
          await companies.refetch();
        }}
      />
    );
  setActiveCompany(active.id);
  const role =
    user.active_company === active.id && user.active_company_role
      ? user.active_company_role
      : "AGENT";
  const title = titles[location.pathname.split("/")[1] || "inbox"] ?? "OrderHub";

  async function switchCompany(id: string) {
    setError(null);
    try {
      const selected = await post<{
        ok: boolean;
        role: Me["active_company_role"];
      }>(`/api/companies/${id}/select/`);
      setActiveCompany(id);
      setUser((current) =>
        current
          ? {
              ...current,
              active_company: id,
              active_company_role: selected.role,
            }
          : current,
      );
      cache.removeQueries({
        predicate: (query) => query.queryKey[0] !== "companies",
      });
      navigate("/inbox");
    } catch (reason) {
      setError(reason);
    }
  }

  return (
    <WorkspaceProvider companyId={active.id} role={role}>
      <div className="app-shell">
        <aside className="sidebar">
          <NavLink className="brand" to="/inbox">
            <span className="brand-mark">
              <span />
              <span />
              <span />
            </span>
            <strong>OrderHub</strong>
          </NavLink>
          <nav>
            <p className="nav-label">ХАРИЛЦАГЧ</p>
            {navigation.slice(0, 2).map((item) => (
              <NavLink
                key={item.to}
                className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
                to={item.to}
              >
                <Icon name={item.icon} />
                {item.label}
              </NavLink>
            ))}
            <p className="nav-label nav-label-spaced">ТОХИРГОО</p>
            <NavLink
              className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
              to={navigation[2].to}
            >
              <Icon name="link" />
              Холболтууд
            </NavLink>
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-user">
              <Avatar name={user.username} size="sm" />
              <span>
                <strong>{user.username}</strong>
                <small>{role}</small>
              </span>
              <Button
                variant="icon"
                icon="logout"
                aria-label="Гарах"
                onClick={() => void signOut()}
              />
            </div>
          </div>
        </aside>
        <div className="app-main">
          <header className="app-header">
            <div className="mobile-brand">
              <span className="brand-mark small">
                <span />
                <span />
                <span />
              </span>
              <strong>OrderHub</strong>
            </div>
            <div className="breadcrumb">
              <span>Ажлын хэсэг</span>
              <i>/</i>
              <strong>{title}</strong>
            </div>
            <div className="header-actions">
              <label className="company-select">
                <span className="company-icon">
                  <Icon name="building" size={16} />
                </span>
                <select
                  aria-label="Компани"
                  value={active.id}
                  onChange={(event) => void switchCompany(event.target.value)}
                >
                  {companies.data?.results.map((company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))}
                </select>
              </label>
              <Avatar name={user.username} size="sm" />
            </div>
          </header>
          {error ? (
            <div className="shell-error">
              <ErrorNotice error={error} />
            </div>
          ) : null}
          <main className="app-content" key={active.id}>
            <Outlet />
          </main>
        </div>
        <nav className="mobile-nav">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              className={({ isActive }) => (isActive ? "active" : "")}
              to={item.to}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </WorkspaceProvider>
  );
}

function CreateCompany({ onCreated }: { onCreated: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<unknown>(null);
  return (
    <main className="login-page">
      <form
        className="login-card"
        onSubmit={async (event) => {
          event.preventDefault();
          try {
            await post("/api/companies/", {
              name,
              slug,
              timezone: "Asia/Ulaanbaatar",
            });
            await onCreated();
          } catch (reason) {
            setError(reason);
          }
        }}
      >
        <small className="eyebrow">ЭХЛЭХ</small>
        <h2>Компани үүсгэх</h2>
        <p>OrderHub ажлын орчноо нэрлэнэ үү.</p>
        <label>
          Компанийн нэр
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Товч нэр (латин үсэг)
          <input
            required
            pattern="[a-z0-9-]+"
            value={slug}
            onChange={(event) => setSlug(event.target.value.toLowerCase())}
          />
        </label>
        <ErrorNotice error={error} />
        <Button type="submit" variant="primary">
          Үүсгэх
        </Button>
      </form>
    </main>
  );
}
