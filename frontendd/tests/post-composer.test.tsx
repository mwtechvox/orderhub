import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { PostAutomationEditor, PostComposer } from "@/components/posts";
import { api } from "@/lib/api";
import type { CommentAutomationRule } from "@/lib/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", () => ({ api: vi.fn(), post: vi.fn() }));
vi.mock("@/components/shell", () => ({
  useCompany: () => "company",
  useCanManageIntegration: () => true,
}));

const automation: CommentAutomationRule = {
  is_enabled: true,
  public_reply_enabled: true,
  public_reply_text: "Нийтийн хариу",
  private_reply_enabled: true,
  private_reply_text: "Хувийн мессеж",
  created_at: null,
  updated_at: null,
};

function wrapper(children: React.ReactNode) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

beforeEach(() => {
  push.mockReset();
  vi.mocked(api).mockReset();
});

it("creates a draft with a per-post static automation override", async () => {
  vi.mocked(api).mockImplementation(async (path, init) => {
    if (path === "/api/meta/accounts/")
      return {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: "account",
            platform: "FACEBOOK_PAGE",
            display_name: "Дэлгүүр",
            status: "ACTIVE",
            last_synced_at: null,
            sync_status: "IDLE",
            last_error: "",
            webhook_subscribed_at: null,
          },
        ],
      };
    if (init?.method === "POST") return { id: "post" };
    throw new Error(String(path));
  });
  render(wrapper(<PostComposer />));
  await screen.findByRole("option", { name: "Дэлгүүр" });
  fireEvent.change(screen.getByLabelText("Нийтлэлийн текст"), {
    target: { value: "Шинэ нийтлэл" },
  });
  fireEvent.click(
    screen.getByRole("checkbox", {
      name: "Энэ нийтлэлд тусдаа тохиргоо ашиглах",
    }),
  );
  fireEvent.change(screen.getByLabelText("Нийтийн автомат хариу"), {
    target: { value: "Чатаа шалгаарай" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Ноорог хадгалах" }));
  await waitFor(() => expect(push).toHaveBeenCalledWith("/posts/post"));
  expect(api).toHaveBeenLastCalledWith(
    "/api/posts/",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('"publish_mode":"DRAFT"'),
    }),
  );
  expect(vi.mocked(api).mock.calls.at(-1)?.[1]?.body).toContain(
    "Чатаа шалгаарай",
  );
});

it("edits automation after publishing without changing post content", async () => {
  vi.mocked(api).mockResolvedValue({
    ...automation,
    public_reply_text: "Шинэ текст",
  });
  const saved = vi.fn().mockResolvedValue(undefined);
  render(
    wrapper(
      <PostAutomationEditor
        postId="post"
        rule={automation}
        canEdit
        onSaved={saved}
      />,
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Засах" }));
  fireEvent.change(screen.getByLabelText("Нийтийн автомат хариу"), {
    target: { value: "Шинэ текст" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Хадгалах" }));
  await waitFor(() => expect(saved).toHaveBeenCalled());
  expect(api).toHaveBeenCalledWith(
    "/api/posts/post/comment-automation/",
    expect.objectContaining({
      method: "PUT",
      body: expect.stringContaining("Шинэ текст"),
    }),
  );
});
