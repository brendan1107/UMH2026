"use client";

import { useState } from "react";

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSendMessage, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input);
    setInput("");
  };

  return (
    <div className="p-4 bg-white  border-t border-slate-200  transition-colors">
      <div className="max-w-3xl mx-auto relative">
        <form onSubmit={handleSubmit} className="relative flex items-end gap-2 bg-white  border border-slate-300  rounded-xl shadow-sm focus-within:ring-1 focus-within:ring-slate-900  focus-within:border-slate-900  p-2 transition-colors">
          
          <button 
            type="button" 
            disabled={disabled}
            className="p-2 text-slate-400  hover:text-slate-600  transition-colors disabled:opacity-50"
            title="Attach file"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
          </button>
          
          <textarea
            value={input}
            disabled={disabled}
            onChange={(e) => setInput(e.target.value)}
            placeholder={disabled ? "Session archived - Reopen to chat" : "Answer questions or provide more details..."}
            className="flex-1 max-h-32 min-h-[44px] bg-transparent border-0 focus:ring-0 resize-none py-3 text-slate-900  placeholder-slate-400  text-sm custom-scrollbar disabled:cursor-not-allowed"
            rows={1}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          
          <button 
            type="submit" 
            disabled={!input.trim() || disabled}
            className="p-2 rounded-lg bg-slate-900  text-white  hover:bg-slate-800  disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
          
        </form>
        <p className="text-center text-xs text-slate-400  mt-2">
          F&B Genie can make mistakes. Consider verifying important business assumptions.
        </p>
      </div>
    </div>
  );
}
