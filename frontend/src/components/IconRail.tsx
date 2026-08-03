import { NavLink } from "react-router-dom";

interface Item {
  to: string;
  label: string;
  path: string;
}

const ITEMS: Item[] = [
  { to: "/account", label: "내 투자", path: "M4 19h16M7 16V9m5 7V5m5 11v-5" },
  {
    to: "/",
    label: "관심",
    path: "M12 20.5 3.8 12.6a5.1 5.1 0 0 1 7.2-7.2l1 1 1-1a5.1 5.1 0 0 1 7.2 7.2z",
  },
];

/** Slim vertical rail on the far right, mirroring Toss's shortcut column. */
export default function IconRail({
  recentCount,
  onOpenRecent,
}: {
  recentCount: number;
  onOpenRecent: () => void;
}) {
  return (
    <nav className="hidden w-14 shrink-0 flex-col items-center gap-1 border-l border-line bg-base py-5 2xl:flex">
      {ITEMS.map((item) => (
        <NavLink
          key={item.label}
          to={item.to}
          className={({ isActive }) =>
            `flex w-full flex-col items-center gap-1 rounded-xl py-2.5 text-2xs transition-colors ${
              isActive ? "text-ink" : "text-ink-faint hover:text-ink-muted"
            }`
          }
        >
          <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden>
            <path
              d={item.path}
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          {item.label}
        </NavLink>
      ))}

      <button
        type="button"
        onClick={onOpenRecent}
        className="flex w-full flex-col items-center gap-1 rounded-xl py-2.5 text-2xs text-ink-faint transition-colors hover:text-ink-muted"
      >
        <span className="relative">
          <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden>
            <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path
              d="M12 7v5l3 2"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
          {recentCount > 0 && (
            <span className="absolute -right-1.5 -top-1 grid h-3.5 min-w-3.5 place-items-center rounded-full bg-brand px-1 text-[9px] font-bold text-white">
              {recentCount}
            </span>
          )}
        </span>
        최근 본
      </button>
    </nav>
  );
}
