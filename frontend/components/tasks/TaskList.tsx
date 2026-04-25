"use client";

import { InvestigationTask } from "../../lib/api/types";

// For backward compatibility with existing components
export type { InvestigationTask as Task };

interface TaskListProps {
  tasks: InvestigationTask[];
  disabled?: boolean;
  onTaskUpdate?: (taskId: string, status: InvestigationTask["status"]) => void;
  onTaskDelete?: (taskId: string) => void;
  onTaskAction?: (task: InvestigationTask) => void;
}

export default function TaskList({ tasks, disabled, onTaskUpdate, onTaskDelete, onTaskAction }: TaskListProps) {
  // Deduplication logic
  const uniqueTasks = tasks.reduce((acc: InvestigationTask[], current) => {
    const norm = (title: string) => title.toLowerCase().replace(/[^a-z0-9]/g, '').trim();
    const x = acc.find(item => norm(item.title) === norm(current.title));
    if (!x) return acc.concat([current]);
    return acc;
  }, []);

  const handleActionClick = (task: InvestigationTask) => {
    // Internal link tasks
    if (task.type === "review_ai_suggestions") {
      const el = document.getElementById("location-analysis-section");
      if (el) el.scrollIntoView({ behavior: "smooth" });
      return;
    }

    if (onTaskAction) onTaskAction(task);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "bg-emerald-50 text-emerald-600 border-emerald-100";
      case "pending": return "bg-amber-50 text-amber-600 border-amber-100";
      case "scheduled": return "bg-indigo-50 text-indigo-600 border-indigo-100";
      default: return "bg-slate-50 text-slate-400 border-slate-100";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Case Roadmap</h3>
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">{uniqueTasks.length} total tasks</span>
      </div>

      <div className="space-y-3 px-1">
        {uniqueTasks.length === 0 ? (
          <div className="py-12 px-6 border-2 border-dashed border-slate-200 rounded-[2rem] text-center bg-slate-50/50">
            <p className="text-[11px] text-slate-500 font-black uppercase tracking-widest">No Active Tasks</p>
            <p className="text-[10px] text-slate-400 mt-2 leading-relaxed italic">Run analysis or talk to AI to generate steps.</p>
          </div>
        ) : (
          uniqueTasks.map((task) => (
            <div 
              key={task.id} 
              className={`p-5 rounded-3xl border transition-all ${
                task.status === 'completed' 
                  ? 'bg-slate-50/50 border-slate-100' 
                  : 'bg-white border-slate-100 hover:border-slate-300 shadow-sm hover:shadow-xl group ring-1 ring-slate-900/5'
              }`}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-lg text-[9px] font-black uppercase tracking-widest border ${getStatusColor(task.status)}`}>
                    {task.status}
                  </span>
                  <span className="text-[9px] text-slate-300 font-bold uppercase tracking-tight opacity-0 group-hover:opacity-100 transition-opacity">
                    {task.type?.replace(/_/g, ' ')}
                  </span>
                </div>
                {onTaskDelete && !disabled && (
                  <button 
                    onClick={(e) => { e.stopPropagation(); onTaskDelete(task.id); }}
                    className="p-1 text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
              
              <h4 className={`text-sm font-black mb-1 leading-tight text-slate-900`}>
                {task.title}
              </h4>
              <p className="text-[11px] text-slate-500 leading-relaxed mb-4">
                {task.description}
              </p>

              {task.status !== 'completed' && (
                <button
                  onClick={() => handleActionClick(task)}
                  className="w-full py-3 bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest rounded-2xl hover:bg-slate-800 transition-all shadow-md shadow-slate-900/10 active:scale-[0.98]"
                >
                  {task.actionLabel || 'Begin Task'}
                </button>
              )}

              {task.status === 'completed' && (
                <div className="space-y-3">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-[11px] text-slate-600 italic leading-relaxed">
                    <span className="font-bold text-slate-400 uppercase text-[9px] block mb-1 not-italic">Your Answer:</span>
                    {typeof task.submittedValue === 'string' ? task.submittedValue : 
                     (task.submittedValue as any)?.text ? (task.submittedValue as any).text :
                     (task.submittedValue as any)?.answers ? Object.values((task.submittedValue as any).answers).join(", ") :
                     (task.submittedValue as any)?.location?.address || "Answer provided"}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-emerald-600">
                      <div className="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-[10px] font-black uppercase tracking-widest">Step Finished</span>
                    </div>
                    <button 
                      onClick={() => handleActionClick(task)}
                      className="text-[10px] font-bold text-slate-400 hover:text-slate-900 uppercase tracking-tighter transition-colors"
                    >
                      Edit Answer
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
