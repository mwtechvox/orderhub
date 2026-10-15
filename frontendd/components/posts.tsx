"use client";
/* eslint-disable @next/next/no-img-element -- Meta media hosts vary; direct HTTPS media avoids a server-side image proxy. */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api, post } from "@/lib/api";
import { dateTime } from "@/lib/format";
import type {
  Account,
  Post,
  Comment,
  CommentAutomationRule,
  CommentReplyAttempt,
  Page,
} from "@/lib/types";
import { useCanManageIntegration, useCompany } from "./shell";
import {
  AccountSelector,
  ChannelSelector,
  FilterBar,
  PlatformBadge,
  StatusBadge,
} from "./social-ui";
import { Empty, ErrorNotice, Pager } from "./ui";

type ReplySender = (
  message: string,
  idempotencyKey: string,
) => Promise<CommentReplyAttempt>;

export function CommentReplyComposer({
  commentId,
  disabled = false,
  onSent,
  sendReply,
}: {
  commentId: string;
  disabled?: boolean;
  onSent: () => Promise<void>;
  sendReply?: ReplySender;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState<CommentReplyAttempt | null>(null);
  const [error, setError] = useState<unknown>(null);
  const pending = useRef<{ text: string; key: string } | null>(null);
  const unknown = attempt?.status === "DELIVERY_UNKNOWN";
  const failed = attempt?.status === "FAILED";

  async function submit(retry = false) {
    const message = text.trim();
    if (!message || busy || disabled || unknown || (failed && !retry)) return;
    if (retry || !pending.current || pending.current.text !== message) {
      pending.current = { text: message, key: crypto.randomUUID() };
    }
    setBusy(true);
    setError(null);
    try {
      const outcome = await (
        sendReply ??
        ((value, key) =>
          post<CommentReplyAttempt>(`/api/comments/${commentId}/reply/`, {
            message: value,
            idempotency_key: key,
          }))
      )(message, pending.current.key);
      setAttempt(outcome);
      if (outcome.status === "SENT") {
        setText("");
        pending.current = null;
        await onSent();
      }
    } catch (err) {
      // Keep the key: replaying it asks the backend for the same durable attempt.
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="composer">
      <label className="sr-only" htmlFor={`comment-reply-${commentId}`}>
        Хариу бичих
      </label>
      <textarea
        id={`comment-reply-${commentId}`}
        aria-label="Хариу бичих"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          if (failed) {
            setAttempt(null);
            pending.current = null;
          }
        }}
        maxLength={8000}
        placeholder="Хариу бичих…"
        disabled={disabled || busy || unknown}
      />
      <button
        className="primary"
        disabled={disabled || busy || unknown || failed || !text.trim()}
        onClick={() => void submit()}
      >
        {busy ? "Илгээж байна…" : "Илгээх"}
      </button>
      {attempt?.status === "SENT" && <p role="status">Илгээгдлээ.</p>}
      {failed && (
        <>
          <p role="alert" className="error">
            Илгээж чадсангүй.
          </p>
          <button disabled={busy} onClick={() => void submit(true)}>
            Дахин оролдох
          </button>
        </>
      )}
      {unknown && (
        <p role="alert" className="error">
          Илгээлтийн төлөв тодорхойгүй байна. Facebook хариуг нийтэлсэн байж
          болзошгүй. Дахин илгээхээс өмнө Facebook-ийг шалгана уу.
        </p>
      )}
      <ErrorNotice error={error} />
    </div>
  );
}

