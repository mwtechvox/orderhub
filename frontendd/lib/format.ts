export function dateTime(value: string | null): string {
  if (!value) return "";
  const parts = new Intl.DateTimeFormat("en-GB", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Ulaanbaatar",
  }).formatToParts(new Date(value));
  const part = (type: string) =>
    parts.find((p) => p.type === type)?.value ?? "";
  return `${part("month")}/${part("day")} · ${part("hour")}:${part("minute")}`;
}
