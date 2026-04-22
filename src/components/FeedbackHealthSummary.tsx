import {
  Activity,
  Smile,
  TrendingDown,
  AlertCircle,
  MessageSquare,
} from "lucide-react";
import type { FeedbackHealthSummary as FHSType, KPIMetric } from "../types";
import { TrendBadge } from "./ui/TrendBadge";

interface KPICardProps {
  metric: KPIMetric;
  icon: React.ReactNode;
  accentColor: string;
  bgGlow: string;
}

function formatValue(metric: KPIMetric): string {
  switch (metric.unit) {
    case "percent":
      return `${metric.value}%`;
    case "score":
      return metric.value.toFixed(1);
    case "nps":
      return metric.value > 0 ? `+${metric.value}` : `${metric.value}`;
    case "count":
      return metric.value.toString();
  }
}

function KPICard({ metric, icon, accentColor, bgGlow }: KPICardProps) {
  const delta = metric.value - metric.previousValue;
  const isPositive = metric.higherIsBetter ? delta > 0 : delta < 0;
  const isNegative = metric.higherIsBetter ? delta < 0 : delta > 0;

  return (
    <div
      className={`card card-hover p-5 flex flex-col gap-4 relative overflow-hidden animate-fade-in`}
      style={{ animationFillMode: "both" }}
    >
      {/* Subtle glow background */}
      <div
        className={`absolute -top-8 -right-8 w-32 h-32 rounded-full opacity-10 blur-2xl ${bgGlow}`}
      />

      <div className="flex items-start justify-between relative">
        <div
          className={`w-10 h-10 rounded-xl flex items-center justify-center ${accentColor}`}
        >
          {icon}
        </div>
        <TrendBadge metric={metric} />
      </div>

      <div className="relative">
        <div
          className={`text-3xl font-bold tracking-tight ${
            isNegative
              ? "text-rose-400"
              : isPositive
              ? "text-emerald-400"
              : "text-slate-100"
          }`}
        >
          {formatValue(metric)}
        </div>
        <div className="text-sm font-medium text-slate-300 mt-0.5">
          {metric.label}
        </div>
        <div className="text-xs text-slate-500 mt-1">{metric.description}</div>
      </div>

      <div className="text-xs text-slate-500 border-t border-slate-800 pt-3 flex items-center gap-1">
        <span className="text-slate-400">
          Was{" "}
          <span className="font-medium text-slate-300">
            {formatValue({ ...metric, value: metric.previousValue })}
          </span>
        </span>
        <span className="text-slate-600">·</span>
        <span>{metric.higherIsBetter ? "higher is better" : "lower is better"}</span>
      </div>
    </div>
  );
}

interface FeedbackHealthSummaryProps {
  data: FHSType;
}

export function FeedbackHealthSummary({ data }: FeedbackHealthSummaryProps) {
  const kpis: { metric: KPIMetric; icon: React.ReactNode; accent: string; glow: string }[] = [
    {
      metric: data.responseRate,
      icon: <Activity size={18} className="text-violet-400" />,
      accent: "bg-violet-900/40",
      glow: "bg-violet-500",
    },
    {
      metric: data.averageCSAT,
      icon: <Smile size={18} className="text-sky-400" />,
      accent: "bg-sky-900/40",
      glow: "bg-sky-500",
    },
    {
      metric: data.averageNPS,
      icon: <TrendingDown size={18} className="text-indigo-400" />,
      accent: "bg-indigo-900/40",
      glow: "bg-indigo-500",
    },
    {
      metric: data.negativeFeedbackPercent,
      icon: <MessageSquare size={18} className="text-rose-400" />,
      accent: "bg-rose-900/40",
      glow: "bg-rose-500",
    },
    {
      metric: data.unresolvedCount,
      icon: <AlertCircle size={18} className="text-amber-400" />,
      accent: "bg-amber-900/40",
      glow: "bg-amber-500",
    },
  ];

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-100">
            Feedback Health
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">{data.periodLabel}</p>
        </div>
        <span className="badge bg-emerald-900/30 text-emerald-400 text-xs px-3 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
          Live
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {kpis.map(({ metric, icon, accent, glow }) => (
          <KPICard
            key={metric.id}
            metric={metric}
            icon={icon}
            accentColor={accent}
            bgGlow={glow}
          />
        ))}
      </div>
    </section>
  );
}
