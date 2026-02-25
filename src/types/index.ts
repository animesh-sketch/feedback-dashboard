// ─── Enums ────────────────────────────────────────────────────────────────────

export type SurveyType = "CSAT" | "NPS" | "Yes-No" | "Open";

export type CampaignStatus = "Healthy" | "Needs Action" | "Critical" | "Draft";

export type FeedbackTag =
  | "delay"
  | "pricing"
  | "agent behavior"
  | "product quality"
  | "billing issue"
  | "feature request"
  | "onboarding"
  | "response time"
  | "refund"
  | "communication";

export type ActionPriority = "critical" | "high" | "medium" | "low";

export type TrendDirection = "up" | "down" | "neutral";

// ─── KPI / Health ─────────────────────────────────────────────────────────────

export interface KPIMetric {
  id: string;
  label: string;
  value: number;
  unit: "percent" | "score" | "count" | "nps";
  /** Previous period value for comparison */
  previousValue: number;
  trend: TrendDirection;
  /** Positive means "higher is better"; negative means "lower is better" */
  higherIsBetter: boolean;
  description: string;
}

export interface FeedbackHealthSummary {
  responseRate: KPIMetric;
  averageCSAT: KPIMetric;
  averageNPS: KPIMetric;
  negativeFeedbackPercent: KPIMetric;
  unresolvedCount: KPIMetric;
  periodLabel: string; // e.g. "Last 30 days"
}

// ─── Campaigns ────────────────────────────────────────────────────────────────

export interface Campaign {
  id: string;
  name: string;
  surveyType: SurveyType;
  responsesReceived: number;
  totalSent: number;
  averageScore: number | null; // null for Yes-No
  yesPercent?: number; // only for Yes-No surveys
  status: CampaignStatus;
  sentAt: string; // ISO timestamp
  /** Segment/audience label */
  audience: string;
}

// ─── Action Queue ─────────────────────────────────────────────────────────────

export interface ActionItem {
  id: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  /** Score they gave (0-10 NPS, 1-5 CSAT, true/false Yes-No) */
  score: number;
  surveyType: SurveyType;
  campaignName: string;
  tags: FeedbackTag[];
  comment: string;
  receivedAt: string; // ISO timestamp
  priority: ActionPriority;
  /** Whether this item has breached the SLA response window */
  slaBreached: boolean;
  /** Hours since feedback was received */
  hoursOpen: number;
  /** SLA threshold in hours */
  slaHours: number;
  resolved: boolean;
}

// ─── Smart Actions ────────────────────────────────────────────────────────────

export type SmartActionId =
  | "create_survey"
  | "send_recovery"
  | "analyze_campaign"
  | "export_negative";

export interface SmartAction {
  id: SmartActionId;
  label: string;
  description: string;
  icon: string;
  variant: "primary" | "ghost" | "danger" | "success" | "warning";
  badge?: string; // optional count badge (e.g. "12 ready")
}

// ─── Dashboard Aggregate ──────────────────────────────────────────────────────

export interface DashboardData {
  health: FeedbackHealthSummary;
  campaigns: Campaign[];
  actionQueue: ActionItem[];
  smartActions: SmartAction[];
  lastUpdated: string; // ISO timestamp
}

// ─── API Shapes ───────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
  meta?: {
    total: number;
    page: number;
    pageSize: number;
  };
}

// GET /api/dashboard
export type GetDashboardResponse = ApiResponse<DashboardData>;

// GET /api/campaigns?page=&limit=&status=
export type GetCampaignsResponse = ApiResponse<Campaign[]>;

// GET /api/action-queue?priority=&slaBreached=
export type GetActionQueueResponse = ApiResponse<ActionItem[]>;

// POST /api/actions/:id/resolve
export interface ResolveActionPayload {
  note?: string;
  resolvedBy: string;
}

// POST /api/campaigns
export interface CreateCampaignPayload {
  name: string;
  surveyType: SurveyType;
  audience: string;
  scheduledAt?: string;
}

// POST /api/recovery-emails
export interface SendRecoveryEmailPayload {
  actionItemIds: string[];
  templateId?: string;
  customMessage?: string;
}
