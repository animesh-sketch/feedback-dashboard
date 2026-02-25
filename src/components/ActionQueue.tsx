import { Clock, Tag, ChevronRight, Flame } from "lucide-react";
import type { ActionItem, FeedbackTag } from "../types";
import { formatDistanceToNow } from "../utils/date";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function priorityConfig(priority: ActionItem["priority"]) {
  return {
    critical: {
      dot: "bg-rose-500",
      text: "text-rose-400",
      label: "Critical",
      border: "border-rose-900/40",
      bg: "hover:bg-rose-900/10",
    },
    high: {
      dot: "bg-amber-500",
      text: "text-amber-400",
      label: "High",
      border: "border-amber-900/30",
      bg: "hover:bg-amber-900/10",
    },
    medium: {
      dot: "bg-sky-500",
      text: "text-sky-400",
      label: "Medium",
      border: "border-slate-800",
      bg: "hover:bg-slate-800/40",
    },
    low: {
      dot: "bg-slate-500",
      text: "text-slate-400",
      label: "Low",
      border: "border-slate-800",
      bg: "hover:bg-slate-800/30",
    },
  }[priority];
}

const tagColors: Record<FeedbackTag, string> = {
  delay: "bg-orange-900/40 text-orange-400",
  pricing: "bg-yellow-900/40 text-yellow-400",
  "agent behavior": "bg-rose-900/40 text-rose-400",
  "product quality": "bg-purple-900/40 text-purple-400",
  "billing issue": "bg-red-900/40 text-red-400",
  "feature request": "bg-sky-900/40 text-sky-400",
  onboarding: "bg-teal-900/40 text-teal-400",
  "response time": "bg-amber-900/40 text-amber-400",
  refund: "bg-rose-900/50 text-rose-300",
  communication: "bg-indigo-900/40 text-indigo-400",
};

function ScoreDot({ score, type }: { score: number; type: ActionItem["surveyType"] }) {
  const isBad =
    type === "CSAT" ? score <= 2 :
    type === "NPS" ? score <= 4 :
    score === 0;

  const isWarn =
    type === "CSAT" ? score === 3 :
    type === "NPS" ? score <= 6 :
    false;

  const colorClass = isBad
    ? "bg-rose-500/20 text-rose-400 border-rose-700/40"
    : isWarn
    ? "bg-amber-500/20 text-amber-400 border-amber-700/40"
    : "bg-emerald-500/20 text-emerald-400 border-emerald-700/40";

  return (
    <div
      className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold border shrink-0 ${colorClass}`}
    >
      {score}
    </div>
  );
}

function SLABadge({ item }: { item: ActionItem }) {
  if (item.slaBreached) {
    return (
      <span className="badge bg-rose-900/40 text-rose-400 animate-pulse-soft">
        <Flame size={10} />
        SLA Breached · {item.hoursOpen}h open
      </span>
    );
  }
  const remaining = item.slaHours - item.hoursOpen;
  if (remaining <= 12) {
    return (
      <span className="badge bg-amber-900/40 text-amber-400">
        <Clock size={10} />
        {remaining}h to SLA
      </span>
    );
  }
  return null;
}

interface ActionItemCardProps {
  item: ActionItem;
}

function ActionItemCard({ item }: ActionItemCardProps) {
  const p = priorityConfig(item.priority);

  return (
    <div
      className={`flex gap-3 p-4 rounded-xl border ${p.border} ${p.bg} transition-all duration-200 cursor-pointer group`}
    >
      <ScoreDot score={item.score} type={item.surveyType} />

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${p.dot} shrink-0`}
              />
              <span className="font-semibold text-slate-100 text-sm">
                {item.customerName}
              </span>
              <span className="text-xs text-slate-500">{item.customerEmail}</span>
            </div>
            <div className="text-xs text-slate-500 mt-0.5 ml-4">
              {item.campaignName}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <SLABadge item={item} />
            <span className="text-xs text-slate-600">
              {formatDistanceToNow(item.receivedAt)}
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
          "{item.comment}"
        </p>

        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <Tag size={11} className="text-slate-600 shrink-0" />
          {item.tags.map((tag) => (
            <span key={tag} className={`badge text-[11px] ${tagColors[tag]}`}>
              {tag}
            </span>
          ))}
          <button className="ml-auto text-xs text-violet-400 hover:text-violet-300 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
            Resolve <ChevronRight size={11} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface ActionQueueProps {
  items: ActionItem[];
}

export function ActionQueue({ items }: ActionQueueProps) {
  const slaBreached = items.filter((i) => i.slaBreached).length;
  const sorted = [...items].sort((a, b) => {
    const prio = { critical: 0, high: 1, medium: 2, low: 3 };
    if (a.slaBreached !== b.slaBreached) return a.slaBreached ? -1 : 1;
    return prio[a.priority] - prio[b.priority];
  });

  return (
    <section className="card p-5 flex flex-col">
      <div className="flex items-start justify-between mb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-slate-100">
              Action Queue
            </h2>
            <span className="badge bg-rose-900/40 text-rose-400 font-semibold">
              {items.length}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {slaBreached > 0 && (
              <span className="text-rose-400 font-medium">
                {slaBreached} breaching SLA ·{" "}
              </span>
            )}
            Customers needing immediate follow-up
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-2.5 py-1.5 cursor-pointer">
            <option>All priorities</option>
            <option>Critical only</option>
            <option>SLA breached</option>
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-2 overflow-y-auto max-h-[520px] pr-1">
        {sorted.map((item) => (
          <ActionItemCard key={item.id} item={item} />
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-500">
          Showing {items.length} open items
        </span>
        <button className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors">
          View all issues <ChevronRight size={12} />
        </button>
      </div>
    </section>
  );
}
