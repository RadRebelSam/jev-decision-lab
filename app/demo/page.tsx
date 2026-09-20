import { Suspense } from "react";
import { PersonalizationDemo } from "@/components/personalization-demo";

export default function DemoPage() {
  return (
    <Suspense fallback={<main className="demo-loading">Loading personalization demo…</main>}>
      <PersonalizationDemo />
    </Suspense>
  );
}
