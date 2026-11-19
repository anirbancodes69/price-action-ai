import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { PageSkeleton } from "@/components/data/loading-skeleton";
import { data } from "@/lib/data";
import { AnalysisView } from "@/features/analysis/analysis-view";

export async function generateStaticParams() {
  const symbols = await data.getAnalysisSymbols();
  return symbols.map((symbol) => ({ symbol }));
}

export async function generateMetadata({ params }: PageProps<"/analysis/[symbol]">): Promise<Metadata> {
  const { symbol } = await params;
  return { title: `${decodeURIComponent(symbol).toUpperCase()} analysis` };
}

/**
 * The URL data (`params`) is read inside a Suspense boundary, so the App Shell stays shared across symbols and
 * navigation can be instant (Next.js "URL data outside of Suspense" insight).
 */
export default function StockAnalysisPage({ params }: PageProps<"/analysis/[symbol]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <StockAnalysis params={params} />
    </Suspense>
  );
}

async function StockAnalysis({ params }: Pick<PageProps<"/analysis/[symbol]">, "params">) {
  const { symbol } = await params;
  const analysis = await data.getAnalysis(symbol);
  if (!analysis) notFound();
  return <AnalysisView key={analysis.stock.symbol} a={analysis} />;
}
