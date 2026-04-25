"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import AppShell from "../../../components/layout/AppShell";
import ChatWindow from "../../../components/chat/ChatWindow";
import ChatInput from "../../../components/chat/ChatInput";
import TaskList, { Task } from "../../../components/tasks/TaskList";
import UploadPanel, { UploadedFile } from "../../../components/uploads/UploadPanel";
import RecommendationPanel, { RecommendationData } from "../../../components/report/RecommendationPanel";
import TaskActionModal from "../../../components/modals/TaskActionModal";
import EndSessionModal, { FinalInsight } from "../../../components/modals/EndSessionModal";
import SettingsModal from "../../../components/modals/SettingsModal";
import LocationAnalysis from "../../../components/locations/LocationAnalysis";
import { auth } from "../../../lib/firebase";

// API services
import { 
  casesService, chatService, tasksService, reportsService, 
  uploadsService, verdictService, ChatMessage, BusinessCase, 
  EvidenceUpload, InvestigationTask, TaskActionData
} from "../../../lib/api";

// ─── TYPES & INTERFACES ─────────────────────────────────────────────────────────

type UploadedTaskAction = { uploadId: string; fileName: string; fileType?: string; fileSize?: number; storagePath?: string; storageMode?: string; url?: string; };
type SubmittedTaskAction = { selectedOption?: string | null; answers?: Record<string, string>; text?: string; location?: { lat: number; lng: number; address: string } | null; eventDate?: string; uploadId?: string; fileName?: string; };
type SessionStatus = "active" | "insight_generated" | "archived";
type TaskOption = { id: string; title?: string };
type TaskQuestion = { id: string; label?: string };
type TaskModalData = { options?: TaskOption[]; questions?: TaskQuestion[]; };

// ─── HELPER FUNCTIONS ───────────────────────────────────────────────────────────

const toStoredUploadedFiles = (uploads: EvidenceUpload[]): UploadedFile[] =>
  uploads.map((u) => ({ id: u.id, name: u.name || u.fileName || "Uploaded file", size: u.size, type: u.type }));

const toTaskListItems = (apiTasks: InvestigationTask[]): Task[] => apiTasks.map((task) => ({ ...task }));
const toSessionStatus = (status: BusinessCase["status"]): SessionStatus => (status === "archived" || status === "insight_generated" ? status : "active");
const isUploadNotFoundError = (error: unknown) => error instanceof Error && error.message.toLowerCase().includes("upload not found");

const toTaskUploadAction = (upload: EvidenceUpload): UploadedTaskAction => ({
  uploadId: upload.id, fileName: upload.name || upload.fileName || "Uploaded file", fileType: upload.fileType, fileSize: upload.fileSize, storagePath: upload.storagePath, storageMode: upload.storageMode, url: upload.url,
});

/** Formats structured task data into a readable chat message string */
const formatTaskSubmissionText = (task: Task | undefined, submitted: SubmittedTaskAction): string => {
  if (!task) return "";
  const taskData = task.data as TaskModalData | undefined;
  let content = `I've completed the task: ${task.title || task.id}.`;
  
  switch (task.type) {
    case "choose_option":
      const option = taskData?.options?.find((o) => o.id === submitted.selectedOption);
      content += `\nSelected option: ${option?.title || submitted.selectedOption}.`;
      break;
    case "answer_questions":
      content += "\nProvided details:\n";
      Object.entries(submitted.answers || {}).forEach(([qId, ans]) => {
        const q = taskData?.questions?.find((question) => question.id === qId);
        content += `- ${q?.label || qId}: ${ans}\n`;
      });
      break;
    case "provide_text_input":
      content += `\nInput: ${submitted.text}`;
      break;
    case "select_location":
      content += `\nSelected location: ${submitted.location?.address} (${submitted.location?.lat}, ${submitted.location?.lng})`;
      break;
    case "schedule_event":
      content += `\nScheduled event for: ${submitted.eventDate}`;
      break;
    case "upload_file":
    case "upload_image":
      content += `\nUploaded file: ${submitted.fileName || submitted.uploadId || "uploaded evidence"}.`;
      break;
  }
  return content;
};

