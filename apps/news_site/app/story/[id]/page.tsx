export default function StoryPage({ params }: { params: { id: string } }) {
  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-semibold">Story: {params.id}</h1>
      <p className="mt-4 text-neutral-600">Vista placeholder de story.</p>
    </main>
  );
}
