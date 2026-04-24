import { useState, useEffect } from "react";

import { signOut } from "firebase/auth";
import { auth } from "../../lib/firebase";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  userEmail?: string | null;
}

export default function SettingsModal({ isOpen, onClose, userEmail }: SettingsModalProps) {

  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = async () => {
    try {
      await signOut(auth);
      // Next.js routing should handle the redirect (via protected route HOC or auth state listener)
    } catch (error) {
      console.error("Failed to log out", error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
          <h2 className="text-lg font-semibold text-slate-900">Settings</h2>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-8">
          
          {/* Account Section */}
          <section>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Account</h3>
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center">
                  <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-900">Logged in as</p>
                  <p className="text-sm text-slate-500 truncate max-w-[200px]">
                    {userEmail || "User"}
                  </p>
                </div>
              </div>
              <button 
                onClick={handleLogout}
                className="w-full py-2 px-4 bg-white border border-slate-200 text-red-600 text-sm font-medium rounded-lg hover:bg-red-50 transition-colors"
              >
                Log Out
              </button>
            </div>
          </section>

          {/* About Section */}
          <section>
             <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">About</h3>
             <div className="px-1">
                <p className="text-sm text-slate-600">
                  F&B Genie
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  AI-powered business consulting.
                </p>
             </div>
          </section>

        </div>
      </div>
    </div>
  );
}
