"use client";

export interface RecommendationData {
  status: "gathering" | "ready";
  summary: string;
  strengths: string[];
  risks: string[];
}

interface RecommendationPanelProps {
  data: RecommendationData;
}

export default function RecommendationPanel({ data }: RecommendationPanelProps) {
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

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <h3 className="font-semibold text-slate-900 mb-2">Executive Summary</h3>
        <p className="text-sm text-slate-600 leading-relaxed">
          {data.summary}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Key Strengths
          </h4>
          <ul className="space-y-2">
            {data.strengths.map((item, i) => (
              <li key={i} className="text-sm text-slate-700 bg-green-50/50 border border-green-100 rounded-lg p-2.5">
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            Identified Risks
          </h4>
          <ul className="space-y-2">
            {data.risks.map((item, i) => (
              <li key={i} className="text-sm text-slate-700 bg-red-50/50 border border-red-100 rounded-lg p-2.5">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <button className="w-full mt-4 bg-slate-900 text-white font-medium py-2.5 rounded-lg hover:bg-slate-800 transition-colors shadow-sm text-sm flex justify-center items-center gap-2">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Export PDF Report
      </button>
    </div>
  );
}
