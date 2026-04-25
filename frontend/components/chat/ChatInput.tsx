"use client";

import { useState, useRef } from "react";

interface ChatInputProps {
  onSendMessage: (content: string, files?: File[]) => void | boolean | Promise<void | boolean>;
  disabled?: boolean;
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

export default function ChatInput({ onSendMessage, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    const filename = file.name.toLowerCase();

    if (BLOCKED_PATTERNS.some(pattern => filename.includes(pattern)) ||
        BLOCKED_EXTENSIONS.some(ext => filename.endsWith(ext))) {
      return "Sensitive configuration or credential files cannot be uploaded as evidence.";
    }

    if (!ALLOWED_EXTENSIONS.some(ext => filename.endsWith(ext))) {
      return `Unsupported file type. Allowed types: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }

    return null;
  };

  const submitMessage = async () => {
    if ((!input.trim() && selectedFiles.length === 0) || disabled || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const sent = await onSendMessage(input.trim(), selectedFiles);
      if (sent !== false) {
        setInput("");
        setSelectedFiles([]);
      }
    } catch (error) {
      console.error("Failed to send message", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void submitMessage();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const nextFiles = Array.from(e.target.files);
      const validFiles: File[] = [];

      for (const file of nextFiles) {
        const validationError = validateFile(file);
        if (validationError) {
          alert(validationError);
        } else {
          validFiles.push(file);
        }
      }

      setSelectedFiles(validFiles);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const removeSelectedFile = (indexToRemove: number) => {
    setSelectedFiles((prev) => prev.filter((_, index) => index !== indexToRemove));
  };

  return (
    <div className="p-4 bg-white  border-t border-slate-200  transition-colors">
      <div className="max-w-3xl mx-auto relative">
        <form onSubmit={handleSubmit} className="relative bg-white border border-slate-200 rounded-xl shadow-sm focus-within:border-slate-300 focus-within:ring-2 focus-within:ring-slate-100 p-2 transition-colors">
          {selectedFiles.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2 px-1">
              {selectedFiles.map((file, index) => (
                <div key={`${file.name}-${file.lastModified}-${index}`} className="flex max-w-full items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-700">
                  <svg className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="max-w-[13rem] truncate">{file.name}</span>
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => removeSelectedFile(index)}
                    className="rounded-full p-0.5 text-slate-400 transition-colors hover:bg-slate-200 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-50"
                    title="Remove file"
                    aria-label={`Remove ${file.name}`}
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              multiple
              accept={ALLOWED_EXTENSIONS.join(",")}
              className="hidden"
            />
            <button
              type="button"
              disabled={disabled || isSubmitting}
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-slate-400  hover:text-slate-600  transition-colors disabled:opacity-50"
              title="Attach file"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>

            <textarea
              value={input}
              disabled={disabled || isSubmitting}
              onChange={(e) => setInput(e.target.value)}
              placeholder={disabled ? "Session archived - Reopen to chat" : "Answer questions or provide more details..."}
              className="flex-1 max-h-32 min-h-[44px] bg-transparent border-0 outline-none ring-0 resize-none py-3 text-sm text-slate-900 placeholder-slate-400 focus:border-transparent focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 disabled:cursor-not-allowed custom-scrollbar"
              rows={1}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void submitMessage();
                }
              }}
            />

            <button
              type="submit"
              disabled={(!input.trim() && selectedFiles.length === 0) || disabled || isSubmitting}
              className="p-2 rounded-lg bg-slate-900  text-white  hover:bg-slate-800  disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </form>
        <p className="text-center text-xs text-slate-400  mt-2">
          F&B Genie can make mistakes. Consider verifying important business assumptions.
        </p>
      </div>
    </div>
  );
}
