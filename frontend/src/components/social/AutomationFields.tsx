import type { CommentAutomationRule } from "@/types/api";

export const DEFAULT_AUTOMATION: CommentAutomationRule = {
  is_enabled: false,
  public_reply_enabled: true,
  public_reply_text: "Мэдээллийг чат руу илгээлээ. Чатаа шалгаарай 😊",
  private_reply_enabled: true,
  private_reply_text:
    "Сайн байна уу 👋\n\nМанай бүтээгдэхүүний дэлгэрэнгүй мэдээллийг танд чат руу илгээлээ.\n\nЗахиалах бол энэ чатад хариу бичээрэй.",
  created_at: null,
  updated_at: null,
};

export default function AutomationFields({
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
          onChange={(event) => onChange({ ...value, is_enabled: event.target.checked })}
        />
        <span>Автомат хариу {value.is_enabled ? "идэвхтэй" : "унтраалттай"}</span>
      </label>
      <label className="toggle-row">
        <input
          type="checkbox"
          checked={value.public_reply_enabled}
          disabled={disabled}
          onChange={(event) => onChange({ ...value, public_reply_enabled: event.target.checked })}
        />
        <span>Нийтийн хариу илгээх</span>
      </label>
      <textarea
        aria-label="Нийтийн автомат хариу"
        maxLength={8000}
        disabled={disabled || !value.public_reply_enabled}
        value={value.public_reply_text}
        onChange={(event) => onChange({ ...value, public_reply_text: event.target.value })}
      />
      <label className="toggle-row">
        <input
          type="checkbox"
          checked={value.private_reply_enabled}
          disabled={disabled}
          onChange={(event) => onChange({ ...value, private_reply_enabled: event.target.checked })}
        />
        <span>Хувийн мессеж илгээх</span>
      </label>
      <textarea
        aria-label="Хувийн автомат мессеж"
        maxLength={2000}
        disabled={disabled || !value.private_reply_enabled}
        value={value.private_reply_text}
        onChange={(event) => onChange({ ...value, private_reply_text: event.target.value })}
      />
    </div>
  );
}
