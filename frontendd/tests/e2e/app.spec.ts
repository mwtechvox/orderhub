import { test, expect } from "@playwright/test";
const now = "2026-10-13T10:00:00Z";
const company = { id: "company", name: "Демо дэлгүүр", slug: "demo" };
const conversation = {
  id: "conversation",
  customer: { id: "customer", name: "Бат" },
  social_account: "account",
  platform: "FACEBOOK_PAGE",
  page_name: "Демо дэлгүүр",
  last_message: "M размер байна уу?",
  last_message_at: now,
  unread_count: 1,
  last_inbound_at: now,
  can_reply: true,
};
const post = {
  id: "post",
  social_account: "account",
  platform: "FACEBOOK_PAGE",
  page_name: "Демо дэлгүүр",
  origin: "FACEBOOK_SYNC",
  status: "PUBLISHED",
  message: "Шинэ намрын цуглуулга ирлээ.\nДулаахан өдрүүдийг хамтдаа.",
  media: [],
  permalink_url: "https://www.facebook.com/post",
  comment_count: 1,
  reaction_count: 14,
  created_at_platform: now,
  scheduled_at: null,
  published_at: now,
  publish_error_code: null,
  comment_automation: null,
};
const comment = {
  id: "comment",
  post: "post",
  parent_comment: null,
  author_name: "Нараа",
  message: "Үнэ хэд вэ?",
  can_reply: true,
  created_at_platform: now,
};
const pageOf = (results: unknown[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
});
test("inbox send, post reply and integration selection", async ({ page }) => {
  const messages = [
    {
      id: "message",
      conversation: "conversation",
      direction: "INBOUND",
      text: "M размер байна уу?",
      attachments: [],
      status: "RECEIVED",
      sent_at: now,
      error_code: null,
    },
  ];
  const replies = [comment];
  let sentBody: Record<string, unknown> | null = null;
  let authoredPost: Record<string, unknown> | null = null;
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    let data: unknown = {};
    if (path === "/api/auth/me/")
      data = {
        id: 1,
        username: "demo",
        active_company: "company",
        active_company_role: "OWNER",
      };
    else if (path === "/api/auth/csrf/") data = { csrfToken: "test-csrf" };
    else if (path === "/api/companies/") data = pageOf([company]);
    else if (path === "/api/conversations/") data = pageOf([conversation]);
    else if (path === "/api/conversations/conversation/") data = conversation;
    else if (path === "/api/conversations/conversation/messages/")
      data = pageOf([...messages].reverse());
    else if (path === "/api/messages/send/") {
      sentBody = route.request().postDataJSON();
      const message = {
        ...messages[0],
        id: "outgoing",
        direction: "OUTBOUND",
        text: String(sentBody?.text),
        status: "PENDING",
      };
      messages.push(message);
      data = message;
    } else if (path === "/api/posts/" && method === "POST") {
      const body = route.request().postDataJSON();
      authoredPost = {
        ...post,
        id: "authored",
        origin: "ORDERHUB",
        status: "DRAFT",
        message: body.message,
        comment_automation: body.comment_automation,
      };
      data = authoredPost;
    } else if (path === "/api/posts/") data = pageOf([post]);
    else if (path === "/api/posts/post/") data = post;
    else if (path === "/api/posts/authored/") data = authoredPost;
    else if (path === "/api/posts/authored/comments/") data = pageOf([]);
    else if (path === "/api/posts/post/comments/") data = pageOf(replies);
    else if (path === "/api/comments/comment/reply/") {
      replies.push({
        ...comment,
        id: "reply",
        author_name: "Демо дэлгүүр",
        message: route.request().postDataJSON().message,
      });
      data = {
        id: "attempt",
        comment: "comment",
        text: route.request().postDataJSON().message,
        status: "SENT",
        error_code: null,
        created_at: now,
        updated_at: now,
      };
    } else if (path === "/api/meta/accounts/")
      data = pageOf([
        {
          id: "account",
          platform: "FACEBOOK_PAGE",
          display_name: "Демо дэлгүүр",
          status: "ACTIVE",
          last_synced_at: now,
          sync_status: "IDLE",
          last_error: "",
          webhook_subscribed_at: now,
        },
      ]);
    else if (path === "/api/meta/accounts/account/comment-automation/")
      data = {
        is_enabled: method === "PUT",
        public_reply_enabled: true,
        public_reply_text: "Мэдээллийг чат руу илгээлээ.",
        private_reply_enabled: true,
        private_reply_text:
          "Сайн байна уу. Дэлгэрэнгүй мэдээллийг хүргэж байна.",
        created_at: now,
        updated_at: now,
      };
    else if (path === "/api/meta/facebook/pages/")
      data =
        method === "GET"
          ? {
              selection_id: "selection",
              pages: [{ id: "page", name: "Демо дэлгүүр" }],
            }
          : { id: "account" };
    await route.fulfill({ json: data });
  });
  await page.goto("/inbox");
  await page.getByRole("button").filter({ hasText: "Бат" }).click();
  await expect(
    page.getByText("M размер байна уу?", { exact: true }),
  ).toHaveCount(2);
  await page
    .getByRole("textbox", { name: "Хариу бичих" })
    .fill("M размер байгаа шүү.");
  await page.getByRole("button", { name: "Илгээх", exact: true }).click();
  await expect(
    page.getByText("M размер байгаа шүү.", { exact: true }),
  ).toBeVisible();
  expect(sentBody).toMatchObject({
    conversation_id: "conversation",
    text: "M размер байгаа шүү.",
  });
  expect(Object.keys(sentBody!)).toEqual([
    "conversation_id",
    "text",
    "idempotency_key",
  ]);
  await page.screenshot({
    path: "/tmp/orderhub-inbox-desktop.png",
    fullPage: true,
  });
  await page.goto("/posts");
  await page.getByRole("link", { name: "+ Шинэ нийтлэл" }).click();
  await page.getByLabel("Нийтлэлийн текст").fill("OrderHub шинэ нийтлэл");
  await page
    .locator("summary")
    .filter({ hasText: "Сэтгэгдлийн автомат хариу" })
    .click();
  await page
    .getByRole("checkbox", { name: "Энэ нийтлэлд тусдаа тохиргоо ашиглах" })
    .click();
  await page.getByLabel("Нийтийн автомат хариу").fill("Чатаа шалгаарай 😊");
  await page.getByRole("button", { name: "Ноорог хадгалах" }).click();
  await expect(page).toHaveURL(/\/posts\/authored$/);
  await expect(page.getByText("OrderHub шинэ нийтлэл")).toBeVisible();
  await page
    .getByRole("link", { name: "Нийтлэл", exact: true })
    .first()
    .click();
  await page.getByRole("link", { name: "Дэлгэрэнгүй →" }).click();
  await page.getByRole("button").filter({ hasText: "Үнэ хэд вэ?" }).click();
  await page.getByRole("textbox", { name: "Хариу бичих" }).fill("89,000₮");
  await page.getByRole("button", { name: "Илгээх", exact: true }).click();
  await expect(page.getByText("89,000₮", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "/tmp/orderhub-post-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Холболтууд", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Холбох хуудсаа сонгох" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Сэтгэгдлийн автомат хариу" }),
  ).toBeVisible();
  await page
    .getByLabel("Демо дэлгүүр нийтийн хариу")
    .fill("Чатаа шалгаарай 😊");
  await page.getByRole("button", { name: "Хадгалах" }).click();
  await expect(page.getByText("Тохиргоо хадгалагдлаа.")).toBeVisible();
  await page.getByRole("button", { name: "Сонгох" }).click();
  await expect(
    page.getByText("Хуудас холбогдлоо. Синк эхэлж байна."),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/inbox");
  await page.getByRole("button").filter({ hasText: "Бат" }).click();
  await expect(
    page.getByRole("textbox", { name: "Хариу бичих" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: "/tmp/orderhub-inbox-mobile.png",
    fullPage: true,
  });
});

