import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { KPIMetric } from "../../types";

interface TrendBadgeProps {
  metric: KPIMetric;
}

export function TrendBadge({ metric }: TrendBadgeProps) {
  const delta = metric.value - metric.previousValue;
  const pctChange =
    metric.previousValue !== 0
      ? ((delta / Math.abs(metric.previousValue)) * 100).toFixed(1)
      : "0";

  const isPositive = metric.higherIsBetter ? delta > 0 : delta < 0;
  const isNeutral = delta === 0;

  if (isNeutral) {
    return (
      <span className="badge bg-slate-800 text-slate-400">
        <Minus size={10} />
        No change
      </span>
    );
  }

  if (isPositive) {
    return (
      <span className="badge bg-emerald-900/40 text-emerald-400">
        <TrendingUp size={10} />
        {Math.abs(Number(pctChange))}%
      </span>
    );
  }

  return (
    <span className="badge bg-rose-900/40 text-rose-400">
      <TrendingDown size={10} />
      {Math.abs(Number(pctChange))}%
    </span>
  );
}
