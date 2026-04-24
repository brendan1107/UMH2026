import { useState, useEffect } from "react";

export interface FinalInsight {
  verdict: "Continue" | "Continue with caution" | "Pivot" | "Stop / Do Not Continue";
  riskLevel: "Low" | "Medium" | "High";
  confidence: "Low" | "Moderate" | "High";
  explanation: string;
  reasons: string[];
  nextSteps: string[];
}

interface EndSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionType: "new" | "existing";
  onSaveDecision: (decision: "continue" | "archive", insight: FinalInsight) => void;
}

export default function EndSessionModal({ isOpen, onClose, sessionType, onSaveDecision }: EndSessionModalProps) {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [insight, setInsight] = useState<FinalInsight | null>(null);
  const [selectedDecision, setSelectedDecision] = useState<"continue" | "archive" | null>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setAnalysisProgress(0);
      setInsight(null);
      setSelectedDecision(null);
    }
  }, [isOpen]);

  const handleAnalyzeClick = () => {
    setStep(2);
    // Simulate analysis steps
    let progress = 0;
    const interval = setInterval(() => {
      progress += 25;
      setAnalysisProgress(progress);
      if (progress >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          generateMockInsight();
          setStep(3);
        }, 500);
      }
    }, 800);
  };

  const generateMockInsight = () => {
    if (sessionType === "existing") {
      setInsight({
        verdict: "Stop / Do Not Continue",
        riskLevel: "High",
        confidence: "High",
        explanation: "Based on the continuing margin compression, rising COGS, and declining foot traffic, the current business model is no longer financially viable. Continuing operations risks significant further debt accumulation.",
        reasons: [
          "Labor costs exceed 35% of revenue consistently.",
          "Ingredient costs have risen 18% with no ability to raise menu prices without losing volume.",
          "Weekday foot traffic is down 40% year-over-year."
        ],
        nextSteps: [
          "Consult with a financial advisor to manage outstanding liabilities immediately.",
          "Review lease exit clauses to understand termination costs.",
          "Begin liquidating inventory and equipment."
        ]
      });
    } else {
      setInsight({
        verdict: "Continue with caution",
        riskLevel: "Medium",
        confidence: "Moderate",
        explanation: "The grab-and-go cafe concept in the target area has merit due to high demographic density. However, the intense local competition and premium lease rates pose a significant risk to early cash flow and require tight operational execution.",
        reasons: [
          "High density of target demographic (office workers) within a 3-block radius.",
          "Proposed menu matches speed-of-service requirements.",
          "High local competition (4 existing coffee shops within 2 blocks).",
          "Premium lease rate leaves little room for lower-than-expected initial sales."
        ],
        nextSteps: [
          "Secure a lease agreement with favorable early termination clauses.",
          "Execute a soft launch to test menu pricing and operational speed.",
          "Aggressively market to local office buildings prior to opening."
        ]
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50 shrink-0">
          <h2 className="text-lg font-semibold text-slate-900">
            {step === 1 && "End Investigation Session?"}
            {step === 2 && "Analyzing Session Data..."}
            {step === 3 && "Final Insight Results"}
            {step === 4 && "Session Decision"}
          </h2>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
            disabled={step === 2}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto grow">
          
          {/* STEP 1: Confirmation */}
          {step === 1 && (
            <div className="space-y-6">
              <p className="text-slate-600">
                You are about to conclude this active investigation. F&B Genie will synthesize all gathered information to provide a definitive recommendation.
              </p>
              
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-slate-900 mb-3">Included in Analysis:</h3>
                <ul className="space-y-3">
                  {["Conversation history and context", "Completed investigation tasks", "Selected recommendations", "Uploaded evidence (files/images)", "Current business stage factors"].map((item, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-700">
                      <svg className="w-5 h-5 text-green-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* STEP 2: Loading */}
          {step === 2 && (
            <div className="py-12 flex flex-col items-center justify-center space-y-8">
              <div className="relative w-20 h-20">
                <svg className="w-full h-full text-slate-200" viewBox="0 0 100 100">
                  <circle className="stroke-current" strokeWidth="8" cx="50" cy="50" r="40" fill="transparent" />
                </svg>
                <svg className="w-full h-full text-slate-900 absolute top-0 left-0 transition-all duration-300" viewBox="0 0 100 100" style={{ strokeDasharray: 251.2, strokeDashoffset: 251.2 - (251.2 * analysisProgress) / 100 }}>
                  <circle className="stroke-current" strokeWidth="8" strokeLinecap="round" cx="50" cy="50" r="40" fill="transparent" transform="rotate(-90 50 50)" />
                </svg>
              </div>

              <div className="w-full max-w-sm space-y-4">
                {[
                  { threshold: 25, label: "Reviewing conversation context..." },
                  { threshold: 50, label: "Checking completed investigation tasks..." },
                  { threshold: 75, label: "Evaluating business risks..." },
                  { threshold: 100, label: "Preparing final recommendation..." }
                ].map((item, i) => (
                  <div key={i} className={`flex items-center gap-3 transition-opacity duration-500 ${analysisProgress >= item.threshold ? 'opacity-100' : 'opacity-40'}`}>
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${analysisProgress >= item.threshold ? 'bg-green-100 text-green-600' : 'bg-slate-100 text-slate-400'}`}>
                      {analysisProgress >= item.threshold ? (
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <div className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      )}
                    </div>
                    <span className="text-sm font-medium text-slate-700">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 3: Final Insight Result */}
          {step === 3 && insight && (
            <div className="space-y-6">
              {/* Verdict Header */}
              <div className={`p-5 rounded-xl border ${
                insight.verdict.includes("Stop") ? "bg-red-50 border-red-200" :
                insight.verdict.includes("Pivot") ? "bg-orange-50 border-orange-200" :
                insight.verdict.includes("caution") ? "bg-yellow-50 border-yellow-200" :
                "bg-green-50 border-green-200"
              }`}>
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider opacity-70">Final Verdict</h3>
                  <div className="flex gap-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-white/60 border border-black/10 uppercase tracking-wide">
                      Risk: {insight.riskLevel}
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-white/60 border border-black/10 uppercase tracking-wide">
                      Confidence: {insight.confidence}
                    </span>
                  </div>
                </div>
                <p className="text-2xl font-bold mb-2">{insight.verdict}</p>
                <p className="text-sm leading-relaxed opacity-90">{insight.explanation}</p>
              </div>

              {/* Key Reasons */}
              <div>
                <h4 className="text-sm font-semibold text-slate-900 mb-3">Key Reasons</h4>
                <ul className="space-y-2">
                  {insight.reasons.map((reason, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-slate-400 mt-0.5">-</span>
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Next Steps */}
              <div>
                <h4 className="text-sm font-semibold text-slate-900 mb-3">Recommended Next Steps</h4>
                <div className="bg-slate-50 border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
                  {insight.nextSteps.map((step, i) => (
                    <div key={i} className="p-3.5 text-sm text-slate-700 flex gap-3">
                      <span className="font-semibold text-slate-400 shrink-0">{i + 1}.</span>
                      {step}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: Decision */}
          {step === 4 && (
            <div className="space-y-6">
              <div className="text-center mb-2">
                <p className="text-slate-600 text-lg">What would you like to do with this session?</p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                {/* Option A */}
                <button
                  onClick={() => setSelectedDecision("continue")}
                  className={`text-left p-5 rounded-xl border-2 transition-all ${
                    selectedDecision === "continue" 
                      ? "border-slate-900 bg-slate-50 shadow-sm" 
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                      selectedDecision === "continue" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300"
                    }`}>
                      {selectedDecision === "continue" && (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <circle cx="10" cy="10" r="5" />
                        </svg>
                      )}
                    </div>
                    <span className="font-semibold text-slate-900">Continue Business</span>
                  </div>
                  <p className="text-sm text-slate-500 pl-8">
                    Save this analysis as a checkpoint and continue working on this investigation.
                  </p>
                </button>

                {/* Option B */}
                <button
                  onClick={() => setSelectedDecision("archive")}
                  className={`text-left p-5 rounded-xl border-2 transition-all ${
                    selectedDecision === "archive" 
                      ? "border-slate-900 bg-slate-50 shadow-sm" 
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                      selectedDecision === "archive" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300"
                    }`}>
                      {selectedDecision === "archive" && (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <circle cx="10" cy="10" r="5" />
                        </svg>
                      )}
                    </div>
                    <span className="font-semibold text-slate-900">Archive for Later</span>
                  </div>
                  <p className="text-sm text-slate-500 pl-8">
                    Save this investigation and close it for now. You can reopen it later.
                  </p>
                </button>
              </div>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3 shrink-0">
          {step === 1 && (
            <>
              <button 
                onClick={onClose}
                className="px-5 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={handleAnalyzeClick}
                className="px-5 py-2.5 text-sm font-medium bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors shadow-sm"
              >
                Analyze Session
              </button>
            </>
          )}

          {step === 3 && (
            <button 
              onClick={() => setStep(4)}
              className="px-5 py-2.5 text-sm font-medium bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors shadow-sm"
            >
              Continue to Decision
            </button>
          )}

          {step === 4 && (
            <>
              <button 
                onClick={() => setStep(3)}
                className="px-5 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
              >
                Back
              </button>
              <button 
                onClick={() => selectedDecision && insight && onSaveDecision(selectedDecision, insight)}
                disabled={!selectedDecision}
                className={`px-5 py-2.5 text-sm font-medium rounded-lg transition-colors shadow-sm ${
                  selectedDecision 
                    ? "bg-slate-900 text-white hover:bg-slate-800" 
                    : "bg-slate-200 text-slate-400 cursor-not-allowed"
                }`}
              >
                Save Decision
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  );
}