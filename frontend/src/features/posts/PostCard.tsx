import { Link } from "react-router";
import { Avatar, Button, PlatformBadge, StatusBadge } from "@/components/ui";
import Icon from "@/components/ui/Icon";
import { dateTime } from "@/lib/formatters";
import type { Post } from "@/types/api";

const labels: Record<Post["status"], string> = {
  DRAFT: "Ноорог",
  SCHEDULED: "Хуваарьтай",
  PUBLISHED: "Нийтлэгдсэн",
  FAILED: "Амжилтгүй",
  DELIVERY_UNKNOWN: "Төлөв тодорхойгүй",
};

export default function PostCard({ post, detail = false }: { post: Post; detail?: boolean }) {
  return (
    <article className={detail ? "detail-post" : "post-card"}>
      <div className="post-card-header">
        <Avatar name={post.page_name} store />
        <span>
          <strong>{post.page_name}</strong>
          <small>
            {dateTime(post.published_at || post.scheduled_at || post.created_at_platform)}
          </small>
        </span>
        <PlatformBadge platform={post.platform} compact={!detail} />
        {!detail && <Button variant="icon" icon="more" />}
      </div>
      {post.status !== "PUBLISHED" && (
        <StatusBadge
          tone={
            post.status === "FAILED" || post.status === "DELIVERY_UNKNOWN" ? "danger" : "warning"
          }
        >
          {labels[post.status]}
        </StatusBadge>
      )}
      <p className="post-copy">{post.message || "Медиа нийтлэл"}</p>
      {post.media.map((media, index) => (
        <a
          className="post-image"
          key={`${media.url}-${index}`}
          href={media.url}
          target="_blank"
          rel="noreferrer"
        >
          <img src={media.url} alt="Нийтлэлийн медиа" referrerPolicy="no-referrer" />
        </a>
      ))}
      <div className="post-stats">
        <span>
          <span className="reaction-stack">
            <i>f</i>
            <i>
              <Icon name="heart" size={11} />
            </i>
          </span>
          {post.reaction_count}
        </span>
        <span>
          <Icon name="comment" size={16} />
          {post.comment_count} сэтгэгдэл
        </span>
      </div>
      <div className="post-actions">
        {detail && post.permalink_url && (
          <a
            className="button button-secondary"
            href={post.permalink_url}
            target="_blank"
            rel="noreferrer"
          >
            Facebook дээр ↗
          </a>
        )}
        {!detail && (
          <Link className="button button-secondary" to={`/posts/${post.id}`}>
            Дэлгэрэнгүй
          </Link>
        )}
      </div>
    </article>
  );
}
