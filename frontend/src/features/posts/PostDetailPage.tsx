import { useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post, put } from "@/lib/api-client";
import { dateTime } from "@/lib/formatters";
import type { Comment, CommentAutomationRule, CommentReplyAttempt, Page, Post } from "@/types/api";
import AutomationFields, { DEFAULT_AUTOMATION } from "@/components/social/AutomationFields";
import {
  Avatar,
  Button,
  EmptyState,
  ErrorNotice,
  LoadingState,
  Pager,
  PlatformBadge,
  StatusBadge,
} from "@/components/ui";
import { useWorkspace } from "@/features/companies/WorkspaceContext";
import PostCard from "./PostCard";

export default function PostDetailPage() {
  const { id = "" } = useParams();
  const { companyId, canManage } = useWorkspace();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const postQuery = useQuery({
    queryKey: ["post", companyId, id],
    queryFn: () => api<Post>(`/api/posts/${id}/`),
  });
  const comments = useQuery({
    queryKey: ["comments", companyId, id, page],
    queryFn: () => api<Page<Comment>>(`/api/posts/${id}/comments/?page=${page}`),
  });
  const selectedComment =
    comments.data?.results.find((item) => item.id === selected) ??
    comments.data?.results[0] ??
    null;
  if (postQuery.isLoading) return <LoadingState />;
  if (!postQuery.data) return <ErrorNotice error={postQuery.error} />;
  const item = postQuery.data;
  return (
    <div className="screen detail-screen">
      <div className="page-top detail-top">
        <div className="title-with-back">
          <Link className="button button-icon" to="/posts">
            ←
          </Link>
          <div>
            <h1>Нийтлэлийн дэлгэрэнгүй</h1>
            <p>Сэтгэгдэл, хариултуудыг удирдана.</p>
          </div>
        </div>
        {canManage &&
          item.origin === "ORDERHUB" &&
          ["DRAFT", "SCHEDULED", "FAILED"].includes(item.status) && (
            <Link className="button button-secondary" to={`/posts/${id}/edit`}>
              Засах
            </Link>
          )}
      </div>
      <ErrorNotice error={postQuery.error || comments.error} />
      <div className="detail-layout">
        <main className="detail-main">
          <PostCard post={item} detail />
          <section className="comments-section">
            <div className="comments-heading">
              <span>
                <h2>Сэтгэгдэл</h2>
                <b>{comments.data?.count ?? item.comment_count}</b>
              </span>
            </div>
            {comments.isLoading ? (
              <LoadingState />
            ) : comments.data?.results.length ? (
              comments.data.results.map((comment) => (
                <CommentItem
                  key={comment.id}
                  item={comment}
                  selected={selectedComment?.id === comment.id}
                  onClick={() => setSelected(comment.id)}
                />
              ))
            ) : (
              <EmptyState title="Сэтгэгдэл алга" />
            )}
            <Pager page={page} count={comments.data?.count ?? 0} onChange={setPage} />
          </section>
          {canManage && (
            <PostAutomationEditor
              post={item}
              onSaved={async () => {
                await cache.invalidateQueries({
                  queryKey: ["post", companyId, id],
                });
              }}
            />
          )}
        </main>
        {selectedComment && (
          <ReplyPanel
            comment={selectedComment}
            onSent={async () => {
              await cache.invalidateQueries({
                queryKey: ["comments", companyId, id],
              });
            }}
          />
        )}
      </div>
    </div>
  );
}

function CommentItem({
  item,
  selected,
  onClick,
}: {
  item: Comment;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`comment-item ${selected ? "selected" : ""} ${
        item.parent_comment ? "nested" : ""
      }`}
      onClick={onClick}
    >
      <Avatar name={item.author_name} size="sm" />
      <span className="comment-content">
        <span className="comment-bubble">
          <strong>{item.author_name || "Facebook хэрэглэгч"}</strong>
          <p>{item.message}</p>
        </span>
        <span className="comment-meta">
          <span>{dateTime(item.created_at_platform)}</span>
          {item.can_reply && <b>Хариулах</b>}
        </span>
      </span>
    </button>
  );
}