// ─── MAIN COMPONENT ─────────────────────────────────────────────────────────────

export default function CaseWorkspace() {
  const params = useParams();
  const id = params.id as string;
  const searchParams = useSearchParams();
  const sessionType: "new" | "existing" = searchParams.get("type") === "existing" ? "existing" : "new";
  const currentUser = auth.currentUser;
  
  // Core State
  const [caseDetails, setCaseDetails] = useState<BusinessCase | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [recommendation, setRecommendation] = useState<RecommendationData | null>(null);
  
  // UI & Status State
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("active");
  const [chatInputText, setChatInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false); // Prevents double submits
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  // Modal State
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isEndSessionModalOpen, setIsEndSessionModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [finalInsight, setFinalInsight] = useState<FinalInsight | null>(null);
  const [stagedTaskActions, setStagedTaskActions] = useState<Record<string, TaskActionData>>({});

  // ─── DATA FETCHING (Memoized) ─────────────────────────────────────────────────

  const refreshTasks = useCallback(async () => {
    const tasksData = await tasksService.getTasks(id);
    
    // Deduplicate tasks by canonicalKey or normalized title
    const dedupedTasks = tasksData.reduce((acc: InvestigationTask[], current) => {
      const norm = (t: string) => t?.toLowerCase().replace(/[^a-z0-9]/g, '').trim() || '';
      const xIndex = acc.findIndex(item => {
        if (item.canonicalKey && current.canonicalKey) return item.canonicalKey === current.canonicalKey;
        return norm(item.title) === norm(current.title);
      });
      if (xIndex === -1) return [...acc, current];
      const existing = acc[xIndex];
      // Priority: completed > latest updated
      if (current.status === "completed" && existing.status !== "completed") {
        const newAcc = [...acc]; newAcc[xIndex] = current; return newAcc;
      }
      if (current.status === existing.status) {
        const currentUpdate = current.updatedAt ? new Date(current.updatedAt).getTime() : 0;
        const existingUpdate = existing.updatedAt ? new Date(existing.updatedAt).getTime() : 0;
        if (currentUpdate > existingUpdate) {
          const newAcc = [...acc]; newAcc[xIndex] = current; return newAcc;
        }
      }
      return acc;
    }, []);

    setTasks(toTaskListItems(dedupedTasks));
    return dedupedTasks;
  }, [id]);

  const refreshUploads = useCallback(async () => {
    const uploadsData = await uploadsService.listUploads(id);
    setFiles(toStoredUploadedFiles(uploadsData));
    return uploadsData;
  }, [id]);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [caseData, messagesData, tasksData, uploadsData] = await Promise.all([
        casesService.getCaseById(id),
        chatService.getMessages(id, "default_session"),
        tasksService.getTasks(id),
        uploadsService.listUploads(id)
      ]);

      setCaseDetails(caseData);
      setSessionStatus(toSessionStatus(caseData.status));
      setMessages(messagesData);
      
      // Deduplicate tasks by canonicalKey or normalized title
      const dedupedTasks = tasksData.reduce((acc: InvestigationTask[], current) => {
        const norm = (t: string) => t?.toLowerCase().replace(/[^a-z0-9]/g, '').trim() || '';
        const xIndex = acc.findIndex(item => {
          if (item.canonicalKey && current.canonicalKey) return item.canonicalKey === current.canonicalKey;
          return norm(item.title) === norm(current.title);
        });
        if (xIndex === -1) return [...acc, current];
        const existing = acc[xIndex];
        // Priority: completed > latest updated
        if (current.status === "completed" && existing.status !== "completed") {
          const newAcc = [...acc]; newAcc[xIndex] = current; return newAcc;
        }
        if (current.status === existing.status) {
          const currentUpdate = current.updatedAt ? new Date(current.updatedAt).getTime() : 0;
          const existingUpdate = existing.updatedAt ? new Date(existing.updatedAt).getTime() : 0;
          if (currentUpdate > existingUpdate) {
            const newAcc = [...acc]; newAcc[xIndex] = current; return newAcc;
          }
        }
        return acc;
      }, []);

      setTasks(toTaskListItems(dedupedTasks));
      setFiles(toStoredUploadedFiles(uploadsData));

      try {
        const recData = await reportsService.getLatestRecommendation(id);
        setRecommendation(recData as RecommendationData);
      } catch {
        setRecommendation({ status: "gathering", summary: "Waiting for enough data to generate a recommendation.", strengths: [], risks: [] });
      }
    } catch (err) {
      console.error("Failed to load case data:", err);
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg.match(/fetch|NetworkError/i) ? "Could not connect to backend. Ensure server is running." : msg);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) fetchData();
  }, [id, fetchData]);

  // ─── CHAT & TASK HANDLERS ─────────────────────────────────────────────────────

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isProcessing) return;
    setIsProcessing(true);

    const userMessage: ChatMessage = { id: Date.now().toString(), role: "user", content, createdAt: new Date().toISOString() };
    setMessages((prev) => [...prev, userMessage]);
    setChatInputText(""); // Clear input immediately for better UX
    setRecommendation((prev) => prev ? { ...prev, status: "gathering" } : prev);

    try {
      await chatService.sendMessage(id, "default_session", content);
      setMessages(await chatService.getMessages(id, "default_session"));
      await refreshTasks();
      
      const updatedRec = await reportsService.getLatestRecommendation(id);
      setRecommendation(updatedRec as RecommendationData);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setMessages((prev) => [...prev, {
        id: `${Date.now()}-error`, role: "assistant", content: `Connection error: ${errorMessage}`, createdAt: new Date().toISOString()
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTaskActionSubmit = async (taskId: string, actionData: TaskActionData) => {
    setIsTaskModalOpen(false);
    try {
      const updatedTask = await tasksService.updateTask(id, taskId, "completed", actionData);
      setStagedTaskActions((prev) => ({ ...prev, [taskId]: actionData }));
      await refreshTasks();
      setMessages(await chatService.getMessages(id, "default_session"));
      
      // Also refresh recommendation state as it might have changed
      try {
        const recData = await reportsService.getLatestRecommendation(id);
        setRecommendation(recData as RecommendationData);
      } catch (err) { /* ignore if not ready */ }
    } catch (error) {
      console.error("Failed to save task", error);
      alert("Failed to save task. Please try again.");
    } finally {
      setActiveTask(null);
    }
  };

  const handleSubmitAllTasks = () => {
    const tasksToSubmit = Object.entries(stagedTaskActions);
    if (tasksToSubmit.length === 0) return;

    const contents = tasksToSubmit.map(([taskId, actionData]) => {
      const task = tasks.find(t => t.id === taskId);
      return formatTaskSubmissionText(task, actionData as SubmittedTaskAction);
    });
    
    const finalContent = contents.join("\n\n");
    // Draft it into the input box instead of auto-sending
    setChatInputText((prev) => prev ? `${prev}\n\n${finalContent}` : finalContent);
    setStagedTaskActions({});
  };

  const handleTaskDelete = async (taskId: string) => {
    if (!window.confirm("Remove this task from the investigation?")) return;
    try {
      await tasksService.deleteTask(id, taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      setStagedTaskActions((prev) => { const next = { ...prev }; delete next[taskId]; return next; });
    } catch (error) {
      alert("Failed to remove task.");
    }
  };

  const handleGenerateVerdict = async () => {
    setRecommendation(prev => prev ? { ...prev, status: "generating_verdict" } : prev);
    try {
      const verdict = await verdictService.generateVerdict(id);
      setRecommendation(prev => ({
        ...(prev || { status: "ready", summary: "", strengths: [], risks: [] }),
        status: "ready",
        verdict: verdict.verdict,
        verdictReasoning: verdict.reasoning,
        nextSteps: verdict.nextSteps,
        strengths: verdict.strengths || prev?.strengths || [],
        risks: verdict.risks?.map((risk) =>
          [risk.title, risk.reasoning].filter(Boolean).join(": ")
        ) || prev?.risks || [],
      }));

      try {
        setRecommendation(await reportsService.getLatestRecommendation(id) as RecommendationData);
      } catch {}
    } catch (error) {
      console.error("Failed to generate verdict", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to generate verdict.";
      alert(errorMessage);
      setRecommendation(prev => prev ? { ...prev, status: "ready" } : prev);
    }
  };

  const handleExportPdf = async () => {
    if (!recommendation?.verdict) {
      alert("Generate a verdict before exporting the PDF report.");
      return;
    }

    setIsExportingPdf(true);
    try {
      await reportsService.exportPdf(id);
    } catch (error) {
      console.error("Failed to export PDF report", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to export PDF report.";
      alert(errorMessage);
    } finally {
      setIsExportingPdf(false);
    }
  };

  // ─── FILE UPLOAD HANDLERS ─────────────────────────────────────────────────────

  const uploadEvidenceFile = async (file: File): Promise<EvidenceUpload> => {
    const uploaded = await uploadsService.uploadFile(id, file);
    await refreshUploads();
    return uploaded;
  };

  const handleFileUpload = async (file: File) => {
    try {
      const uploaded = await uploadEvidenceFile(file);
      const uploadTask = tasks.find(t => (t.type === "upload_file" || t.type === "upload_image") && t.status === "pending");
      
      if (uploadTask) {
        const updatedTask = await tasksService.updateTask(id, uploadTask.id, "completed", toTaskUploadAction(uploaded));
        setTasks((prev) => prev.map((t) => (t.id === uploadTask.id ? ({ ...t, ...updatedTask } as Task) : t)));
        await handleSendMessage("I've uploaded the requested file.");
      }
    } catch (error) {
      alert("Failed to upload file. Please try again.");
    }
  };

  const deleteEvidenceFile = async (fileId: string, showAlert = true) => {
    // Optimistic UI update: remove the file from the list immediately
    setFiles((prev) => prev.filter((f) => f.id !== fileId));

    try {
      await uploadsService.deleteUpload(id, fileId);
    } catch (error) {
      if (isUploadNotFoundError(error)) return;

      console.error("Failed to delete file", error);
      // Revert the optimistic update if it failed
      await refreshUploads().catch(() => undefined);
      if (showAlert) {
        alert("Failed to delete file. Please try again.");
      }
    }
  };



  // ─── RENDERERS ────────────────────────────────────────────────────────────────

  if (error) {
    return (
      <AppShell leftSidebar={<div />} rightSidebar={<div />} onSettingsClick={() => setIsSettingsOpen(true)}>
        <div className="flex flex-col items-center justify-center h-full p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
            <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mb-2">Connection Failure</h2>
          <p className="text-slate-500 mb-8 max-w-md mx-auto">{error}</p>
          <button onClick={fetchData} className="px-8 py-3 bg-slate-900 text-white rounded-xl font-semibold hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/20">
            Retry Connection
          </button>
        </div>
      </AppShell>
    );
  }

  if (isLoading) {
    return (
      <AppShell leftSidebar={<div />} rightSidebar={<div />} onSettingsClick={() => setIsSettingsOpen(true)}>
        <div className="flex items-center justify-center h-full text-slate-500 font-medium animate-pulse">
          Loading workspace...
        </div>
      </AppShell>
    );
  }

  const leftSidebar = (
    <div className="flex flex-col h-full bg-slate-50/50">
      <div className="p-4 border-b border-slate-200 bg-white">
        <h2 className="text-sm font-semibold text-slate-900 truncate">{caseDetails?.title || "Project Workspace"}</h2>
        <p className="text-xs text-slate-500 mt-1">Case #{id.slice(0, 5)} - <span className="capitalize">{sessionStatus.replace('_', ' ')}</span></p>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <TaskList 
          tasks={tasks.filter(t => t.status !== "completed" || stagedTaskActions[t.id])} 
          title="Investigation Tasks"
          disabled={sessionStatus === "archived"}
          onTaskUpdate={async (taskId, status) => {
            try {
              const updatedTask = await tasksService.updateTask(id, taskId, status);
              setTasks((prev) => prev.map((t) => (t.id === taskId ? ({ ...t, ...updatedTask } as Task) : t)));
            } catch { alert("Failed to update task."); }
          }} 
          onTaskDelete={handleTaskDelete}
          onTaskAction={(t) => { setActiveTask(t); setIsTaskModalOpen(true); }} 
        />
        
        {Object.keys(stagedTaskActions).length > 0 && (
          <div className="px-4 pb-4">
            <button 
              onClick={handleSubmitAllTasks}
              className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 shadow-sm transition-colors flex items-center justify-center gap-2"
            >
              <span>Draft Submission to Chat</span>
              <span className="bg-white/20 text-white text-xs px-2 py-0.5 rounded-full">{Object.keys(stagedTaskActions).length}</span>
            </button>
          </div>
        )}
        
        <TaskList 
          tasks={tasks.filter(t => t.status === "completed" && !stagedTaskActions[t.id])} 
          title="Completed Tasks" 
          disabled={sessionStatus === "archived"} 
          onTaskAction={(t) => { setActiveTask(t); setIsTaskModalOpen(true); }}
          onTaskUpdate={() => {}} 
        />
        
        <div className="p-4 border-t border-slate-200">
          <LocationAnalysis caseId={id} onAnalysisComplete={async () => {
            await refreshTasks();
            setMessages(await chatService.getMessages(id, "default_session"));
            try {
              setRecommendation(await reportsService.getLatestRecommendation(id) as RecommendationData);
            } catch {}
          }} />
        </div>
      </div>
      
      <UploadPanel files={files} onFileUpload={handleFileUpload} onFileDelete={(fileId) => deleteEvidenceFile(fileId)} />
    </div>
  );

  const rightSidebar = (
    <RecommendationPanel 
      data={recommendation || { status: "gathering", summary: "", strengths: [], risks: [] }} 
      sessionStatus={sessionStatus}
      finalInsight={finalInsight}
      onGenerateVerdict={handleGenerateVerdict}
      onEndSessionClick={() => setIsEndSessionModalOpen(true)}
      onReopenSessionClick={async () => {
        await casesService.reopenCase(id);
        setSessionStatus("active");
        setMessages((prev) => [...prev, { id: Date.now().toString(), role: "assistant", content: "Session reopened.", createdAt: new Date().toISOString() }]);
      }}
      onExportPdf={handleExportPdf}
      isExportingPdf={isExportingPdf}
    />
  );

  return (
    <AppShell leftSidebar={leftSidebar} rightSidebar={rightSidebar} onSettingsClick={() => setIsSettingsOpen(true)}>
      <div className="flex flex-col h-full bg-white relative">
        <div className="h-14 border-b border-slate-200 bg-white flex items-center px-4 shrink-0 shadow-sm lg:hidden">
          <span className="font-semibold text-slate-900 truncate">{caseDetails?.title || "Workspace"}</span>
        </div>
        
        <ChatWindow messages={messages} />
        
        <div className="shrink-0 relative">
          <ChatInput
            value={chatInputText}
            onChange={setChatInputText}
            onSendMessage={handleSendMessage}
            onFileUpload={handleFileUpload}
            disabled={sessionStatus === "archived" || isProcessing}
          />
          {isProcessing && (
            <div className="absolute top-0 left-0 w-full h-1 bg-indigo-100 overflow-hidden">
              <div className="h-full bg-indigo-600 animate-pulse w-1/3"></div>
            </div>
          )}
        </div>
      </div>

      <TaskActionModal isOpen={isTaskModalOpen} onClose={() => setIsTaskModalOpen(false)} task={activeTask} onSubmit={handleTaskActionSubmit} onFileUpload={async (taskId, file) => toTaskUploadAction(await uploadEvidenceFile(file))} />
      <EndSessionModal isOpen={isEndSessionModalOpen} onClose={() => setIsEndSessionModalOpen(false)} sessionType={sessionType} onSaveDecision={async (decision, insight) => { await casesService.endSession(id, decision, insight); setFinalInsight(insight); setSessionStatus(decision === "archive" ? "archived" : "insight_generated"); setIsEndSessionModalOpen(false); }} />
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} userEmail={currentUser?.email} />
    </AppShell>
  );
}