export function PostCard({
  item,
  detail = false,
}: {
  item: Post;
  detail?: boolean;
}) {
  return (
    <article className="card post-card">
      <div className="post-heading">
        <span className="avatar">{item.page_name.slice(0, 1)}</span>
        <div>
          <strong>{item.page_name}</strong>
          <small>{dateTime(item.created_at_platform)}</small>
        </div>
        <PlatformBadge platform={item.platform} />
      </div>
      {item.status !== "PUBLISHED" && (
        <StatusBadge
          tone={
            item.status === "FAILED" || item.status === "DELIVERY_UNKNOWN"
              ? "danger"
              : "warning"
          }
        >
          {postStatusLabel(item.status)}
        </StatusBadge>
      )}
      <p className="post-text">{item.message || "Медиа нийтлэл"}</p>
      {item.media.map((m, i) => (
        <a key={i} href={m.url} target="_blank" rel="noopener noreferrer">
          <img
            src={m.url}
            alt="Нийтлэлийн медиа"
            className="post-image"
            referrerPolicy="no-referrer"
          />
        </a>
      ))}
      <div className="stats">
        <span>♡ {item.reaction_count}</span>
        <span>☏ {item.comment_count} сэтгэгдэл</span>
        {!detail && <Link href={`/posts/${item.id}`}>Дэлгэрэнгүй →</Link>}
        {detail && item.permalink_url && (
          <a
            href={item.permalink_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Facebook дээр ↗
          </a>
        )}
      </div>
    </article>
  );
}
export function Posts() {
  const company = useCompany();
  const canManageIntegration = useCanManageIntegration();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [platform, setPlatform] = useState("");
  const [account, setAccount] = useState("");
  const accounts = useQuery({
    queryKey: ["accounts", company],
    queryFn: () => api<Page<Account>>("/api/meta/accounts/"),
  });
  const platforms = [
    ...new Set((accounts.data?.results ?? []).map((item) => item.platform)),
  ];
  const query = useQuery({
    queryKey: ["posts", company, page, search, platform, account],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), search });
      if (platform) params.set("platform", platform);
      if (account) params.set("social_account", account);
      return api<Page<Post>>(`/api/posts/?${params}`);
    },
    refetchInterval: 5000,
  });
  const sync = useMutation({ mutationFn: () => post("/api/posts/sync/") });
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">FACEBOOK</p>
          <h1>Нийтлэлүүд</h1>
          <p className="muted">Сэтгэгдэл бүрийг ярианы эхлэл болгоорой.</p>
        </div>
        {canManageIntegration && (
          <div className="page-actions">
            <Link className="primary button-link" href="/posts/new">
              + Шинэ нийтлэл
            </Link>
            <button disabled={sync.isPending} onClick={() => sync.mutate()}>
              ↻ Синк хийх
            </button>
          </div>
        )}
      </div>
      <FilterBar>
        <ChannelSelector
          value={platform}
          platforms={platforms}
          onChange={(value) => {
            setPlatform(value);
            setAccount("");
            setPage(1);
          }}
        />
        <AccountSelector
          value={account}
          accounts={accounts.data?.results ?? []}
          platform={platform}
          onChange={(value) => {
            setAccount(value);
            setPage(1);
          }}
        />
        <label className="filter-search">
          <span className="sr-only">Нийтлэл хайх</span>
          <input
            aria-label="Нийтлэл хайх"
            placeholder="Нийтлэл хайх…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </label>
      </FilterBar>
      <ErrorNotice error={query.error || sync.error} />
      {sync.isSuccess && <p role="status">Синк хийх хүсэлтийг хүлээн авлаа.</p>}
      {query.isLoading ? (
        <Empty>Ачаалж байна…</Empty>
      ) : query.data?.results.length ? (
        <div className="post-grid">
          {query.data.results.map((p) => (
            <PostCard key={p.id} item={p} />
          ))}
        </div>
      ) : (
        <Empty>
          Нийтлэл алга.{" "}
          <Link href="/settings/integrations">Facebook хуудсаа холбоод</Link>{" "}
          синк хийнэ үү.
        </Empty>
      )}
      <Pager page={page} count={query.data?.count ?? 0} onChange={setPage} />
    </>
  );
}
export function PostDetail({ id }: { id: string }) {
  const company = useCompany();
  const canManage = useCanManageIntegration();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Comment | null>(null);
  const item = useQuery({
    queryKey: ["post", company, id],
    queryFn: () => api<Post>(`/api/posts/${id}/`),
  });
  const comments = useQuery({
    queryKey: ["comments", company, id, page],
    queryFn: () =>
      api<Page<Comment>>(`/api/posts/${id}/comments/?page=${page}`),
    refetchInterval: 5000,
  });
  return (
    <>
      <Link className="back" href="/posts">
        ← Нийтлэлүүд
      </Link>
      <ErrorNotice error={item.error || comments.error} />
      <div className="detail-grid">
        <section>
          {item.data && <PostCard item={item.data} detail />}
          {item.data &&
            item.data.origin === "ORDERHUB" &&
            ["DRAFT", "SCHEDULED", "FAILED"].includes(item.data.status) &&
            canManage && (
              <Link className="button-link" href={`/posts/${id}/edit`}>
                Нийтлэл засах
              </Link>
            )}
          {item.data && (
            <PostAutomationEditor
              postId={id}
              rule={item.data.comment_automation}
              canEdit={canManage}
              onSaved={async () => {
                await item.refetch();
              }}
            />
          )}
          <div className="card comments">
            <h2>Сэтгэгдлүүд</h2>
            {comments.data?.results.map((c) => (
              <button
                className={`comment ${c.parent_comment ? "nested" : ""}`}
                key={c.id}
                onClick={() => setSelected(c)}
              >
                <strong>{c.author_name || "Facebook хэрэглэгч"}</strong>
                {c.parent_comment && <small>↳ Хариу</small>}
                <p>{c.message}</p>
                <small>{dateTime(c.created_at_platform)}</small>
              </button>
            ))}
            {comments.data?.count === 0 && <Empty>Сэтгэгдэл алга.</Empty>}
            <Pager
              page={page}
              count={comments.data?.count ?? 0}
              onChange={setPage}
            />
          </div>
        </section>
        <aside className="card reply-panel">
          <h2>Сэтгэгдэлд хариулах</h2>
          {selected ? (
            <>
              <strong>{selected.author_name || "Facebook хэрэглэгч"}</strong>
              <blockquote>{selected.message}</blockquote>
              <CommentReplyComposer
                key={selected.id}
                commentId={selected.id}
                disabled={!selected.can_reply}
                onSent={async () => {
                  await cache.invalidateQueries({
                    queryKey: ["comments", company, id],
                  });
                }}
              />
            </>
          ) : (
            <Empty>Хариулах сэтгэгдлээ сонгоно уу.</Empty>
          )}
        </aside>
      </div>
    </>
  );
}

