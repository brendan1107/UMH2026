"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Task } from "../tasks/TaskList";

interface TaskActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: Task | null;
  onSubmit: (taskId: string, actionData: any) => void;
}

export default function TaskActionModal({ isOpen, onClose, task, onSubmit }: TaskActionModalProps) {
  const [textInput, setTextInput] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  if (!task) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    let submitData = {};
    if (task.type === "provide_text_input") submitData = { text: textInput };
    if (task.type === "answer_questions") submitData = { answers };
    if (task.type === "choose_option") submitData = { selectedOption };
    
    onSubmit(task.id, submitData);
    
    // Reset state
    setTextInput("");
    setAnswers({});
    setSelectedOption(null);
  };

  const renderContent = () => {
    switch (task.type) {
      case "choose_option":
        const options = task.data?.options || [];
        return (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 mb-4">{task.data?.description || "Select an option below:"}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {options.map((opt: any) => (
                <div 
                  key={opt.id}
                  onClick={() => setSelectedOption(opt.id)}
                  className={`border rounded-lg p-4 cursor-pointer transition-all ${selectedOption === opt.id ? 'border-slate-900 bg-slate-50 ring-1 ring-slate-900' : 'border-slate-200 hover:border-slate-400 bg-white'}`}
                >
                  <h4 className="font-semibold text-slate-900">{opt.title}</h4>
                  {opt.subtitle && <p className="text-xs text-slate-500 mb-2">{opt.subtitle}</p>}
                  
                  {opt.pros && opt.pros.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-semibold text-green-600">Pros:</p>
                      <ul className="text-xs text-slate-600 list-disc pl-4 mt-1">
                        {opt.pros.map((pro: string, i: number) => <li key={i}>{pro}</li>)}
                      </ul>
                    </div>
                  )}
                  {opt.cons && opt.cons.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-semibold text-red-600">Cons:</p>
                      <ul className="text-xs text-slate-600 list-disc pl-4 mt-1">
                        {opt.cons.map((con: string, i: number) => <li key={i}>{con}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );

      case "answer_questions":
        const questions = task.data?.questions || [];
        return (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 mb-4">{task.data?.description || "Please provide some additional details:"}</p>
            {questions.map((q: any) => (
              <div key={q.id}>
                <label className="block text-sm font-medium text-slate-700 mb-1">{q.label}</label>
                <textarea
                  value={answers[q.id] || ""}
                  onChange={(e) => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                  placeholder={q.placeholder}
                  className="w-full bg-white border border-slate-300 rounded-lg p-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 text-sm min-h-[80px]"
                />
              </div>
            ))}
          </div>
        );

      case "provide_text_input":
      case "review_ai_suggestions":
        return (
          <div className="space-y-4">
             <p className="text-sm text-slate-600 mb-2">{task.data?.description || "Provide your input:"}</p>
             <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Enter your response here..."
                className="w-full bg-white border border-slate-300 rounded-lg p-3 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 text-sm h-32"
              />
          </div>
        );

      case "upload_file":
      case "upload_image":
        return (
          <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-slate-300 rounded-xl bg-slate-50">
             <svg className="w-10 h-10 text-slate-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
             </svg>
             <p className="text-sm font-medium text-slate-700">Click or drag files here</p>
             <p className="text-xs text-slate-500 mt-1">Please use the workspace upload panel for now.</p>
          </div>
        );

      default:
        return <p className="text-sm text-slate-600">Action details not available.</p>;
    }
  };

  const isSubmitDisabled = () => {
    if (task.type === "choose_option") return !selectedOption;
    if (task.type === "answer_questions") {
      const requiredCount = task.data?.questions?.length || 0;
      return Object.keys(answers).length < requiredCount || Object.values(answers).some(val => !val.trim());
    }
    if (task.type === "provide_text_input") return !textInput.trim();
    return false;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="w-full max-w-2xl bg-white border border-slate-200 shadow-xl rounded-xl overflow-hidden flex flex-col max-h-[90vh] pointer-events-auto"
            >
              <div className="flex justify-between items-center p-5 border-b border-slate-100">
                <h2 className="text-lg font-semibold text-slate-900">
                  {task.title}
                </h2>
                <button
                  onClick={onClose}
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1">
                {renderContent()}
              </form>

              <div className="p-5 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitDisabled()}
                  className="px-6 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Submit
                </button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
