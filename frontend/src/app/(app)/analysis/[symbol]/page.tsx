import type { Metadata } from "next";
import { notFound } from "next/navigation";
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

export default async function StockAnalysisPage({ params }: PageProps<"/analysis/[symbol]">) {
  const { symbol } = await params;
  const analysis = await data.getAnalysis(symbol);
  if (!analysis) notFound();
  return <AnalysisView key={analysis.stock.symbol} a={analysis} />;
}
