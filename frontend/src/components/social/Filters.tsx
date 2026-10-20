import Icon from "@/components/ui/Icon";
import type { Account } from "@/types/api";

export default function Filters({
  accounts,
  platform,
  account,
  search,
  searchPlaceholder,
  onPlatformChange,
  onAccountChange,
  onSearchChange,
}: {
  accounts: Account[];
  platform: string;
  account: string;
  search: string;
  searchPlaceholder: string;
  onPlatformChange: (value: string) => void;
  onAccountChange: (value: string) => void;
  onSearchChange: (value: string) => void;
}) {
  const platforms = [...new Set(accounts.map((item) => item.platform))];
  const visibleAccounts = accounts.filter((item) => !platform || item.platform === platform);
  return (
    <div className="filter-bar">
      <label className="filter-wrap">
        <span className="sr-only">Суваг</span>
        <select
          aria-label="Суваг"
          className="filter-select"
          value={platform}
          onChange={(event) => onPlatformChange(event.target.value)}
        >
          <option value="">Бүх суваг</option>
          {platforms.map((item) => (
            <option key={item} value={item}>
              {item === "FACEBOOK_PAGE" ? "Facebook" : item}
            </option>
          ))}
        </select>
      </label>
      <label className="filter-wrap account-filter">
        <span className="sr-only">Хаяг</span>
        <select
          aria-label="Хаяг"
          className="filter-select"
          value={account}
          onChange={(event) => onAccountChange(event.target.value)}
        >
          <option value="">Бүх хаяг</option>
          {visibleAccounts.map((item) => (
            <option key={item.id} value={item.id}>
              {item.display_name}
            </option>
          ))}
        </select>
      </label>
      <label className="search-input">
        <Icon name="search" size={17} />
        <input
          aria-label={searchPlaceholder}
          placeholder={searchPlaceholder}
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>
    </div>
  );
}