const DEFAULT_AUTOMATION: CommentAutomationRule = {
  is_enabled: true,
  public_reply_enabled: true,
  public_reply_text: "Мэдээллийг чат руу илгээлээ. Чатаа шалгаарай 😊",
  private_reply_enabled: true,
  private_reply_text:
    "Сайн байна уу 👋\n\nДэлгэрэнгүй мэдээллийг танд чат руу илгээлээ.\n\nЗахиалах бол энэ чатад хариу бичээрэй.",
  created_at: null,
  updated_at: null,
};

function postStatusLabel(status: Post["status"]) {
  return {
    DRAFT: "Ноорог",
    SCHEDULED: "Хуваарьт",
    PUBLISHED: "Нийтлэгдсэн",
    FAILED: "Нийтэлж чадсангүй",
    DELIVERY_UNKNOWN: "Төлөв тодорхойгүй",
  }[status];
}

function AutomationFields({
  value,
  onChange,
  disabled = false,
}: {
  value: CommentAutomationRule;
  onChange: (value: CommentAutomationRule) => void;
  disabled?: boolean;
}) {
  return (
    <div className="automation-fields">
      <label className="toggle-row">
        <input
          type="checkbox"
          checked={value.is_enabled}
          disabled={disabled}
          onChange={(event) =>
            onChange({ ...value, is_enabled: event.target.checked })
          }
        />
        <span>Автомат хариу идэвхжүүлэх</span>
      </label>
      <div className="automation-field">
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={value.public_reply_enabled}
            disabled={disabled || !value.is_enabled}
            onChange={(event) =>
              onChange({ ...value, public_reply_enabled: event.target.checked })
            }
          />
          <span>Нийтийн хариу</span>
        </label>
        <textarea
          aria-label="Нийтийн автомат хариу"
          value={value.public_reply_text}
          maxLength={8000}
          disabled={
            disabled || !value.is_enabled || !value.public_reply_enabled
          }
          onChange={(event) =>
            onChange({ ...value, public_reply_text: event.target.value })
          }
        />
      </div>
      <div className="automation-field">
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={value.private_reply_enabled}
            disabled={disabled || !value.is_enabled}
            onChange={(event) =>
              onChange({
                ...value,
                private_reply_enabled: event.target.checked,
              })
            }
          />
          <span>Хувийн мессеж</span>
        </label>
        <textarea
          aria-label="Хувийн автомат мессеж"
          value={value.private_reply_text}
          maxLength={2000}
          disabled={
            disabled || !value.is_enabled || !value.private_reply_enabled
          }
          onChange={(event) =>
            onChange({ ...value, private_reply_text: event.target.value })
          }
        />
      </div>
    </div>
  );
}

