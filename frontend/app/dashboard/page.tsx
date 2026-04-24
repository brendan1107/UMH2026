"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import NewSessionModal from "../../components/modals/NewSessionModal";
import SettingsModal from "../../components/modals/SettingsModal";
import { auth } from "../../lib/firebase";
import { BusinessCase } from "../../lib/api/types";

// Mock cases for dashboard
const MOCK_CASES: BusinessCase[] = [
  {
    id: "case-1",
    title: "Downtown Cafe Expansion",
    description: "Analyzing the viability of a second location in the financial district.",
    stage: "existing",
    status: "active",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: "case-2",
    title: "Li Villas Western Eatery",
    description: "Menu restructuring and cost analysis for dinner service.",
    stage: "existing",
    status: "insight_generated",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString()
  },
  {
    id: "case-3",
    title: "Struggling Dessert Kiosk",
    description: "Evaluating whether to continue or pivot concept.",
    stage: "existing",
    status: "archived",
    createdAt: new Date(Date.now() - 172800000).toISOString(),
    updatedAt: new Date(Date.now() - 172800000).toISOString()
  }
];

export default function DashboardPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [cases, setCases] = useState<BusinessCase[]>(MOCK_CASES);
  
  const currentUser = auth.currentUser;

  // Management states
  const [editingCaseId, setEditingCaseId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [deletingCaseId, setDeletingCaseId] = useState<string | null>(null);

  const handleRenameSubmit = (caseId: string) => {
    if (!editTitle.trim()) return;
    // TODO: Connect to backend - casesService.updateCaseTitle(caseId, editTitle)
    setCases(prev => prev.map(c => c.id === caseId ? { ...c, title: editTitle.trim() } : c));
    setEditingCaseId(null);
  };

  const handleDeleteConfirm = () => {
    if (!deletingCaseId) return;
    // TODO: Connect to backend - casesService.deleteCase(deletingCaseId)
    setCases(prev => prev.filter(c => c.id !== deletingCaseId));
    setDeletingCaseId(null);
  };

  const handleReopen = (caseId: string) => {
    // TODO: Connect to backend - casesService.reopenCase(caseId)
    setCases(prev => prev.map(c => c.id === caseId ? { ...c, status: "active" } : c));
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB]  text-slate-900  pb-20 transition-colors duration-200">
      {/* Navigation Bar */}
      <nav className="border-b border-slate-200  bg-white ">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <span className="font-semibold text-lg text-slate-900 tracking-tight">F&B Genie</span>
              </div>
            </div>
              <button 
                onClick={() => setIsSettingsOpen(true)}
                className="w-9 h-9 rounded-full hover:bg-slate-100  flex items-center justify-center transition-colors border border-transparent hover:border-slate-200 "
                title="Settings"
              >
                <svg className="w-5 h-5 text-slate-500 " fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
            </div>
          </div>
        </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900  tracking-tight mb-2">
              Dashboard
            </h1>
            <p className="text-base text-slate-500  max-w-2xl">
              Welcome back. Start a new investigation or resume an existing F&B case.
            </p>
          </div>
          
          <button 
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center justify-center px-6 py-2.5 text-sm font-medium text-white transition-colors bg-slate-900 rounded-lg hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900"
          >
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Start New Session
          </button>
        </div>

        {cases.length === 0 ? (
          <div className="bg-white  border border-slate-200  rounded-xl p-12 sm:p-16 text-center flex flex-col items-center justify-center min-h-[300px]">
            <div className="w-16 h-16 bg-slate-50  rounded-full flex items-center justify-center mb-4 border border-slate-100 ">
              <svg className="w-8 h-8 text-slate-400 " fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            
            <h3 className="text-lg font-semibold text-slate-900  mb-2">No active investigations</h3>
            <p className="text-slate-500  max-w-sm mx-auto mb-6 text-sm">
              You haven't started any F&B cases yet. Click the button below to initialize your first business analysis.
            </p>
            
            <button 
              onClick={() => setIsModalOpen(true)}
              className="text-slate-900  font-medium hover:text-slate-700  transition-colors flex items-center gap-2 bg-slate-50  hover:bg-slate-100  px-5 py-2 rounded-lg border border-slate-200  text-sm"
            >
              Initialize First Case
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cases.map((c) => (
              <div key={c.id} className="bg-white  border border-slate-200  rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col group relative overflow-hidden">
                <div className="flex justify-between items-start mb-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wide ${
                    c.status === "archived" ? "bg-slate-100 text-slate-600  " :
                    c.status === "insight_generated" ? "bg-green-50 text-green-700 border border-green-200   " :
                    "bg-blue-50 text-blue-700 border border-blue-200   "
                  }`}>
                    {c.status === "insight_generated" ? "Insight Saved" : c.status}
                  </span>
                  
                  {/* Actions Dropdown / Icons */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => { setEditingCaseId(c.id); setEditTitle(c.title); }} className="p-1 text-slate-400 hover:text-blue-600 transition-colors" title="Rename">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                    </button>
                    <button onClick={() => setDeletingCaseId(c.id)} className="p-1 text-slate-400 hover:text-red-600 transition-colors" title="Delete">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                </div>

                {editingCaseId === c.id ? (
                  <div className="mb-2">
                    <input 
                      type="text" 
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") handleRenameSubmit(c.id); if (e.key === "Escape") setEditingCaseId(null); }}
                      className="w-full text-lg font-semibold bg-white  border border-slate-300  rounded px-2 py-1 text-slate-900  focus:outline-none focus:ring-2 focus:ring-slate-900 "
                      autoFocus
                    />
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => handleRenameSubmit(c.id)} className="text-xs bg-slate-900 text-white px-2 py-1 rounded">Save</button>
                      <button onClick={() => setEditingCaseId(null)} className="text-xs text-slate-500 hover:text-slate-700  px-2 py-1">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <h3 className="text-lg font-semibold text-slate-900  mb-2 truncate" title={c.title}>{c.title}</h3>
                )}
                
                <p className="text-sm text-slate-500  mb-4 line-clamp-2 grow">{c.description}</p>
                
                <div className="mt-auto flex items-center justify-between pt-4 border-t border-slate-100 ">
                  <div className="text-xs text-slate-400 ">
                    Updated {new Date(c.updatedAt).toLocaleDateString()}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {c.status === "archived" && (
                      <button 
                        onClick={() => handleReopen(c.id)}
                        className="text-xs font-medium text-slate-600  hover:text-slate-900  border border-slate-200  px-3 py-1.5 rounded-lg hover:bg-slate-50  transition-colors"
                      >
                        Reopen
                      </button>
                    )}
                    <Link href={`/case/${c.id}?type=${c.stage}`} className="text-xs font-medium text-white bg-slate-900   px-4 py-1.5 rounded-lg hover:bg-slate-800  transition-colors">
                      {c.status === "archived" ? "View" : "Open"}
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Delete Confirmation Modal */}
      {deletingCaseId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white  rounded-xl shadow-xl w-full max-w-sm p-6 border border-slate-200 ">
            <h3 className="text-lg font-bold text-slate-900  mb-2">Delete Session?</h3>
            <p className="text-sm text-slate-500  mb-6">This will permanently remove it from your dashboard. This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setDeletingCaseId(null)} className="px-4 py-2 text-sm font-medium text-slate-600  hover:text-slate-900  transition-colors">Cancel</button>
              <button onClick={handleDeleteConfirm} className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">Delete Session</button>
            </div>
          </div>
        </div>
      )}

      <NewSessionModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
        userEmail={currentUser?.email} 
      />
    </div>
  );
}
