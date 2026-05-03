import { Button } from "@/components/ui/button";
import { Card, CardBody, CardTitle } from "@/components/ui/card";

const KPIS = [
  { label: "Revenue", value: "120M đ", delta: "+12%", trend: "up" as const },
  { label: "Active users", value: "3,402", delta: "+8%", trend: "up" as const },
  { label: "Orders", value: "881", delta: "-3%", trend: "down" as const },
];

export default function Dashboard() {
  return (
    <main className="p-12 max-w-6xl mx-auto space-y-12 font-body">
      <header className="flex items-baseline justify-between">
        <h1 className="text-3xl font-heading font-bold leading-vn-heading text-vck-trust">
          Dashboard
        </h1>
        <Button variant="ghost" size="sm" type="button">
          Xuất CSV
        </Button>
      </header>

      <ul className="grid gap-6 sm:grid-cols-3">
        {KPIS.map((k) => (
          <li key={k.label}>
            <Card variant="elevated">
              <CardTitle>{k.label}</CardTitle>
              <CardBody>
                <p className="text-3xl font-heading font-bold text-vck-neutral">
                  {k.value}
                </p>
                <p
                  className={
                    "mt-1 text-sm " +
                    (k.trend === "up"
                      ? "text-vck-growth"
                      : "text-vck-warning")
                  }
                >
                  {k.delta}
                </p>
              </CardBody>
            </Card>
          </li>
        ))}
      </ul>

      <Card variant="bordered">
        <CardTitle>Trend</CardTitle>
        <CardBody>
          Wire <code>recharts</code>&apos; AreaChart here once data is
          available. Token-driven palette: line uses{" "}
          <code>stroke-vck-trust</code>, anomalies highlight{" "}
          <code>vck-warning</code>.
        </CardBody>
      </Card>
    </main>
  );
}
