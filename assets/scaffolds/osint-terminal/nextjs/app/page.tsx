import { DegradedBanner, KpiList, PageHeader } from "./components/PagePrimitives";

// Demo content — replace with your real data sources.
const KPIS = [
  { label: "ASSETS TRACKED", value: "1,204", delta: "+12 last hr", tone: "neutral" as const },
  { label: "LIVE SOURCES", value: "08 / 08", delta: "all responding", tone: "ok" as const },
  { label: "ALERTS (24H)", value: "23", delta: "+5 vs prev", tone: "warn" as const },
  { label: "QUARANTINED", value: "01", delta: "manual review", tone: "alert" as const },
];

const FEED = [
  { id: "F-0921", source: "OSINT", level: "INFO", body: "Scheduled sweep completed (8/8 sources)." },
  { id: "F-0922", source: "INGEST", level: "WARN", body: "Source #04 latency 2.4s (threshold 1.5s)." },
  { id: "F-0923", source: "ALERT", level: "RED",  body: "Pattern match: terminal-grade emergent signature." },
  { id: "F-0924", source: "OSINT", level: "INFO", body: "Daily digest queued for 18:00 UTC+7." },
];

const LEVEL_TAG: Record<string, string> = {
  INFO: "label-tag-cyan",
  WARN: "label-tag-amber",
  RED: "label-tag-red",
};

export default function HomePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        moduleTag="MOD-01"
        moduleLabel="overview"
        title="Intelligence Overview"
        subtitle="Cross-source signal aggregation. Pure visual scaffold — wire your data sources into KpiList and the FEED panel."
        right={
          <span className="label-tag-mute font-normal normal-case">
            sweep // 600s
          </span>
        }
      />

      <DegradedBanner
        visible={false}
        message="One or more sources are degraded. Some panels may show stale data."
      />

      <KpiList items={KPIS} />

      <section className="panel">
        <header className="section-heading px-4 pt-4">
          <span>SIGNAL FEED</span>
          <span className="ascii-bracket">last 4</span>
        </header>
        <ol role="list" className="divide-y divide-border">
          {FEED.map((row) => (
            <li
              key={row.id}
              className="grid grid-cols-[80px_80px_60px_1fr] items-center gap-3 px-4 py-3 text-sm hover:bg-panel-elev"
            >
              <span className="font-mono text-text-muted">{row.id}</span>
              <span className="text-[11px] uppercase tracking-widest text-text-mute">
                {row.source}
              </span>
              <span className={LEVEL_TAG[row.level] ?? "label-tag-mute"}>
                {row.level}
              </span>
              <span className="text-text-base">{row.body}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
