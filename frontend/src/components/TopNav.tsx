import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "홈", end: true },
  { to: "/account", label: "내 계좌", end: false },
];

export default function TopNav({ onOpenSearch }: { onOpenSearch: () => void }) {
  // Solid background, not backdrop-blur: blurring a sticky full-width bar forces
  // a repaint of everything behind it on every scroll frame.
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-8 bg-base px-6">
      <div className="flex items-center gap-2.5">
        <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden>
          <circle cx="13" cy="13" r="13" fill="#3182F6" />
          <path
            d="M6.5 16.5 L10.5 11 L14 14 L19.5 7.5"
            fill="none"
            stroke="#fff"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="text-lg font-bold tracking-tight">AI 트레이더</span>
      </div>

      <nav className="flex items-center gap-1">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-[0.95rem] font-semibold transition-colors ${
                isActive ? "text-ink" : "text-ink-faint hover:text-ink-muted"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <button
        type="button"
        onClick={onOpenSearch}
        className="ml-auto flex w-72 items-center gap-2.5 rounded-xl bg-surface px-3.5 py-2 text-sm text-ink-faint transition-colors hover:bg-hover"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden>
          <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
          <path d="M16.5 16.5 21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <span className="flex-1 text-left">종목 검색</span>
        <kbd className="rounded border border-line px-1.5 py-0.5 text-2xs">/</kbd>
      </button>
    </header>
  );
}
