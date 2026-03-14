export default function TopicPage({ params }: { params: { topic: string } }) {
  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-semibold">Tema: {params.topic}</h1>
      <p className="mt-4 text-neutral-600">Vista placeholder de topic.</p>
    </main>
  );
}
