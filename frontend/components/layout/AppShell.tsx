"use client";

import { ReactNode } from "react";
import Link from "next/link";

interface AppShellProps {
  leftSidebar: ReactNode;
  children: ReactNode;
  rightSidebar: ReactNode;
}

export default function AppShell({ leftSidebar, children, rightSidebar }: AppShellProps) {
  return (
    <div className="flex h-screen bg-[#F9FAFB] text-slate-900 overflow-hidden">
      {/* Left Sidebar */}
      <aside className="w-80 flex-shrink-0 border-r border-slate-200 bg-white flex flex-col hidden lg:flex">
        <div className="h-14 border-b border-slate-100 flex items-center justify-between px-4">
          <Link href="/dashboard" className="flex items-center gap-2 text-slate-900 font-semibold hover:opacity-80 transition-opacity">
            <div className="w-6 h-6 bg-slate-900 rounded flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            F&B Genie
          </Link>
          <button 
            onClick={() => {
              import("firebase/auth").then(({ signOut }) => {
                import("../../lib/firebase").then(({ auth }) => {
                  signOut(auth);
                });
              });
            }}
            className="w-8 h-8 rounded-md bg-white border border-slate-200 flex items-center justify-center hover:bg-slate-50 transition-colors"
            title="Log out"
          >
            <svg className="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {leftSidebar}
        </div>
      </aside>

      {/* Main Center Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-white shadow-[0_0_40px_rgba(0,0,0,0.03)] z-10">
        {children}
      </main>

      {/* Right Sidebar */}
      <aside className="w-80 flex-shrink-0 border-l border-slate-200 bg-[#F9FAFB] flex flex-col hidden xl:flex">
        <div className="h-14 border-b border-slate-200 bg-white flex items-center px-4 font-medium text-sm text-slate-700">
          Recommendation & Analysis
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {rightSidebar}
        </div>
      </aside>
    </div>
  );
}
