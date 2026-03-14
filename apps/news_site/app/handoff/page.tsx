import { loadHandoff } from "@/lib/adapter/mappers";

export default function HandoffPage() {
  const handoff = loadHandoff();

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-semibold">Editorial handoff</h1>
      <pre className="mt-6 overflow-x-auto rounded border p-4 text-sm">
        {JSON.stringify(handoff, null, 2)}
      </pre>
    </main>
  );
}
