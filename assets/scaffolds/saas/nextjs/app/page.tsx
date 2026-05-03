import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardBody, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function Page() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-24 space-y-10">
      <header className="space-y-4">
        <h1 className="text-5xl font-heading font-bold tracking-tight leading-vn-heading">
          Ship your SaaS faster
        </h1>
        <p className="text-lg font-body text-vck-neutral leading-vn-body">
          Next.js + NextAuth + Prisma starter — scaffolded by VibecodeKit
          (preset: saas). Tokens (CP-01..CP-06, FP-01) đã pre-wired qua{" "}
          <code className="mx-1 rounded bg-vck-neutral/10 px-1">tailwind.config.ts</code>{" "}
          +{" "}
          <code className="mx-1 rounded bg-vck-neutral/10 px-1">design/tokens.css</code>.
        </p>
      </header>

      <nav aria-label="primary" className="flex flex-wrap gap-4">
        <Link
          href="/auth/login"
          className="inline-flex items-center justify-center rounded-lg bg-vck-trust px-5 py-2.5 text-base font-body text-white hover:bg-vck-trust/90"
        >
          Đăng nhập
        </Link>
        <Link
          href="/dashboard"
          className="inline-flex items-center justify-center rounded-lg bg-vck-neutral/10 px-5 py-2.5 text-base font-body text-vck-neutral hover:bg-vck-neutral/20"
        >
          Vào dashboard
        </Link>
      </nav>

      <section className="space-y-3">
        <label htmlFor="newsletter" className="font-heading text-vck-trust">
          Đăng ký nhận update
        </label>
        <Input
          id="newsletter"
          type="email"
          placeholder="ban@example.vn"
        />
        <Button variant="primary" size="md" type="submit">
          Đăng ký
        </Button>
      </section>

      <section className="grid gap-6 sm:grid-cols-2">
        <Card variant="elevated">
          <CardTitle>Tokens consumption</CardTitle>
          <CardBody>
            Component này dùng <code>bg-vck-trust</code>,{" "}
            <code>text-vck-neutral</code>, <code>font-heading</code> — đổi
            HEX trong methodology là cả app cập nhật.
          </CardBody>
        </Card>
        <Card variant="bordered">
          <CardTitle>VN typography</CardTitle>
          <CardBody>
            <code>leading-vn-body</code> (1.6) +{" "}
            <code>leading-vn-heading</code> (1.2) đảm bảo dấu tiếng Việt
            không bị cắt.
          </CardBody>
        </Card>
      </section>
    </main>
  );
}
