import { formatDistanceToNow } from "../utils/date";
import type { Campaign, SurveyType, CampaignStatus } from "../types";
import { CheckCircle2, AlertTriangle, XCircle, FileText, ChevronRight } from "lucide-react";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function surveyTypePill(type: SurveyType) {
  const map: Record<SurveyType, { bg: string; text: string }> = {
    CSAT: { bg: "bg-sky-900/40", text: "text-sky-400" },
    NPS: { bg: "bg-indigo-900/40", text: "text-indigo-400" },
    "Yes-No": { bg: "bg-teal-900/40", text: "text-teal-400" },
    Open: { bg: "bg-slate-800", text: "text-slate-400" },
  };
  const { bg, text } = map[type];
  return (
    <span className={`badge ${bg} ${text} text-xs font-semibold uppercase tracking-wide`}>
      {type}
    </span>
  );
}

function statusBadge(status: CampaignStatus) {
  const map: Record<
    CampaignStatus,
    { bg: string; text: string; icon: React.ReactNode }
  > = {
    Healthy: {
      bg: "bg-emerald-900/30",
      text: "text-emerald-400",
      icon: <CheckCircle2 size={12} />,
    },
    "Needs Action": {
      bg: "bg-amber-900/30",
      text: "text-amber-400",
      icon: <AlertTriangle size={12} />,
    },
    Critical: {
      bg: "bg-rose-900/30",
      text: "text-rose-400",
      icon: <XCircle size={12} />,
    },
    Draft: {
      bg: "bg-slate-800",
      text: "text-slate-400",
      icon: <FileText size={12} />,
    },
  };
  const { bg, text, icon } = map[status];
  return (
    <span className={`badge ${bg} ${text}`}>
      {icon}
      {status}
    </span>
  );
}

function ScoreDisplay({ campaign }: { campaign: Campaign }) {
  if (campaign.surveyType === "Yes-No") {
    const pct = campaign.yesPercent ?? 0;
    const color = pct >= 75 ? "text-emerald-400" : pct >= 50 ? "text-amber-400" : "text-rose-400";
    return (
      <div className="text-right">
        <div className={`text-lg font-bold ${color}`}>{pct}%</div>
        <div className="text-xs text-slate-500">Yes</div>
      </div>
    );
  }

  if (campaign.averageScore === null) return <span className="text-slate-600">—</span>;

  const score = campaign.averageScore;
  let color = "text-emerald-400";
  if (campaign.surveyType === "CSAT") {
    color = score >= 4 ? "text-emerald-400" : score >= 3 ? "text-amber-400" : "text-rose-400";
  } else if (campaign.surveyType === "NPS") {
    color = score >= 30 ? "text-emerald-400" : score >= 0 ? "text-amber-400" : "text-rose-400";
  }

  return (
    <div className="text-right">
      <div className={`text-lg font-bold ${color}`}>
        {campaign.surveyType === "NPS" && score > 0 ? `+${score}` : score}
      </div>
      <div className="text-xs text-slate-500">
        {campaign.surveyType === "NPS" ? "NPS" : "/ 5"}
      </div>
    </div>
  );
}

function ResponseBar({ received, total }: { received: number; total: number }) {
  const pct = Math.round((received / total) * 100);
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
        <span className="font-medium">{received.toLocaleString()}</span>
        <span className="text-slate-600">{pct}%</span>
      </div>
      <div className="h-1 bg-slate-800 rounded-full w-24">
        <div
          className="h-1 rounded-full bg-violet-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-xs text-slate-600 mt-1">of {total.toLocaleString()}</div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface RecentCampaignsProps {
  campaigns: Campaign[];
}

export function RecentCampaigns({ campaigns }: RecentCampaignsProps) {
  return (
    <section className="card p-5">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-base font-semibold text-slate-100">
            Recent Campaigns
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {campaigns.length} campaigns sent in the last 30 days
          </p>
        </div>
        <button className="text-xs text-violet-400 hover:text-violet-300 transition-colors flex items-center gap-1">
          View all <ChevronRight size={12} />
        </button>
      </div>

      <div className="overflow-x-auto -mx-5">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left">
              <th className="pb-3 pl-5 text-xs font-medium text-slate-500 uppercase tracking-wide w-[30%]">
                Campaign
              </th>
              <th className="pb-3 text-xs font-medium text-slate-500 uppercase tracking-wide">
                Type
              </th>
              <th className="pb-3 text-xs font-medium text-slate-500 uppercase tracking-wide">
                Responses
              </th>
              <th className="pb-3 text-xs font-medium text-slate-500 uppercase tracking-wide text-right">
                Score
              </th>
              <th className="pb-3 text-xs font-medium text-slate-500 uppercase tracking-wide">
                Status
              </th>
              <th className="pb-3 pr-5 text-xs font-medium text-slate-500 uppercase tracking-wide">
                Sent
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {campaigns.map((c) => (
              <tr
                key={c.id}
                className="hover:bg-slate-800/30 transition-colors group cursor-pointer"
              >
                <td className="py-3.5 pl-5">
                  <div className="font-medium text-slate-200 group-hover:text-white transition-colors truncate max-w-[220px]">
                    {c.name}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">{c.audience}</div>
                </td>
                <td className="py-3.5">{surveyTypePill(c.surveyType)}</td>
                <td className="py-3.5">
                  <ResponseBar
                    received={c.responsesReceived}
                    total={c.totalSent}
                  />
                </td>
                <td className="py-3.5 text-right">
                  <ScoreDisplay campaign={c} />
                </td>
                <td className="py-3.5">{statusBadge(c.status)}</td>
                <td className="py-3.5 pr-5 text-xs text-slate-500 whitespace-nowrap">
                  {formatDistanceToNow(c.sentAt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
