import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "홈", end: true },
  { to: "/account", label: "내 계좌", end: false },
];

export default function TopNav() {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-8 bg-base/90 px-6 backdrop-blur">
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
    </header>
  );
}
