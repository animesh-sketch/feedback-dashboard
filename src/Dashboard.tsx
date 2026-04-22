import { useState } from "react";
import {
  Bell,
  Settings,
  Search,
  RefreshCw,
  Zap,
  LayoutDashboard,
  Megaphone,
  ListChecks,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { FeedbackHealthSummary } from "./components/FeedbackHealthSummary";
import { RecentCampaigns } from "./components/RecentCampaigns";
import { ActionQueue } from "./components/ActionQueue";
import { SmartNextActions } from "./components/SmartNextActions";
import { mockDashboardData } from "./data/mockData";
import { formatDate } from "./utils/date";

type Tab = "overview" | "campaigns" | "queue";

// ─── Sidebar ──────────────────────────────────────────────────────────────────

function Sidebar({
  activeTab,
  onTabChange,
  queueCount,
  userName,
  onLogout,
}: {
  activeTab: Tab;
  onTabChange: (t: Tab) => void;
  queueCount: number;
  userName: string;
  onLogout: () => void;
}) {
  const navItems: { id: Tab; label: string; icon: React.ReactNode; badge?: number }[] = [
    { id: "overview", label: "Overview", icon: <LayoutDashboard size={16} /> },
    { id: "campaigns", label: "Campaigns", icon: <Megaphone size={16} /> },
    { id: "queue", label: "Action Queue", icon: <ListChecks size={16} />, badge: queueCount },
  ];

  return (
    <aside className="hidden md:flex flex-col w-56 shrink-0 bg-[#0d1117] border-r border-slate-800 min-h-screen sticky top-0 h-screen">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-14 border-b border-slate-800 shrink-0">
        <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
          <Zap size={14} className="text-white" />
        </div>
        <span className="font-semibold text-slate-100 text-sm tracking-tight">
          PulseSignal
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        <p className="text-[10px] uppercase tracking-widest text-slate-600 px-2 mb-2 font-semibold">
          Navigation
        </p>
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={`group flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-150 w-full text-left ${
              activeTab === item.id
                ? "bg-violet-600/20 text-violet-300 border border-violet-500/20"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <span
              className={`shrink-0 transition-colors ${
                activeTab === item.id ? "text-violet-400" : "text-slate-500 group-hover:text-slate-300"
              }`}
            >
              {item.icon}
            </span>
            <span className="flex-1">{item.label}</span>
            {item.badge !== undefined && (
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  activeTab === item.id
                    ? "bg-violet-500/30 text-violet-300"
                    : "bg-rose-900/50 text-rose-400"
                }`}
              >
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* User + logout */}
      <div className="px-3 pb-4 border-t border-slate-800 pt-4 shrink-0">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-7 h-7 rounded-full bg-violet-500 flex items-center justify-center text-[11px] font-bold text-white shrink-0">
            {userName[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-slate-200 truncate">{userName}</div>
            <div className="text-[10px] text-slate-500">Admin</div>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="mt-2 w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-500 hover:text-rose-400 hover:bg-rose-900/10 transition-all duration-150"
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </aside>
  );
}

// ─── Top bar ──────────────────────────────────────────────────────────────────

function Topbar({
  userName,
  activeTab,
  onTabChange,
  queueCount,
  onLogout,
}: {
  userName: string;
  activeTab: Tab;
  onTabChange: (t: Tab) => void;
  queueCount: number;
  onLogout: () => void;
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 border-b border-slate-800 bg-[#0f1117]/90 backdrop-blur-sm">
      <div className="h-14 px-4 md:px-6 flex items-center justify-between gap-4">
        {/* Mobile logo */}
        <div className="flex md:hidden items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <span className="font-semibold text-slate-100 text-sm">PulseSignal</span>
        </div>

        {/* Search */}
        <div className="flex-1 max-w-sm hidden md:flex items-center gap-2 bg-slate-800/60 border border-slate-700/50 rounded-xl px-3 py-2 text-sm text-slate-500">
          <Search size={14} />
          <input
            type="text"
            placeholder="Search campaigns, customers…"
            className="bg-transparent outline-none flex-1 text-slate-300 placeholder:text-slate-600 text-xs"
          />
          <kbd className="text-[10px] bg-slate-700 text-slate-500 px-1.5 py-0.5 rounded">
            ⌘K
          </kbd>
        </div>

        {/* Right */}
        <div className="flex items-center gap-2 shrink-0">
          <button className="relative w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 flex items-center justify-center transition-colors">
            <Bell size={14} className="text-slate-400" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center">
              3
            </span>
          </button>
          <button className="hidden md:flex w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 items-center justify-center transition-colors">
            <Settings size={14} className="text-slate-400" />
          </button>

          {/* Mobile: user + menu */}
          <button
            onClick={() => setMobileMenuOpen((v) => !v)}
            className="flex md:hidden items-center gap-2 bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded-xl px-3 py-1.5 transition-colors"
          >
            <div className="w-5 h-5 rounded-full bg-violet-500 flex items-center justify-center text-[10px] font-bold text-white">
              {userName[0].toUpperCase()}
            </div>
            <ChevronDown size={12} className="text-slate-500" />
          </button>

          {/* Desktop: user */}
          <div className="hidden md:flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-xl px-3 py-1.5">
            <div className="w-5 h-5 rounded-full bg-violet-500 flex items-center justify-center text-[10px] font-bold text-white">
              {userName[0].toUpperCase()}
            </div>
            <span className="text-xs text-slate-300">{userName}</span>
          </div>
        </div>
      </div>

      {/* Mobile nav dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-[#0d1117] px-3 py-3 flex flex-col gap-1 animate-fade-in">
          {(["overview", "campaigns", "queue"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => { onTabChange(t); setMobileMenuOpen(false); }}
              className={`flex items-center justify-between px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                activeTab === t
                  ? "bg-violet-600/20 text-violet-300"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <span className="capitalize">{t === "queue" ? "Action Queue" : t}</span>
              {t === "queue" && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-rose-900/50 text-rose-400">
                  {queueCount}
                </span>
              )}
            </button>
          ))}
          <button
            onClick={onLogout}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-500 hover:text-rose-400 hover:bg-rose-900/10 transition-all"
          >
            <LogOut size={13} />
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}

// ─── Page header ──────────────────────────────────────────────────────────────

function PageHeader({
  lastUpdated,
  onRefresh,
  isRefreshing,
  userName,
}: {
  lastUpdated: string;
  onRefresh: () => void;
  isRefreshing: boolean;
  userName: string;
}) {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">
          {greeting}, {userName} 👋
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
          className={`btn btn-ghost text-xs py-1.5 px-3 ${
            isRefreshing ? "opacity-70 pointer-events-none" : ""
          }`}
        >
          <RefreshCw size={12} className={isRefreshing ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export default function Dashboard({
  userName,
  onLogout,
}: {
  userName: string;
  onLogout: () => void;
}) {
  const [data] = useState(mockDashboardData);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  function handleRefresh() {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1200);
  }

  return (
    <div className="min-h-screen bg-[#0f1117] flex">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        queueCount={data.actionQueue.length}
        userName={userName}
        onLogout={onLogout}
      />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar
          userName={userName}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          queueCount={data.actionQueue.length}
          onLogout={onLogout}
        />

        <main className="flex-1 px-4 md:px-6 py-6 max-w-screen-xl w-full mx-auto">
          <PageHeader
            lastUpdated={data.lastUpdated}
            onRefresh={handleRefresh}
            isRefreshing={isRefreshing}
            userName={userName}
          />

          {/* Overview */}
          {activeTab === "overview" && (
            <div className="space-y-5 animate-fade-in">
              <FeedbackHealthSummary data={data.health} />
              <SmartNextActions actions={data.smartActions} />
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

          {/* Campaigns */}
          {activeTab === "campaigns" && (
            <div className="space-y-5 animate-fade-in">
              <FeedbackHealthSummary data={data.health} />
              <RecentCampaigns campaigns={data.campaigns} />
            </div>
          )}

          {/* Queue */}
          {activeTab === "queue" && (
            <div className="animate-fade-in">
              <ActionQueue items={data.actionQueue} />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