export function PostAutomationEditor({
  postId,
  rule,
  canEdit,
  onSaved,
}: {
  postId: string;
  rule: CommentAutomationRule | null;
  canEdit: boolean;
  onSaved: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(rule ?? DEFAULT_AUTOMATION);
  const mutation = useMutation({
    mutationFn: (body: CommentAutomationRule) =>
      api<CommentAutomationRule>(`/api/posts/${postId}/comment-automation/`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: async (updated) => {
      setForm(updated);
      setEditing(false);
      await onSaved();
    },
  });
  return (
    <section className="card post-automation-panel">
      <div className="automation-heading">
        <div>
          <p className="eyebrow">POST OVERRIDE</p>
          <h2>Сэтгэгдлийн автомат хариу</h2>
        </div>
        {!editing && canEdit && (
          <button onClick={() => setEditing(true)}>
            {rule ? "Засах" : "Тусдаа тохируулах"}
          </button>
        )}
      </div>
      {!rule && !editing ? (
        <p className="muted">
          Энэ нийтлэл Page-ийн үндсэн автомат хариуг ашиглана.
        </p>
      ) : editing ? (
        <>
          <p className="muted">
            Унтраасан override нь энэ нийтлэлд Page-ийн үндсэн дүрмийг
            ашиглуулахгүй.
          </p>
          <AutomationFields value={form} onChange={setForm} />
          <div className="form-actions">
            <button onClick={() => setEditing(false)}>Цуцлах</button>
            <button
              className="primary"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(form)}
            >
              Хадгалах
            </button>
          </div>
          <ErrorNotice error={mutation.error} />
        </>
      ) : (
        <>
          <StatusBadge tone={rule?.is_enabled ? "success" : "neutral"}>
            {rule?.is_enabled ? "Идэвхтэй" : "Энэ нийтлэлд унтраасан"}
          </StatusBadge>
          <AutomationFields value={form} onChange={setForm} disabled />
        </>
      )}
    </section>
  );
}

export function PostComposer({ id }: { id?: string }) {
  const company = useCompany();
  const canManage = useCanManageIntegration();
  const accounts = useQuery({
    queryKey: ["accounts", company],
    queryFn: () => api<Page<Account>>("/api/meta/accounts/"),
    enabled: canManage,
  });
  const existing = useQuery({
    queryKey: ["post", company, id],
    queryFn: () => api<Post>(`/api/posts/${id}/`),
    enabled: canManage && !!id,
  });
  if (!canManage)
    return (
      <Empty>Нийтлэл үүсгэх, засах эрх OWNER болон ADMIN-д нээлттэй.</Empty>
    );
  if (accounts.isLoading || (id && existing.isLoading))
    return <Empty>Ачаалж байна…</Empty>;
  if (accounts.error || existing.error)
    return <ErrorNotice error={accounts.error || existing.error} />;
  return (
    <PostComposerForm
      key={existing.data?.id ?? "new"}
      id={id}
      initial={existing.data}
      accounts={accounts.data?.results ?? []}
    />
  );
}

function PostComposerForm({
  id,
  initial,
  accounts,
}: {
  id?: string;
  initial?: Post;
  accounts: Account[];
}) {
  const router = useRouter();
  const availableAccounts = accounts.filter(
    (item) => item.platform === "FACEBOOK_PAGE" && item.status === "ACTIVE",
  );
  const [account, setAccount] = useState(
    initial?.social_account ?? availableAccounts[0]?.id ?? "",
  );
  const [message, setMessage] = useState(initial?.message ?? "");
  const [imageUrl, setImageUrl] = useState(initial?.media[0]?.url ?? "");
  const [override, setOverride] = useState(!!initial?.comment_automation);
  const [automation, setAutomation] = useState(
    initial?.comment_automation ?? DEFAULT_AUTOMATION,
  );
  const [scheduledAt, setScheduledAt] = useState(
    initial?.scheduled_at?.slice(0, 16) ?? "",
  );
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function save(publishMode: "DRAFT" | "PUBLISH_NOW" | "SCHEDULE") {
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        social_account: account,
        message,
        media: imageUrl.trim() ? [{ type: "image", url: imageUrl.trim() }] : [],
        publish_mode: publishMode,
      };
      if (publishMode === "SCHEDULE")
        body.scheduled_at = new Date(scheduledAt).toISOString();
      if (override) body.comment_automation = automation;
      const saved = await api<Post>(id ? `/api/posts/${id}/` : "/api/posts/", {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(body),
      });
      router.push(`/posts/${saved.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="post-composer-page">
      <Link className="back" href={id ? `/posts/${id}` : "/posts"}>
        ← Буцах
      </Link>
      <div className="page-title">
        <div>
          <p className="eyebrow">FACEBOOK PUBLISHING</p>
          <h1>{id ? "Нийтлэл засах" : "Шинэ нийтлэл"}</h1>
        </div>
      </div>
      <section className="card post-composer-form">
        <label>
          Facebook Page
          <select
            value={account}
            onChange={(event) => setAccount(event.target.value)}
          >
            {availableAccounts.map((item) => (
              <option key={item.id} value={item.id}>
                {item.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Нийтлэлийн текст
          <textarea
            aria-label="Нийтлэлийн текст"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={63206}
            rows={8}
          />
        </label>
        <label>
          Зургийн HTTPS URL <span className="muted">(V1: нэг зураг)</span>
          <input
            aria-label="Зургийн HTTPS URL"
            type="url"
            value={imageUrl}
            onChange={(event) => setImageUrl(event.target.value)}
            placeholder="https://..."
          />
        </label>
        <details className="automation-details" open={override}>
          <summary>Сэтгэгдлийн автомат хариу</summary>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={override}
              onChange={(event) => setOverride(event.target.checked)}
            />
            <span>Энэ нийтлэлд тусдаа тохиргоо ашиглах</span>
          </label>
          {override ? (
            <AutomationFields value={automation} onChange={setAutomation} />
          ) : (
            <p className="muted">Page-ийн үндсэн автомат хариуг ашиглана.</p>
          )}
        </details>
        <label>
          Хуваарьт нийтлэх хугацаа
          <input
            aria-label="Хуваарьт нийтлэх хугацаа"
            type="datetime-local"
            value={scheduledAt}
            onChange={(event) => setScheduledAt(event.target.value)}
          />
        </label>
        <ErrorNotice error={error} />
        <div className="form-actions publish-actions">
          <button
            disabled={busy || !account}
            onClick={() => void save("DRAFT")}
          >
            Ноорог хадгалах
          </button>
          <button
            disabled={busy || !account || !scheduledAt}
            onClick={() => void save("SCHEDULE")}
          >
            Хуваарьт оруулах
          </button>
          <button
            className="primary"
            disabled={busy || !account}
            onClick={() => void save("PUBLISH_NOW")}
          >
            Одоо нийтлэх
          </button>
        </div>
      </section>
    </div>
  );
}
