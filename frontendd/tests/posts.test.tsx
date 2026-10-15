import { render, screen } from "@testing-library/react";
import { it, expect } from "vitest";
import { PostCard } from "@/components/posts";
it("renders real aggregate counts and the local detail link", () => {
  render(
    <PostCard
      item={{
        id: "post",
        social_account: "page",
        platform: "FACEBOOK_PAGE",
        page_name: "Дэлгүүр",
        origin: "FACEBOOK_SYNC",
        status: "PUBLISHED",
        message: "Шинэ бараа",
        permalink_url: "https://www.facebook.com/post",
        media: [],
        comment_count: 3,
        reaction_count: 14,
        created_at_platform: "2026-10-13T10:00:00Z",
        scheduled_at: null,
        published_at: "2026-10-13T10:00:00Z",
        publish_error_code: null,
        comment_automation: null,
      }}
    />,
  );
  expect(screen.getByText("Шинэ бараа")).toBeInTheDocument();
  expect(screen.getByText("♡ 14")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Дэлгэрэнгүй →" })).toHaveAttribute(
    "href",
    "/posts/post",
  );
});
