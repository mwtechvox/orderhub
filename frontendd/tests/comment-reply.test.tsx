import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CommentReplyComposer } from "@/components/posts";
import type { CommentReplyAttempt } from "@/lib/types";

function attempt(status: CommentReplyAttempt["status"]): CommentReplyAttempt {
  return {
    id: "attempt",
    comment: "comment",
    text: "Хариу",
    status,
    error_code: status === "SENT" ? null : "META_ERROR",
    created_at: "2026-10-14T10:00:00Z",
    updated_at: "2026-10-14T10:00:00Z",
  };
}

function renderComposer(
  sendReply: (text: string, key: string) => Promise<CommentReplyAttempt>,
) {
  const onSent = vi.fn(async () => {});
  render(
    <CommentReplyComposer
      commentId="comment"
      onSent={onSent}
      sendReply={sendReply}
    />,
  );
  fireEvent.change(screen.getByRole("textbox", { name: "Хариу бичих" }), {
    target: { value: "Хариу" },
  });
  return onSent;
}

describe("CommentReplyComposer", () => {
  it("shows a sent outcome", async () => {
    const send = vi.fn(async () => attempt("SENT"));
    const onSent = renderComposer(send);
    fireEvent.click(screen.getByRole("button", { name: "Илгээх" }));
    await screen.findByText("Илгээгдлээ.");
    expect(onSent).toHaveBeenCalledOnce();
  });

  it("only retries a confirmed failure with a new idempotency key", async () => {
    const send = vi
      .fn<(text: string, key: string) => Promise<CommentReplyAttempt>>()
      .mockResolvedValueOnce(attempt("FAILED"))
      .mockResolvedValueOnce(attempt("SENT"));
    renderComposer(send);
    fireEvent.click(screen.getByRole("button", { name: "Илгээх" }));
    await screen.findByText("Илгээж чадсангүй.");
    fireEvent.click(screen.getByRole("button", { name: "Дахин оролдох" }));
    await waitFor(() => expect(send).toHaveBeenCalledTimes(2));
    expect(send.mock.calls[1][1]).not.toBe(send.mock.calls[0][1]);
  });

  it("warns about an ambiguous outcome without a retry button", async () => {
    const send = vi.fn(async () => attempt("DELIVERY_UNKNOWN"));
    renderComposer(send);
    fireEvent.click(screen.getByRole("button", { name: "Илгээх" }));
    await screen.findByText(/Илгээлтийн төлөв тодорхойгүй байна/);
    expect(screen.queryByRole("button", { name: "Дахин оролдох" })).toBeNull();
    expect(screen.getByRole("textbox", { name: "Хариу бичих" })).toBeDisabled();
    expect(send).toHaveBeenCalledOnce();
  });
});
