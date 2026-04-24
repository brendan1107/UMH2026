"use client";

import { useEffect, useRef } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatWindowProps {
  messages: Message[];
}

export default function ChatWindow({ messages }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 scroll-smooth bg-white ">
      {messages.map((msg) => (
        <div 
          key={msg.id} 
          className={`flex gap-4 max-w-3xl mx-auto ${msg.role === "assistant" ? "" : "justify-end"}`}
        >
          {msg.role === "assistant" && (
            <div className="w-8 h-8 rounded bg-slate-900  flex-shrink-0 flex items-center justify-center transition-colors">
              <svg className="w-5 h-5 text-white " fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          )}
          
          <div className={`prose prose-sm max-w-none transition-colors ${
            msg.role === "user" 
              ? "bg-slate-100  px-5 py-3 rounded-2xl rounded-tr-sm text-slate-900  shadow-sm" 
              : "text-slate-800 "
          }`}>
            <p className="whitespace-pre-wrap leading-relaxed m-0">{msg.content}</p>
          </div>
          
          {msg.role === "user" && (
            <div className="w-8 h-8 rounded-full bg-slate-200  flex-shrink-0 flex items-center justify-center border border-slate-300  transition-colors">
              <span className="text-xs font-medium text-slate-600 ">U</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
