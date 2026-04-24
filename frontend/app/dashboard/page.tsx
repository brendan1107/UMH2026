"use client";

import { useState } from "react";
import NewSessionModal from "../../components/modals/NewSessionModal";
import { signOut } from "firebase/auth";
import { auth } from "../../lib/firebase";

export default function DashboardPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error("Failed to log out", error);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] text-slate-900 pb-20">
      {/* Navigation Bar */}
      <nav className="border-b border-slate-200 bg-white">
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
            <div className="flex items-center gap-4">
              <button className="w-9 h-9 rounded-full hover:bg-slate-100 flex items-center justify-center transition-colors">
                <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
              </button>
              <button 
                onClick={handleLogout}
                className="w-9 h-9 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center hover:bg-slate-200 transition-colors"
                title="Log out"
              >
                <svg className="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight mb-2">
              Dashboard
            </h1>
            <p className="text-base text-slate-500 max-w-2xl">
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

        {/* Empty State Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-12 sm:p-16 text-center flex flex-col items-center justify-center min-h-[300px]">
          <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
            <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No active investigations</h3>
          <p className="text-slate-500 max-w-sm mx-auto mb-6 text-sm">
            You haven't started any F&B cases yet. Click the button below to initialize your first business analysis.
          </p>
          
          <button 
            onClick={() => setIsModalOpen(true)}
            className="text-slate-900 font-medium hover:text-slate-700 transition-colors flex items-center gap-2 bg-slate-50 hover:bg-slate-100 px-5 py-2 rounded-lg border border-slate-200 text-sm"
          >
            Initialize First Case
          </button>
        </div>
      </main>

      <NewSessionModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
