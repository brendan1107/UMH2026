"use client";

import { FinalInsight } from "../modals/EndSessionModal";

export interface RecommendationData {
  status: "gathering" | "ready" | "generating_verdict";
  summary: string;
  strengths: string[];
  risks: string[];
  verdict?: "Continue" | "Continue with caution" | "Pivot" | "Stop / Cancel";
  verdictReasoning?: string;
  nextSteps?: string[];
}

interface RecommendationPanelProps {
  data: RecommendationData;
  sessionStatus?: "active" | "insight_generated" | "archived";
  finalInsight?: FinalInsight | null;
  onGenerateVerdict?: () => void;
  onEndSessionClick?: () => void;
  onReopenSessionClick?: () => void;
  onExportPdf?: () => void;
  isExportingPdf?: boolean;
}

export default function RecommendationPanel({ 
  data, 
  sessionStatus = "active", 
  finalInsight, 
  onGenerateVerdict, 
  onEndSessionClick,
  onReopenSessionClick,
  onExportPdf,
  isExportingPdf = false
}: RecommendationPanelProps) {
  if (data.status === "gathering") {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4 text-slate-500">
        <svg className="w-8 h-8 animate-spin text-slate-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <div>
          <p className="font-medium text-slate-900">Analysis in progress</p>
          <p className="text-sm mt-1">Collecting evidence to build your recommendation.</p>
        </div>
      </div>
    );
  }

  if (data.status === "generating_verdict") {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4 text-slate-500">
        <svg className="w-8 h-8 animate-spin text-slate-900" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <div>
          <p className="font-medium text-slate-900">Synthesizing Final Verdict</p>
          <p className="text-sm mt-1">Reviewing all facts, constraints, and external data...</p>
        </div>
      </div>
    );
  }

  const getVerdictStyles = (verdict: string) => {
    switch (verdict) {
      case "Continue": return "bg-green-50 border-green-200 text-green-800";
      case "Continue with caution": return "bg-yellow-50 border-yellow-200 text-yellow-800";
      case "Pivot": return "bg-orange-50 border-orange-200 text-orange-800";
      case "Stop / Cancel": return "bg-red-50 border-red-200 text-red-800";
      default: return "bg-slate-50 border-slate-200 text-slate-800";
    }
  };
  const showExecutiveSummary = Boolean(data.summary && data.summary !== data.verdictReasoning);

  return (
    <div className="space-y-6">
      
      {sessionStatus === "archived" && (
        <div className="bg-slate-100 border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-slate-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
            <div>
              <h3 className="font-semibold text-slate-800  text-sm">Session Archived</h3>
              <p className="text-sm text-slate-600  mt-1">This investigation is closed. You can review the evidence and analysis below.</p>
            </div>
          </div>
          {onReopenSessionClick && (
            <button 
              onClick={onReopenSessionClick}
              className="mt-2 w-full bg-white  border border-slate-300  text-slate-700  font-medium py-2 rounded-lg hover:bg-slate-50  transition-colors shadow-sm text-sm"
            >
              Reopen Session
            </button>
          )}
        </div>
      )}

      {sessionStatus === "insight_generated" && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium text-green-800">Final insight checkpoint saved.</span>
        </div>
      )}

      {finalInsight && (
        <div className={`rounded-xl border p-5 shadow-sm ${
          finalInsight.verdict.includes("Stop") ? "bg-red-50 border-red-200 text-red-900" :
          finalInsight.verdict.includes("Pivot") ? "bg-orange-50 border-orange-200 text-orange-900" :
          finalInsight.verdict.includes("caution") ? "bg-yellow-50 border-yellow-200 text-yellow-900" :
          "bg-green-50 border-green-200 text-green-900"
        }`}>
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-xs font-bold uppercase tracking-wider opacity-80">Final Insight Checkpoint</h3>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-white/50 border border-black/10 uppercase tracking-wide">
              Risk: {finalInsight.riskLevel}
            </span>
          </div>
          <p className="text-xl font-bold mb-3">{finalInsight.verdict}</p>
          <p className="text-sm leading-relaxed opacity-90">{finalInsight.explanation}</p>
          {finalInsight.nextSteps && finalInsight.nextSteps.length > 0 && (
            <div className="mt-4 pt-4 border-t border-current/10">
              <h4 className="text-xs font-bold uppercase tracking-wider mb-2 opacity-80">Next Steps</h4>
              <ul className="space-y-1.5 list-disc pl-4 text-sm opacity-90">
                {finalInsight.nextSteps.map((step, i) => <li key={i}>{step}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {data.verdict && !finalInsight && (
        <div className={`rounded-xl border p-5 shadow-sm ${getVerdictStyles(data.verdict)}`}>
          <h3 className="text-xs font-bold uppercase tracking-wider mb-2 opacity-80">Final Verdict</h3>
          <p className="text-xl font-bold mb-3">{data.verdict}</p>
          <p className="text-sm leading-relaxed opacity-90">{data.verdictReasoning}</p>
          {data.nextSteps && data.nextSteps.length > 0 && (
            <div className="mt-4 pt-4 border-t border-current/10">
              <h4 className="text-xs font-bold uppercase tracking-wider mb-2 opacity-80">Next Steps</h4>
              <ul className="space-y-1.5 list-disc pl-4 text-sm opacity-90">
                {data.nextSteps.map((step, i) => <li key={i}>{step}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {showExecutiveSummary && (
        <div className="bg-white  rounded-xl border border-slate-200  p-4 shadow-sm">
          <h3 className="font-semibold text-slate-900  mb-2">Executive Summary</h3>
          <p className="text-sm text-slate-600  leading-relaxed">
            {data.summary}
          </p>
        </div>
      )}

      {((data.strengths || []).length > 0 || (data.risks || []).length > 0) && (
      <div className="space-y-4">
        {(data.strengths || []).length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Key Strengths
          </h4>
          <ul className="space-y-2">
            {(data.strengths || []).map((item, i) => (
              <li key={i} className="text-sm text-slate-700 bg-green-50/50 border border-green-100 rounded-lg p-2.5">
                {item}
              </li>
            ))}
          </ul>
        </div>
        )}

        {(data.risks || []).length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            Identified Risks
          </h4>
          <ul className="space-y-2">
            {(data.risks || []).map((item, i) => (
              <li key={i} className="text-sm text-slate-700 bg-red-50/50 border border-red-100 rounded-lg p-2.5">
                {item}
              </li>
            ))}
          </ul>
        </div>
        )}
      </div>
      )}

      <div className="mt-6 flex flex-col gap-3">
        {sessionStatus !== "archived" && (
          <div className="flex flex-col gap-2 p-4 bg-slate-50  border border-slate-200  rounded-xl mb-2">
            <p className="text-xs font-semibold text-slate-500  uppercase tracking-wider text-center">Investigation Actions</p>
            {onGenerateVerdict && (
              <button 
                onClick={onGenerateVerdict}
                className="w-full bg-slate-200  text-slate-800  font-medium py-2 rounded-lg hover:bg-slate-300  transition-colors shadow-sm text-sm"
              >
                {data.verdict ? "Regenerate Verdict" : "Generate Quick Verdict"}
              </button>
            )}
            {onEndSessionClick && (
              <button 
                onClick={onEndSessionClick}
                className="w-full bg-slate-900  text-white  font-medium py-2 rounded-lg hover:bg-slate-800  transition-colors shadow-sm text-sm"
              >
                End Session
              </button>
            )}
          </div>
        )}
        
        <button
          onClick={onExportPdf}
          disabled={!data.verdict || isExportingPdf}
          title={!data.verdict ? "Generate verdict before exporting." : undefined}
          className="w-full bg-white  border border-slate-300  text-slate-700  font-medium py-2.5 rounded-lg hover:bg-slate-50  transition-colors shadow-sm text-sm flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          {isExportingPdf ? "Exporting PDF..." : "Export PDF Report"}
        </button>
      </div>
    </div>
  );
}
