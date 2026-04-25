"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { InvestigationTask } from "../../lib/api/types";

interface TaskActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: InvestigationTask | null;
  onComplete: (taskId: string, response: any) => Promise<void>;
}

export default function TaskActionModal({ isOpen, onClose, task, onComplete }: TaskActionModalProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [textInput, setTextInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (task) {
      setAnswers({});
      setTextInput("");
      // Pre-fill if already submitted?
      if (task.submittedValue) {
        if ("answers" in task.submittedValue) {
          setAnswers(task.submittedValue.answers as Record<string, string>);
        } else if ("text" in task.submittedValue) {
          setTextInput(task.submittedValue.text as string);
        }
      }
    }
  }, [task]);

  const handleSubmit = async () => {
    if (!task) return;
    setIsSubmitting(true);
    try {
      let response: any = {};
      if (task.type === "answer_questions") {
        response = { answers };
      } else if (task.type === "provide_text_input") {
        response = { text: textInput };
      } else {
        response = { text: textInput || "Task completed" };
      }
      
      await onComplete(task.id, response);
      onClose();
    } catch (error) {
      console.error("Failed to submit task:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderContent = () => {
    if (!task) return null;

    if (task.type === "answer_questions" && task.questions && task.questions.length > 0) {
      return (
        <div className="space-y-6">
          {task.questions.map((q, i) => (
            <div key={i} className="space-y-2">
              <label className="text-[11px] font-black text-slate-400 uppercase tracking-widest">{q}</label>
              <textarea
                value={answers[q] || ""}
                onChange={(e) => setAnswers(prev => ({ ...prev, [q]: e.target.value }))}
                className="w-full p-4 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-900/5 focus:border-slate-900 min-h-[80px] transition-all bg-slate-50/50"
                placeholder="Type your answer here..."
              />
            </div>
          ))}
        </div>
      );
    }

    if (task.type === "provide_text_input") {
      return (
        <div className="space-y-2">
          <label className="text-[11px] font-black text-slate-400 uppercase tracking-widest">{task.title}</label>
          <textarea
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            className="w-full p-4 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-900/5 focus:border-slate-900 min-h-[120px] transition-all bg-slate-50/50"
            placeholder="Provide requested details..."
          />
        </div>
      );
    }

    if (task.type === "upload_file") {
        return (
          <div className="py-12 border-2 border-dashed border-slate-200 rounded-3xl flex flex-col items-center justify-center space-y-4 bg-slate-50/50">
            <div className="w-12 h-12 rounded-2xl bg-white shadow-sm flex items-center justify-center">
              <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
            </div>
            <div className="text-center">
              <p className="text-sm font-bold text-slate-900">Upload evidence for this task</p>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-black mt-1">PDF, JPG, or PNG</p>
            </div>
            <button className="px-6 py-2 bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest rounded-xl hover:bg-slate-800 transition-all">
              Select File
            </button>
            <p className="text-[10px] text-slate-400 italic">TODO: Connect to file upload service</p>
          </div>
        );
      }

    return (
      <div className="space-y-4">
        <p className="text-sm text-slate-600 leading-relaxed">{task.description}</p>
        <textarea
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            className="w-full p-4 text-sm border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-900/5 focus:border-slate-900 min-h-[100px] transition-all bg-slate-50/50"
            placeholder="Add any notes or results here..."
        />
      </div>
    );
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
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[200]"
          />
          <div className="fixed inset-0 z-[201] overflow-y-auto pointer-events-none flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-lg bg-white rounded-[2.5rem] shadow-2xl overflow-hidden pointer-events-auto flex flex-col border border-slate-100"
            >
              {/* Header */}
              <div className="px-8 py-6 border-b border-slate-50 flex items-center justify-between bg-slate-50/30">
                <div className="space-y-1">
                  <h3 className="text-base font-black text-slate-900">{task?.actionLabel || "Task Action"}</h3>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Case Investigation</p>
                </div>
                <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 transition-colors">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Body */}
              <div className="px-8 py-8 overflow-y-auto max-h-[60vh] custom-scrollbar">
                {renderContent()}
              </div>

              {/* Footer */}
              <div className="px-8 py-6 border-t border-slate-50 flex gap-3 bg-white">
                <button
                  onClick={onClose}
                  className="flex-1 py-3 text-[11px] font-black text-slate-500 uppercase tracking-widest rounded-2xl border border-slate-200 hover:bg-slate-50 transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                  className="flex-1 py-3 bg-slate-900 text-white text-[11px] font-black uppercase tracking-widest rounded-2xl hover:bg-slate-800 shadow-lg shadow-slate-900/20 transition-all disabled:opacity-50"
                >
                  {isSubmitting ? "Saving..." : "Submit Response"}
                </button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
