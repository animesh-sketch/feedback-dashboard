import { useState } from "react";
import {
  Bell,
  Settings,
  Search,
  RefreshCw,
  ChevronDown,
  Zap,
} from "lucide-react";
import { FeedbackHealthSummary } from "./components/FeedbackHealthSummary";
import { RecentCampaigns } from "./components/RecentCampaigns";
import { ActionQueue } from "./components/ActionQueue";
import { SmartNextActions } from "./components/SmartNextActions";
import { mockDashboardData } from "./data/mockData";
import { formatDate } from "./utils/date";

function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-[#0f1117]/90 backdrop-blur-sm">
      <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between gap-4">
        {/* Logo */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <span className="font-semibold text-slate-100 text-sm tracking-tight">
            PulseSignal
          </span>
          <span className="hidden sm:block text-slate-600 text-xs">
            / Dashboard
          </span>
        </div>

        {/* Search */}
        <div className="flex-1 max-w-sm hidden md:flex items-center gap-2 bg-slate-800/60 border border-slate-700/50 rounded-xl px-3 py-2 text-sm text-slate-500">
          <Search size={14} />
          <input
            type="text"
            placeholder="Search campaigns, customers..."
            className="bg-transparent outline-none flex-1 text-slate-300 placeholder:text-slate-600 text-xs"
          />
          <kbd className="text-[10px] bg-slate-700 text-slate-500 px-1.5 py-0.5 rounded">
            ⌘K
          </kbd>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2 shrink-0">
          <button className="relative w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 flex items-center justify-center transition-colors">
            <Bell size={14} className="text-slate-400" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center">
              3
            </span>
          </button>
          <button className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 flex items-center justify-center transition-colors">
            <Settings size={14} className="text-slate-400" />
          </button>
          <button className="flex items-center gap-2 bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded-xl px-3 py-1.5 transition-colors">
            <div className="w-5 h-5 rounded-full bg-violet-500 flex items-center justify-center text-[10px] font-bold text-white">
              A
            </div>
            <span className="text-xs text-slate-300 hidden sm:block">Animesh</span>
            <ChevronDown size={12} className="text-slate-500" />
          </button>
        </div>
      </div>
    </header>
  );
}

function PageHeader({
  lastUpdated,
  onRefresh,
  isRefreshing,
}: {
  lastUpdated: string;
  onRefresh: () => void;
  isRefreshing: boolean;
}) {
  return (
    <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">
          Good morning, Animesh 👋
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Here's what's happening with your customer feedback today.{" "}
          <span className="text-amber-400 font-medium">
            2 items need urgent attention.
          </span>
        </p>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-600">
          Updated {formatDate(lastUpdated)}
        </span>
        <button
          onClick={onRefresh}
          className={`btn btn-ghost text-xs py-1.5 px-3 ${isRefreshing ? "opacity-70 pointer-events-none" : ""}`}
        >
          <RefreshCw
            size={12}
            className={isRefreshing ? "animate-spin" : ""}
          />
          Refresh
        </button>
      </div>
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [data] = useState(mockDashboardData);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "campaigns" | "queue">("overview");

  function handleRefresh() {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1200);
  }

  const tabs = [
    { id: "overview" as const, label: "Overview" },
    { id: "campaigns" as const, label: "Campaigns" },
    { id: "queue" as const, label: "Action Queue", badge: data.actionQueue.length },
  ];

  return (
    <div className="min-h-screen bg-[#0f1117]">
      <Header />

      <main className="max-w-screen-xl mx-auto px-4 md:px-6 py-6">
        <PageHeader
          lastUpdated={data.lastUpdated}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />

        {/* Tabs */}
        <div className="flex items-center gap-1 mb-6 bg-slate-900/60 border border-slate-800 rounded-xl p-1 w-fit">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                activeTab === tab.id
                  ? "bg-violet-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
              {tab.badge !== undefined && (
                <span
                  className={`text-[11px] px-1.5 py-0.5 rounded-full font-semibold ${
                    activeTab === tab.id
                      ? "bg-white/20 text-white"
                      : "bg-slate-700 text-slate-400"
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="space-y-5">
            {/* KPI Row */}
            <FeedbackHealthSummary data={data.health} />

            {/* Smart Actions */}
            <SmartNextActions actions={data.smartActions} />

            {/* Two-column: Campaigns + Action Queue */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2">
                <RecentCampaigns campaigns={data.campaigns} />
              </div>
              <div className="lg:col-span-1">
                <ActionQueue items={data.actionQueue} />
              </div>
            </div>
          </div>
        )}

        {/* Campaigns Tab */}
        {activeTab === "campaigns" && (
          <div className="space-y-5">
            <FeedbackHealthSummary data={data.health} />
            <RecentCampaigns campaigns={data.campaigns} />
          </div>
        )}

        {/* Queue Tab */}
        {activeTab === "queue" && (
          <div className="space-y-5">
            <ActionQueue items={data.actionQueue} />
          </div>
        )}
      </main>
    </div>
  );
}
