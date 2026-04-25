"use client";

export type TaskType = 
  | "answer_questions" 
  | "choose_option" 
  | "upload_file" 
  | "upload_image" 
  | "provide_text_input" 
  | "review_ai_suggestions"
  | "select_location"
  | "schedule_event";

export interface Task {
  id: string;
  title: string;
  status: "pending" | "scheduled" | "skipped" | "completed";
  type?: TaskType;
  actionLabel?: string;
  data?: Record<string, unknown>; // For options, questions, etc.
}

interface TaskListProps {
  tasks: Task[];
  disabled?: boolean;
  onTaskUpdate: (taskId: string, newStatus: Task["status"]) => void;
  onTaskDelete?: (taskId: string) => void;
  onTaskAction?: (task: Task) => void;
}

export default function TaskList({ tasks, disabled, onTaskUpdate, onTaskDelete, onTaskAction }: TaskListProps) {
  return (
    <div className="p-4">
      <h3 className="text-xs font-semibold text-slate-500  uppercase tracking-wider mb-3">
        Investigation Tasks
      </h3>
      <div className="space-y-3">
        {tasks.map((task) => {
          const isCompleted = task.status === "completed";
          const isScheduled = task.status === "scheduled";
          const isSkipped = task.status === "skipped";
          const isPending = task.status === "pending";

          return (
            <div 
              key={task.id} 
              className={`group relative overflow-hidden p-3.5 pr-10 rounded-xl border transition-all duration-300 ease-in-out ${
                isCompleted 
                  ? "bg-green-50/50  border-green-200 " 
                  : isSkipped
                  ? "bg-slate-50  border-slate-200 "
                  : isScheduled
                  ? "bg-blue-50/30  border-blue-100  hover:border-blue-300  hover:shadow-sm"
                  : "bg-white  border-slate-200  hover:border-slate-300  hover:shadow-sm"
              }`}
            >
              {onTaskDelete && !disabled && (
                <button
                  type="button"
                  onClick={() => onTaskDelete(task.id)}
                  title="Remove task"
                  aria-label={`Remove ${task.title}`}
                  className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-400 opacity-100 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-200"
                >
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 12h12" />
                  </svg>
                </button>
              )}
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex-shrink-0">
                  {isCompleted ? (
                    <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center text-white shadow-sm shadow-green-500/20">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : isSkipped ? (
                    <div className="w-5 h-5 rounded-full bg-slate-200  flex items-center justify-center text-slate-500 ">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </div>
                  ) : isScheduled ? (
                    <div className="w-5 h-5 rounded-full bg-blue-100  border border-blue-300  flex items-center justify-center text-blue-600 ">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-slate-300  flex items-center justify-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-300 "></span>
                    </div>
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex flex-col gap-1.5">
                    <p className={`text-sm transition-colors duration-300 ${
                      isCompleted 
                        ? "text-slate-800  font-medium" 
                        : isSkipped 
                        ? "text-slate-500  font-medium" 
                        : "text-slate-700  font-medium"
                    } leading-snug`}>
                      {task.title}
                    </p>
                    
                    <div className="flex flex-wrap items-center gap-2 mt-0.5">
                      {isCompleted && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-green-100  text-green-800  uppercase tracking-wide">
                          Completed
                        </span>
                      )}
                      {isScheduled && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100  text-blue-800  uppercase tracking-wide">
                          Scheduled
                        </span>
                      )}
                      {isSkipped && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-200  text-slate-700  uppercase tracking-wide">
                          Skipped
                        </span>
                      )}
                      {isPending && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-yellow-100  text-yellow-800  uppercase tracking-wide">
                          Pending
                        </span>
                      )}

                      {(isPending || isScheduled) && !disabled && (
                        <div className="flex gap-2 ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
                          <button 
                            onClick={() => onTaskUpdate(task.id, "skipped")}
                            className="text-xs font-medium text-slate-500  hover:text-slate-700  hover:underline underline-offset-2 transition-all focus:outline-none"
                          >
                            Skip
                          </button>
                        </div>
                      )}
                    </div>

                    {isPending && task.actionLabel && onTaskAction && !disabled && (
                      <div className="mt-2">
                        <button
                          onClick={() => onTaskAction(task)}
                          className="text-xs font-medium bg-slate-900  text-white  px-3 py-1.5 rounded-md hover:bg-slate-800  transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400  focus:ring-offset-1 "
                        >
                          {task.actionLabel}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
        {tasks.length === 0 && (
          <p className="text-sm text-slate-500  italic p-3 text-center border border-dashed border-slate-200  rounded-lg">
            No tasks assigned yet.
          </p>
        )}
      </div>
    </div>
  );
}