test("agent keeps daily work but cannot see integration management controls", async ({
  page,
}) => {
  let pageChoicesRequested = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = {};
    if (path === "/api/auth/me/")
      data = {
        id: 1,
        username: "agent",
        active_company: "company",
        active_company_role: "AGENT",
      };
    else if (path === "/api/companies/") data = pageOf([company]);
    else if (path === "/api/posts/") data = pageOf([post]);
    else if (path === "/api/meta/accounts/")
      data = pageOf([
        {
          id: "account",
          platform: "FACEBOOK_PAGE",
          display_name: "Демо дэлгүүр",
          status: "ACTIVE",
          last_synced_at: now,
          sync_status: "IDLE",
          last_error: "",
          webhook_subscribed_at: now,
        },
      ]);
    else if (path === "/api/meta/facebook/pages/") {
      pageChoicesRequested = true;
      data = { selection_id: null, pages: [] };
    }
    await route.fulfill({ json: data });
  });

  await page.goto("/posts");
  await expect(page.getByText("Шинэ намрын цуглуулга ирлээ.")).toBeVisible();
  await expect(page.getByRole("button", { name: "↻ Синк хийх" })).toHaveCount(
    0,
  );
  await page
    .getByRole("link", { name: "Холболтууд", exact: true })
    .first()
    .click();
  await expect(page.getByRole("heading", { name: "Холболтууд" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Демо дэлгүүр" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "+ Facebook холбох" }),
  ).toHaveCount(0);
  await expect(page.getByRole("button", { name: "↻ Синк хийх" })).toHaveCount(
    0,
  );
  await expect(page.getByRole("link", { name: "Дахин холбох" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Салгах" })).toHaveCount(0);
  expect(pageChoicesRequested).toBe(false);
});
