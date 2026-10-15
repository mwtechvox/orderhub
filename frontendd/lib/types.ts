export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export type Company = { id: string; name: string; slug: string };
export type Me = {
  id: number;
  username: string;
  active_company: string | null;
  active_company_role: "OWNER" | "ADMIN" | "AGENT" | null;
};
export type Media = { type: string; url: string };
export type Post = {
  id: string;
  social_account: string;
  platform: string;
  page_name: string;
  origin: "FACEBOOK_SYNC" | "ORDERHUB";
  status: "DRAFT" | "SCHEDULED" | "PUBLISHED" | "FAILED" | "DELIVERY_UNKNOWN";
  message: string;
  permalink_url: string;
  media: Media[];
  comment_count: number;
  reaction_count: number;
  created_at_platform: string;
  scheduled_at: string | null;
  published_at: string | null;
  publish_error_code: string | null;
  comment_automation: CommentAutomationRule | null;
};
export type Comment = {
  id: string;
  post: string;
  parent_comment: string | null;
  author_name: string;
  message: string;
  can_reply: boolean;
  created_at_platform: string;
};
export type CommentReplyAttempt = {
  id: string;
  comment: string;
  text: string;
  status: "SENT" | "FAILED" | "DELIVERY_UNKNOWN";
  error_code: string | null;
  created_at: string;
  updated_at: string;
};
export type Account = {
  id: string;
  platform: string;
  display_name: string;
  status: "ACTIVE" | "NEEDS_REAUTH" | "DISCONNECTED";
  last_synced_at: string | null;
  sync_status: string;
  last_error: string;
  webhook_subscribed_at: string | null;
};
export type CommentAutomationRule = {
  is_enabled: boolean;
  public_reply_enabled: boolean;
  public_reply_text: string;
  private_reply_enabled: boolean;
  private_reply_text: string;
  created_at: string | null;
  updated_at: string | null;
};
export type Conversation = {
  id: string;
  customer: { id: string; name: string };
  social_account: string;
  platform: string;
  page_name: string;
  last_message: string;
  last_message_at: string | null;
  unread_count: number;
  last_inbound_at: string | null;
  can_reply: boolean;
};
export type Message = {
  id: string;
  conversation: string;
  direction: "INBOUND" | "OUTBOUND";
  text: string;
  attachments: Media[];
  status: "RECEIVED" | "PENDING" | "SENDING" | "SENT" | "FAILED";
  sent_at: string;
  error_code: string | null;
};
