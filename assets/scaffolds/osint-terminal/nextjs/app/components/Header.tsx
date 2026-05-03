"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

// Edit `NAV_ITEMS` to match your route map.
const NAV_ITEMS: ReadonlyArray<{ id: string; label: string; href: string }> = [
  { id: "01", label: "OVERVIEW", href: "/" },
  { id: "02", label: "INTAKE", href: "/intake" },
  { id: "03", label: "FEED", href: "/feed" },
  { id: "04", label: "STATS", href: "/stats" },
];

// Live clock in Indochina Time (UTC+7, Asia/Ho_Chi_Minh).
// `sv-SE` locale formats as `YYYY-MM-DD HH:mm:ss` natively.
// Hoisted so the formatter is constructed once, not on every render tick.
const CLOCK_FORMATTER = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Asia/Ho_Chi_Minh",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

export function Header({ hasToken }: { hasToken: boolean }) {
  const pathname = usePathname();
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const stamp = now ? `${CLOCK_FORMATTER.format(now)} UTC+7` : "—";

  return (
    <header className="fixed inset-x-0 top-0 z-30 border-b border-border bg-panel/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3">
        {/* Logotype */}
        <div className="flex items-center gap-3">
          <span className="status-dot status-dot-cyan" aria-hidden />
          <Link
            href="/"
            className="text-sm uppercase tracking-widest text-text-base hover:text-accent-cyan"
          >
            <span className="text-accent-cyan">/</span>OSINT
            <span className="text-text-muted">.terminal</span>
          </Link>
          <span className="hidden text-[10px] uppercase tracking-widest text-text-muted sm:inline">
            v0.1
          </span>
        </div>

        {/* Nav */}
        <nav aria-label="Primary" className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            // Exact match for the root, otherwise either exact or `prefix + "/"`
            // to avoid `/news` matching `/new`.
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname === item.href ||
                  pathname?.startsWith(item.href + "/") === true;
            return (
              <Link
                key={item.id}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={[
                  "flex items-center gap-2 rounded-sm border px-3 py-1 text-[11px] uppercase tracking-widest transition-colors",
                  active
                    ? "border-accent-cyan/60 bg-accent-cyan/10 text-accent-cyan"
                    : "border-border bg-panel-elev/40 text-text-mute hover:border-accent-cyan/40 hover:text-accent-cyan",
                ].join(" ")}
              >
                <span className="text-text-muted">{item.id}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Status pills */}
        <div className="hidden items-center gap-2 lg:flex">
          <span className="label-tag-cyan">
            <span className="status-dot status-dot-cyan" aria-hidden /> LIVE
          </span>
          <span
            className={hasToken ? "label-tag-green" : "label-tag-amber"}
            aria-label={hasToken ? "auth token configured" : "auth token missing"}
          >
            <span
              className={
                hasToken
                  ? "status-dot status-dot-green"
                  : "status-dot status-dot-amber"
              }
              aria-hidden
            />
            TOKEN {hasToken ? "OK" : "MISSING"}
          </span>
          <span className="label-tag-mute font-normal normal-case tracking-wider">
            {stamp}
          </span>
        </div>
      </div>
    </header>
  );
}
