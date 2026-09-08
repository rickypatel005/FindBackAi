import Link from "next/link";
import { Button } from "@/components/Button";

const STEPS = [
  {
    title: "Report",
    body: "Upload a photo and a few details about the item you lost or found.",
  },
  {
    title: "AI matches",
    body: "FindBack AI compares images, descriptions, and metadata to surface likely matches.",
  },
  {
    title: "Get notified",
    body: "When a strong match appears, you're notified in-app — with a plain-language reason why.",
  },
];

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-16">
      <header className="flex items-center justify-between">
        <span className="text-xl font-semibold">FindBack AI</span>
        <nav className="flex gap-3">
          <Link href="/login">
            <Button variant="neutral">Log in</Button>
          </Link>
          <Link href="/register">
            <Button variant="found">Register</Button>
          </Link>
        </nav>
      </header>

      <section className="mt-24 max-w-2xl">
        <h1 className="text-4xl font-bold leading-tight text-slate-900 sm:text-5xl">
          Lost something? <span className="text-lost">Found something?</span>
          <br />
          Let AI find the match.
        </h1>
        <p className="mt-6 text-lg text-slate-600">
          FindBack AI compares photos, descriptions, and details across lost and found
          reports to surface — and explain — the most likely matches, so you don&apos;t
          have to search manually.
        </p>
        <div className="mt-8 flex gap-4">
          <Link href="/register">
            <Button variant="lost">Report a lost item</Button>
          </Link>
          <Link href="/register">
            <Button variant="found">Report a found item</Button>
          </Link>
        </div>
      </section>

      <section className="mt-24">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          How it works
        </h2>
        <div className="mt-6 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <div key={step.title} className="rounded-xl border border-slate-200 bg-white p-6">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                {i + 1}
              </div>
              <h3 className="font-semibold text-slate-900">{step.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{step.body}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
