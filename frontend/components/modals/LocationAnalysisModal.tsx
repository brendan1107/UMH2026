"use client";

import { motion, AnimatePresence } from "framer-motion";
import { LocationAnalysisResult } from "../../lib/api/types";
import CompetitorMap from "../maps/CompetitorMap";

interface LocationAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: LocationAnalysisResult | null;
  isLoading: boolean;
}

export default function LocationAnalysisModal({ 
  isOpen, 
  onClose, 
  result, 
  isLoading 
}: LocationAnalysisModalProps) {
  
  const getRiskStyles = (level: string) => {
    switch (level) {
      case "High": return "text-red-700 bg-red-100 border-red-200 ring-red-500/10";
      case "Medium": return "text-amber-700 bg-amber-100 border-amber-200 ring-amber-500/10";
      case "Low": return "text-emerald-700 bg-emerald-100 border-emerald-200 ring-emerald-500/10";
      default: return "text-slate-700 bg-slate-100 border-slate-200 ring-slate-500/10";
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[100]"
          />

          {/* Modal Container */}
          <div className="fixed inset-0 z-[101] overflow-y-auto pointer-events-none">
            <div className="flex min-h-full items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl overflow-hidden pointer-events-auto flex flex-col"
              >
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center shadow-lg shadow-slate-900/10">
                      <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A2 2 0 013 15.382V6.418a2 2 0 011.106-1.789L9 2m6 18l5.447-2.724A2 2 0 0021 15.382V6.418a2 2 0 00-1.106-1.789L15 2m-6 18V2m6 18V2" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-base font-black text-slate-900">
                        Location Intelligence Report
                      </h3>
                      <p className="text-[11px] text-slate-500 font-bold uppercase tracking-widest">
                        Market Analysis & Competitor Mapping
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Content Area */}
                <div className="px-6 py-6 overflow-y-auto custom-scrollbar max-h-[75vh]">
                  {isLoading ? (
                    <div className="py-24 flex flex-col items-center justify-center space-y-6">
                      <div className="relative">
                        <div className="w-16 h-16 border-4 border-slate-100 rounded-full"></div>
                        <div className="w-16 h-16 border-4 border-transparent border-t-slate-900 rounded-full animate-spin absolute top-0 left-0"></div>
                      </div>
                      <div className="text-center">
                        <p className="text-base font-black text-slate-900">Scanning Local Market...</p>
                        <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-2">Retrieving geodata & calculating risk scores</p>
                      </div>
                    </div>
                  ) : result ? (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                      
                      {/* Left Side: Summary & Map */}
                      <div className="lg:col-span-7 space-y-8">
                        <div className="space-y-6">
                          <div className="flex flex-wrap items-center gap-4">
                            <div className={`px-4 py-1.5 rounded-xl text-[11px] font-black border uppercase tracking-widest flex items-center gap-2 shadow-sm ring-1 ${getRiskStyles(result.riskLevel)}`}>
                              <div className={`w-2 h-2 rounded-full animate-pulse ${result.riskLevel === 'High' ? 'bg-red-500' : result.riskLevel === 'Medium' ? 'bg-amber-500' : 'bg-emerald-500'}`}></div>
                              {result.riskLevel} Market Risk · {result.riskScore}/10
                            </div>
                            <div className="flex items-center gap-3">
                              <span className={`text-[9px] font-black uppercase tracking-tighter px-2.5 py-1 rounded-lg border ${result.source === 'google_places' ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-amber-700 bg-amber-50 border-amber-200'}`}>
                                {result.source === 'google_places' ? 'Powered by Google Places' : 'Demo data fallback'}
                              </span>
                              {result.analysisMode === 'gemini' && (
                                <span className="text-[9px] font-black uppercase tracking-tighter px-2.5 py-1 rounded-lg border text-indigo-700 bg-indigo-50 border-indigo-200 flex items-center gap-1">
                                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                  AI Analysis: Gemini
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Market Verdict Section */}
                          <div className="p-8 rounded-[2.5rem] bg-slate-50/80 border border-slate-100 space-y-6 shadow-sm ring-1 ring-slate-900/5">
                            <div className="flex items-center justify-between">
                              <div className="space-y-1">
                                <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Market Analysis Verdict</h4>
                                <div className="flex items-center gap-3">
                                  <span className={`text-xl font-black ${result.riskLevel === 'High' ? 'text-red-600' : result.riskLevel === 'Medium' ? 'text-amber-600' : 'text-emerald-600'}`}>
                                    Risk: {result.riskLevel}
                                  </span>
                                  <span className="w-1.5 h-1.5 rounded-full bg-slate-300"></span>
                                  <span className="text-xl font-bold text-slate-900">Score: {result.riskScore} / 10</span>
                                </div>
                              </div>
                              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-inner ${
                                result.riskLevel === 'High' ? 'bg-red-50 text-red-500' : 
                                result.riskLevel === 'Medium' ? 'bg-amber-50 text-amber-500' : 
                                'bg-emerald-50 text-emerald-500'
                              }`}>
                                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04" />
                                </svg>
                              </div>
                            </div>

                            <div className="p-6 bg-white rounded-3xl border border-slate-100 shadow-sm ring-1 ring-slate-900/5">
                              <p className="text-sm text-slate-700 leading-relaxed font-medium">
                                {result.riskExplanation}
                              </p>
                              
                              <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-slate-50 mt-4">
                                {result.targetLocation.googleMapsUrl && (
                                  <a 
                                    href={result.targetLocation.googleMapsUrl} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1.5 text-[10px] font-bold text-slate-600 hover:text-slate-900 uppercase tracking-widest transition-all"
                                  >
                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                                    View in Google Maps
                                  </a>
                                )}
                                <span className="text-[10px] text-slate-400 font-bold uppercase truncate max-w-[200px]">
                                  {result.targetLocation.name}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-4">
                          <div className="flex items-center gap-2">
                            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Market Map Preview</h4>
                            <div className="h-px flex-1 bg-slate-100"></div>
                          </div>
                          <div className="border-4 border-white rounded-[2rem] overflow-hidden shadow-2xl shadow-slate-200/50 bg-white ring-1 ring-slate-200">
                            <CompetitorMap target={result.targetLocation} competitors={result.competitors} />
                          </div>
                        </div>
                      </div>

                      {/* Right Side: Venue List & Follow-ups */}
                      <div className="lg:col-span-5 space-y-8">
                        
                        <div className="space-y-4">
                          <div className="flex flex-col border-b border-slate-100 pb-4">
                            <div className="flex items-center justify-between">
                              <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Neighborhood Intel</h4>
                              <span className="text-[10px] text-slate-400 font-bold italic">Radius: {result.radius}m</span>
                            </div>
                            <div className="flex items-center justify-between mt-2">
                              <div className="flex items-center gap-2">
                                <span className="text-base font-black text-slate-900">{result.competitors.length}</span>
                                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">Relevant Venues Found</span>
                              </div>
                              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-emerald-50 border border-emerald-100">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                                <span className="text-[9px] font-bold text-emerald-700 uppercase">Live Data</span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar min-h-0 max-h-[600px]">
                            {result.competitors.length === 0 ? (
                              <div className="py-20 px-6 border-2 border-dashed border-slate-100 rounded-[2.5rem] text-center bg-slate-50/30">
                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">No Competitors Detected</p>
                              </div>
                            ) : (
                              result.competitors.map((comp) => (
                                <div key={comp.id} className="p-5 border border-slate-100 rounded-3xl bg-white shadow-sm hover:shadow-lg transition-all group relative border-l-4 border-l-slate-200 hover:border-l-indigo-500 ring-1 ring-slate-900/5">
                                  <div className="flex justify-between items-start mb-2 gap-3">
                                    <div className="flex-1 min-w-0">
                                      <h5 className="text-sm font-bold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
                                        {comp.name}
                                      </h5>
                                      <p className="text-[10px] text-slate-500 font-medium mt-0.5">{comp.category} · {comp.distanceMeters}m away</p>
                                    </div>
                                    <div className="flex flex-col items-end shrink-0">
                                      <div className="flex items-center gap-1 text-slate-900 font-bold">
                                        <span className="text-xs">{comp.rating}</span>
                                        <svg className="w-3 h-3 text-amber-400 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
                                      </div>
                                      <span className="text-[9px] text-slate-400 font-medium">{comp.reviewCount} reviews</span>
                                    </div>
                                  </div>
                                  
                                  <div className="flex items-center gap-2 mb-3">
                                    <div className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                                      comp.riskLevel === 'High' ? 'bg-red-50 text-red-600 border-red-100' : 
                                      comp.riskLevel === 'Medium' ? 'bg-amber-50 text-amber-600 border-amber-100' : 
                                      'bg-emerald-50 text-emerald-600 border-emerald-100'
                                    }`}>
                                      {comp.riskLevel} Risk · {comp.riskScore}/10
                                    </div>
                                  </div>

                                  <div className="pt-3 border-t border-slate-50 flex items-center justify-between">
                                    <p className="text-[10px] text-slate-500 italic line-clamp-1 flex-1 pr-4">"{comp.insight}"</p>
                                    {comp.googleMapsUrl && (
                                      <a href={comp.googleMapsUrl} target="_blank" rel="noopener noreferrer" className="text-[9px] font-bold text-indigo-600 hover:text-indigo-800 uppercase tracking-widest transition-colors flex items-center gap-1 shrink-0">
                                        View Maps
                                        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                                      </a>
                                    )}
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </div>

                        {/* Strategic Considerations - Interactive */}
                        <div className="space-y-4">
                          <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest px-2">Strategic Considerations</h4>
                          <div className="grid gap-3">
                            {result.followUpQuestions.map((q, i) => (
                              <details key={i} className="group bg-white border border-slate-100 rounded-3xl hover:border-slate-200 transition-all shadow-sm ring-1 ring-slate-900/5">
                                <summary className="flex items-center justify-between p-5 cursor-pointer list-none">
                                  <p className="text-sm font-bold text-slate-900 pr-4">{q}</p>
                                  <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest group-open:rotate-180 transition-transform">
                                    Answer
                                  </span>
                                </summary>
                                <div className="px-5 pb-5 pt-0">
                                  <textarea 
                                    className="w-full p-4 text-xs border border-slate-100 rounded-2xl bg-slate-50 focus:outline-none focus:ring-1 focus:ring-slate-200 min-h-[80px]"
                                    placeholder="Add your notes or strategic response here..."
                                  />
                                  <div className="flex justify-end mt-2">
                                    <button className="text-[9px] font-black text-slate-400 uppercase tracking-widest hover:text-slate-900">Save Response</button>
                                  </div>
                                </div>
                              </details>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
                
                {/* Footer: Suggested Tasks */}
                {result && !isLoading && (
                  <div className="px-6 py-6 border-t border-slate-100 bg-white shrink-0">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center shrink-0 shadow-lg shadow-slate-200">
                        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>
                      </div>
                      <h4 className="text-[11px] font-black text-slate-900 uppercase tracking-widest leading-none">Automated Action Items</h4>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      {result.suggestedTasks.map((task, i) => (
                        <div key={i} className="p-4 border border-slate-100 rounded-2xl bg-slate-50/30 hover:bg-white hover:shadow-lg hover:border-slate-200 transition-all group ring-1 ring-slate-900/5">
                          <h5 className="text-[11px] font-black text-slate-900 mb-1.5 leading-tight group-hover:text-slate-950 transition-colors">{task.title}</h5>
                          <p className="text-[10px] text-slate-500 font-bold leading-normal">{task.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            </div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