function ReplyPanel({ comment, onSent }: { comment: Comment; onSent: () => Promise<void> }) {
  const pending = useRef<{ text: string; key: string } | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState<CommentReplyAttempt | null>(null);
  const [error, setError] = useState<unknown>(null);
  async function send(retry = false) {
    const value = text.trim();
    if (
      !value ||
      busy ||
      !comment.can_reply ||
      attempt?.status === "DELIVERY_UNKNOWN" ||
      (attempt?.status === "FAILED" && !retry)
    )
      return;
    if (retry || !pending.current || pending.current.text !== value)
      pending.current = { text: value, key: crypto.randomUUID() };
    setBusy(true);
    setError(null);
    try {
      const outcome = await post<CommentReplyAttempt>(`/api/comments/${comment.id}/reply/`, {
        message: value,
        idempotency_key: pending.current.key,
      });
      setAttempt(outcome);
      if (outcome.status === "SENT") {
        setText("");
        pending.current = null;
        await onSent();
      }
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="reply-panel">
      <div className="reply-panel-head">
        <span>
          <small>СОНГОСОН СЭТГЭГДЭЛ</small>
          <strong>Хариулах</strong>
        </span>
      </div>
      <div className="selected-customer">
        <Avatar name={comment.author_name} />
        <span>
          <strong>{comment.author_name || "Facebook хэрэглэгч"}</strong>
          <small>
            <PlatformBadge compact /> Facebook
          </small>
        </span>
      </div>
      <div className="original-comment">
        <span>Эх сэтгэгдэл</span>
        <p>“{comment.message}”</p>
        <small>{dateTime(comment.created_at_platform)}</small>
      </div>
      <div className="reply-composer">
        <label>Хариу бичих</label>
        <textarea
          value={text}
          maxLength={8000}
          disabled={!comment.can_reply || busy || attempt?.status === "DELIVERY_UNKNOWN"}
          onChange={(event) => {
            setText(event.target.value);
            if (attempt?.status === "FAILED") {
              setAttempt(null);
              pending.current = null;
            }
          }}
          placeholder="Хариу бичих..."
        />
        <div className="reply-tools">
          <Button
            variant="primary"
            icon="send"
            onClick={() => void send()}
            disabled={
              !text.trim() || busy || !comment.can_reply || (!!attempt && attempt.status !== "SENT")
            }
          >
            {busy ? "Илгээж байна..." : "Илгээх"}
          </Button>
        </div>
      </div>
      <ErrorNotice error={error} />
      {attempt?.status === "SENT" && (
        <div className="feedback success">
          <span>
            <strong>Илгээгдлээ</strong>
            <small>Хариу амжилттай нийтлэгдлээ.</small>
          </span>
        </div>
      )}
      {attempt?.status === "FAILED" && (
        <div className="feedback danger">
          <span>
            <strong>Илгээж чадсангүй</strong>
            <small>Meta хүсэлтийг татгалзлаа.</small>
            <button onClick={() => void send(true)}>Дахин оролдох</button>
          </span>
        </div>
      )}
      {attempt?.status === "DELIVERY_UNKNOWN" && (
        <div className="feedback warning">
          <span>
            <strong>Төлөв тодорхойгүй</strong>
            <small>
              Facebook дээр нийтлэгдсэн байж болзошгүй. Дахин илгээхээс өмнө шалгана уу.
            </small>
          </span>
        </div>
      )}
    </aside>
  );
}

function PostAutomationEditor({
  post: item,
  onSaved,
}: {
  post: Post;
  onSaved: () => Promise<void>;
}) {
  const [form, setForm] = useState<CommentAutomationRule>(
    item.comment_automation ?? DEFAULT_AUTOMATION,
  );
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<unknown>(null);
  return (
    <details className="automation-card" open={!!item.comment_automation}>
      <summary>Энэ нийтлэлийн автомат хариу</summary>
      <p>Энд хадгалсан тохиргоо Page-ийн үндсэн дүрмээс давуу үйлчилнэ.</p>
      <AutomationFields value={form} onChange={setForm} />
      <ErrorNotice error={error} />
      <div className="form-actions">
        <Button
          variant="primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setSaved(false);
            setError(null);
            try {
              const updated = await put<CommentAutomationRule>(
                `/api/posts/${item.id}/comment-automation/`,
                form,
              );
              setForm(updated);
              setSaved(true);
              await onSaved();
            } catch (reason) {
              setError(reason);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Хадгалж байна..." : "Хадгалах"}
        </Button>
        {saved && <StatusBadge tone="success">Хадгалагдлаа</StatusBadge>}
      </div>
    </details>
  );
}
