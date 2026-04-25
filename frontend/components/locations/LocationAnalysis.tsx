"use client";

import { useState } from "react";
import { locationsService } from "../../lib/api/locations";
import { LocationAnalysisResult } from "../../lib/api/types";
import LocationAnalysisModal from "../modals/LocationAnalysisModal";

interface LocationAnalysisProps {
  caseId: string;
  onAnalysisComplete?: (result: LocationAnalysisResult) => void;
}

export default function LocationAnalysis({ caseId, onAnalysisComplete }: LocationAnalysisProps) {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [result, setResult] = useState<LocationAnalysisResult | null>(null);
  const [preview, setPreview] = useState<LocationAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handlePreview = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    setPreview(null);
    
    try {
      const data = await locationsService.getCompetitors({
        caseId,
        targetLocation: query,
        previewOnly: true
      });
      setPreview(data);
    } catch (err) {
      console.error("Preview failed:", err);
      setError("Could not find location. Try a more specific address.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview) return;

    setIsLoading(true);
    setError(null);
    setIsModalOpen(true);
    
    try {
      const data = await locationsService.getCompetitors({
        caseId,
        targetLocation: preview.targetLocation.name,
        lat: preview.targetLocation.lat,
        lng: preview.targetLocation.lng
      });
      setResult(data);
      setPreview(null);
      if (onAnalysisComplete) onAnalysisComplete(data);
    } catch (err) {
      console.error("Analysis failed:", err);
      setError("Failed to analyze location. Please try again.");
      setIsModalOpen(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/30 flex items-center gap-2">
        <div className="w-6 h-6 rounded-lg bg-slate-900 flex items-center justify-center shrink-0">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          </svg>
        </div>
        <h3 className="text-xs font-black text-slate-900 uppercase tracking-widest">Market Analysis</h3>
      </div>

      <div className="p-4 space-y-4">
        {!preview ? (
          <div className="space-y-3">
            <div className="relative group">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter target location..."
                className="w-full pl-8 pr-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900/5 focus:border-slate-900 transition-all placeholder:text-slate-400 group-hover:border-slate-300"
                onKeyDown={(e) => e.key === "Enter" && handlePreview()}
              />
              <svg className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <button
              onClick={handlePreview}
              disabled={isLoading || !query.trim()}
              className="w-full py-2 bg-slate-900 text-white text-[11px] font-black uppercase tracking-widest rounded-lg hover:bg-slate-800 disabled:opacity-40 transition-all flex items-center justify-center gap-2"
            >
              {isLoading ? "Searching..." : "Start Analysis"}
            </button>
          </div>
        ) : (
          <div className="space-y-3 p-3 bg-slate-50 rounded-xl border border-slate-100 animate-in fade-in slide-in-from-top-2">
            <div className="flex items-start gap-2">
              <div className="w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center shrink-0 mt-0.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
              </div>
              <div className="space-y-0.5 overflow-hidden">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-tighter">Location Found</p>
                <p className="text-xs font-bold text-slate-900 truncate">{preview.targetLocation.name}</p>
                <p className="text-[10px] text-slate-500 line-clamp-2 leading-tight">{preview.targetLocation.address}</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={() => setPreview(null)}
                className="py-1.5 text-[10px] font-black text-slate-500 uppercase tracking-widest rounded-lg border border-slate-200 hover:bg-white transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={isLoading}
                className="py-1.5 bg-emerald-600 text-white text-[10px] font-black uppercase tracking-widest rounded-lg hover:bg-emerald-700 shadow-sm transition-all"
              >
                Confirm
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="p-2 text-[10px] text-red-600 bg-red-50 border border-red-100 rounded-lg flex items-center gap-1.5 font-bold">
            <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}
      </div>

      <LocationAnalysisModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        result={result}
        isLoading={isLoading}
      />
    </div>
  );
}
