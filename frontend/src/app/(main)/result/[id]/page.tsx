import ResultView from "@/components/ResultView";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function RealResultPage({ params }: PageProps) {
  const { id } = await params;
  return <ResultView batchId={id} />;
}
