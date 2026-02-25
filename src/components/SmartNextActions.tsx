import {
  Plus,
  Mail,
  BarChart2,
  Download,
  ArrowRight,
} from "lucide-react";
import type { SmartAction } from "../types";

const iconMap: Record<string, React.ReactNode> = {
  Plus: <Plus size={18} />,
  Mail: <Mail size={18} />,
  BarChart2: <BarChart2 size={18} />,
  Download: <Download size={18} />,
};

const variantStyles: Record<SmartAction["variant"], string> = {
  primary:
    "bg-violet-600 hover:bg-violet-500 text-white border border-violet-500/30 shadow-lg shadow-violet-900/30",
  ghost:
    "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60",
  danger:
    "bg-rose-900/30 hover:bg-rose-900/50 text-rose-300 border border-rose-800/40",
  success:
    "bg-emerald-900/30 hover:bg-emerald-900/50 text-emerald-300 border border-emerald-800/40",
  warning:
    "bg-amber-900/30 hover:bg-amber-900/50 text-amber-300 border border-amber-800/40",
};

interface SmartNextActionsProps {
  actions: SmartAction[];
}

export function SmartNextActions({ actions }: SmartNextActionsProps) {
  return (
    <section className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-100">
            Smart Next Actions
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Recommended based on your current feedback state
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {actions.map((action) => (
          <button
            key={action.id}
            className={`group flex flex-col gap-3 p-4 rounded-xl text-left transition-all duration-200 ${variantStyles[action.variant]}`}
          >
            <div className="flex items-start justify-between w-full">
              <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
                {iconMap[action.icon] ?? <Plus size={18} />}
              </div>
              {action.badge && (
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-black/20">
                  {action.badge}
                </span>
              )}
            </div>

            <div>
              <div className="font-semibold text-sm leading-tight">
                {action.label}
              </div>
              <div className="text-xs opacity-60 mt-1 leading-relaxed">
                {action.description}
              </div>
            </div>

            <div className="flex items-center gap-1 text-xs opacity-0 group-hover:opacity-70 transition-opacity mt-auto">
              Get started <ArrowRight size={11} />
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
