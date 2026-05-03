import type { ReactNode } from "react";

/* ============================================================
 * <PageHeader />
 * Module tag (uppercase pill) + title + subtitle. Drops into
 * the top of any route as the section identifier.
 * ============================================================ */
export function PageHeader({
  moduleTag,
  moduleLabel,
  title,
  subtitle,
  right,
}: {
  moduleTag: string;
  moduleLabel: string;
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <section className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-text-muted">
          <span className="label-tag-cyan">{moduleTag}</span>
          <span className="ascii-bracket">{moduleLabel}</span>
        </div>
        <h1 className="mt-3 text-2xl font-semibold uppercase tracking-wider text-text-base">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-1 max-w-2xl text-sm text-text-mute">{subtitle}</p>
        ) : null}
      </div>
      {right ? <div className="flex items-center gap-2">{right}</div> : null}
    </section>
  );
}

/* ============================================================
 * <KpiList />
 * Inline grid of "label / value / delta" tiles. Pure visual —
 * format the values yourself.
 * ============================================================ */
export type KpiItem = {
  label: string;
  value: ReactNode;
  delta?: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "alert";
};

const TONE_CLASS: Record<NonNullable<KpiItem["tone"]>, string> = {
  neutral: "text-text-base",
  ok: "text-accent-green",
  warn: "text-accent-amber",
  alert: "text-accent-red",
};

export function KpiList({ items }: { items: ReadonlyArray<KpiItem> }) {
  return (
    <ul
      role="list"
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
    >
      {items.map((k) => (
        <li key={String(k.label)} className="panel p-4">
          <p className="text-[10px] uppercase tracking-widest text-text-muted">
            {k.label}
          </p>
          <p
            className={[
              "mt-2 text-2xl font-semibold tabular-nums",
              TONE_CLASS[k.tone ?? "neutral"],
            ].join(" ")}
          >
            {k.value}
          </p>
          {k.delta ? (
            <p className="mt-1 text-[11px] uppercase tracking-wider text-text-mute">
              {k.delta}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

/* ============================================================
 * <DegradedBanner />
 * Renders only when `visible` — call sites pass a boolean derived
 * from data-source health (rate-limited / fallback / offline …).
 * ============================================================ */
export function DegradedBanner({
  visible,
  message,
}: {
  visible: boolean;
  message: string;
}) {
  if (!visible) return null;
  return (
    <div role="alert" className="panel border-l-2 border-l-accent-red">
      <div className="flex items-center gap-3 p-3">
        <span className="status-dot status-dot-red" aria-hidden />
        <span className="text-[11px] uppercase tracking-widest text-accent-red">
          DEGRADED
        </span>
        <span className="text-sm text-text-mute">{message}</span>
      </div>
    </div>
  );
}
