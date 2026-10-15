import { useState } from "react";
import { Link } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post } from "@/lib/api-client";
import type { Account, Page, Post } from "@/types/api";
import Filters from "@/components/social/Filters";
import { Button, EmptyState, ErrorNotice, LoadingState, Pager, StatusBadge } from "@/components/ui";
import { useWorkspace } from "@/features/companies/WorkspaceContext";
import PostCard from "./PostCard";

export default function PostsPage() {
  const { companyId, canManage } = useWorkspace();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [platform, setPlatform] = useState("");
  const [account, setAccount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const accounts = useQuery({
    queryKey: ["accounts", companyId],
    queryFn: () => api<Page<Account>>("/api/meta/accounts/"),
  });
  const posts = useQuery({
    queryKey: ["posts", companyId, page, search, platform, account],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), search });
      if (platform) params.set("platform", platform);
      if (account) params.set("social_account", account);
      return api<Page<Post>>(`/api/posts/?${params}`);
    },
  });
  async function sync() {
    setBusy(true);
    setError(null);
    try {
      await post("/api/posts/sync/", account ? { social_account: account } : {});
      await cache.invalidateQueries({ queryKey: ["posts", companyId] });
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="screen">
      <div className="page-top">
        <div>
          <h1>Нийтлэл</h1>
          <p>Бүх сувгийн нийтлэл, сэтгэгдлийг удирдана.</p>
        </div>
        <div className="page-actions">
          {canManage && (
            <Link className="button button-primary" to="/posts/new">
              + Шинэ нийтлэл
            </Link>
          )}
          {canManage && (
            <Button icon="sync" onClick={() => void sync()} disabled={busy}>
              {busy ? "Синк хийж байна..." : "Синк хийх"}
            </Button>
          )}
        </div>
      </div>
      <ErrorNotice error={error || posts.error || accounts.error} />
      <div className="posts-filter">
        <Filters
          accounts={accounts.data?.results ?? []}
          platform={platform}
          account={account}
          search={search}
          searchPlaceholder="Нийтлэл хайх..."
          onPlatformChange={(value) => {
            setPlatform(value);
            setAccount("");
            setPage(1);
          }}
          onAccountChange={(value) => {
            setAccount(value);
            setPage(1);
          }}
          onSearchChange={(value) => {
            setSearch(value);
            setPage(1);
          }}
        />
      </div>
      <div className="section-heading">
        <span>
          <h2>Сүүлийн нийтлэлүүд</h2>
          <p>{posts.data?.count ?? 0} нийтлэл</p>
        </span>
        {accounts.data?.results.some((item) => item.status === "ACTIVE") && (
          <StatusBadge tone="success">Суваг идэвхтэй</StatusBadge>
        )}
      </div>
      {posts.isLoading ? (
        <LoadingState />
      ) : posts.data?.results.length ? (
        <div className="posts-grid">
          {posts.data.results.map((item) => (
            <PostCard key={item.id} post={item} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="Нийтлэл алга"
          description="Facebook Page-аа холбоод синк хийх эсвэл шинэ нийтлэл үүсгэнэ үү."
        />
      )}
      <Pager page={page} count={posts.data?.count ?? 0} onChange={setPage} />
    </div>
  );
}
