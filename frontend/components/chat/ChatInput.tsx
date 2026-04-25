"use client";

import { useState, useRef } from "react";

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  onFileUpload?: (file: File) => void;
  disabled?: boolean;
  value?: string;
  onChange?: (value: string) => void;
}

const BLOCKED_PATTERNS = [
  "firebase-service-account",
  "service-account",
  ".env",
  "env.backend",
  "credentials.json",
];

const BLOCKED_EXTENSIONS = [".pem", ".key", ".p12", ".pfx"];

const ALLOWED_EXTENSIONS = [
  ".png", ".jpg", ".jpeg", ".webp",
  ".pdf", ".doc", ".docx", ".ppt", ".pptx",
  ".csv", ".xls", ".xlsx"
];

export default function ChatInput({ onSendMessage, onFileUpload, disabled, value, onChange }: ChatInputProps) {
  const [internalInput, setInternalInput] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const input = value !== undefined ? value : internalInput;
  const setInput = onChange ? onChange : setInternalInput;

  const validateFile = (file: File): boolean => {
    const filename = file.name.toLowerCase();

    if (BLOCKED_PATTERNS.some(pattern => filename.includes(pattern)) ||
        BLOCKED_EXTENSIONS.some(ext => filename.endsWith(ext))) {
      alert("Sensitive configuration or credential files cannot be uploaded as evidence.");
      return false;
    }

    if (!ALLOWED_EXTENSIONS.some(ext => filename.endsWith(ext))) {
      alert(`Unsupported file type. Allowed types: ${ALLOWED_EXTENSIONS.join(", ")}`);
      return false;
    }

    return true;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input);
    setInput("");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0 && onFileUpload) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        onFileUpload(file);
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="p-4 bg-white border-t border-slate-200 transition-colors">
      <div className="max-w-3xl mx-auto relative">
        <form onSubmit={handleSubmit} className="relative flex items-end gap-2 bg-white border border-slate-200 rounded-xl shadow-sm focus-within:border-slate-300 focus-within:ring-2 focus-within:ring-slate-100 p-2 transition-colors">
          
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
          <button 
            type="button" 
            disabled={disabled || !onFileUpload}
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
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
            className="flex-1 max-h-32 min-h-[44px] bg-transparent border-0 outline-none ring-0 resize-none py-3 text-sm text-slate-900 placeholder-slate-400 focus:border-transparent focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 disabled:cursor-not-allowed custom-scrollbar"
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
            className="p-2 rounded-lg bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
          
        </form>
        <p className="text-center text-xs text-slate-400 mt-2">
          F&B Genie can make mistakes. Consider verifying important business assumptions.
        </p>
      </div>
    </div>
  );
}
