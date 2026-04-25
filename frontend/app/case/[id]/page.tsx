"use client";

import { useState, useEffect } from "react";
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
import { auth } from "../../../lib/firebase";

// API services
import { 
  casesService, 
  chatService, 
  tasksService, 
  reportsService, 
  uploadsService, 
  verdictService,
  ChatMessage,
  BusinessCase,
  EvidenceUpload,
  InvestigationTask,
  TaskActionData
} from "../../../lib/api";

const toStoredUploadedFiles = (uploads: EvidenceUpload[]): UploadedFile[] =>
  uploads.map((upload) => ({
    id: upload.id,
    name: upload.name || upload.fileName || "Uploaded file",
    size: upload.size,
    type: upload.type
  }));

const toTaskListItems = (apiTasks: InvestigationTask[]): Task[] =>
  apiTasks.map((task) => ({ ...task }));

type UploadedTaskAction = {
  uploadId: string;
  fileName: string;
  fileType?: string;
  fileSize?: number;
  storagePath?: string;
  storageMode?: string;
  url?: string;
};
type SubmittedTaskAction = {
  selectedOption?: string | null;
  answers?: Record<string, string>;
  text?: string;
  location?: { lat: number; lng: number; address: string } | null;
  eventDate?: string;
  uploadId?: string;
  fileName?: string;
};
type SessionStatus = "active" | "insight_generated" | "archived";
type TaskOption = { id: string; title?: string };
type TaskQuestion = { id: string; label?: string };
type TaskModalData = {
  options?: TaskOption[];
  questions?: TaskQuestion[];
};

const toSessionStatus = (status: BusinessCase["status"]): SessionStatus =>
  status === "archived" || status === "insight_generated" ? status : "active";

const toTaskUploadAction = (upload: EvidenceUpload): UploadedTaskAction => ({
  uploadId: upload.id,
  fileName: upload.name || upload.fileName || "Uploaded file",
  fileType: upload.fileType,
  fileSize: upload.fileSize,
  storagePath: upload.storagePath,
  storageMode: upload.storageMode,
  url: upload.url,
});

const toTaskUploadedFilesAction = (uploads: UploadedTaskAction[]): TaskActionData =>
  uploads.length === 1
    ? uploads[0]
    : {
        uploads,
        uploadIds: uploads.map((upload) => upload.uploadId),
        fileNames: uploads.map((upload) => upload.fileName),
      };

const formatUploadedFilesMessage = (uploads: UploadedTaskAction[]) => {
  if (uploads.length === 1) {
    return `Uploaded file: ${uploads[0].fileName}.`;
  }

  return `Uploaded files:\n${uploads.map((upload) => `- ${upload.fileName}`).join("\n")}`;
};

const isUploadNotFoundError = (error: unknown) =>
  error instanceof Error && error.message.toLowerCase().includes("upload not found");

export default function CaseWorkspace() {
  const params = useParams();
  const id = params.id as string;
  const searchParams = useSearchParams();
  const typeParam = searchParams.get("type");
  const sessionType: "new" | "existing" = typeParam === "existing" ? "existing" : "new";
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [recommendation, setRecommendation] = useState<RecommendationData | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [caseDetails, setCaseDetails] = useState<BusinessCase | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  
  // Session Status State
  const [sessionStatus, setSessionStatus] = useState<SessionStatus>("active");
  const [finalInsight, setFinalInsight] = useState<FinalInsight | null>(null);

  // Modal state
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isEndSessionModalOpen, setIsEndSessionModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  
  // Staged tasks state
  const [stagedTaskActions, setStagedTaskActions] = useState<Record<string, TaskActionData>>({});

  const currentUser = auth.currentUser;

  const refreshTasks = async () => {
    const tasksData = await tasksService.getTasks(id);
    setTasks(toTaskListItems(tasksData));
    return tasksData;
  };

  const refreshUploads = async () => {
    const uploadsData = await uploadsService.listUploads(id);
    setFiles(toStoredUploadedFiles(uploadsData));
    return uploadsData;
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [caseData, messagesData, tasksData, uploadsData] = await Promise.all([
          casesService.getCaseById(id),
          chatService.getMessages(id, "default_session"),
          tasksService.getTasks(id),
          uploadsService.listUploads(id)
        ]);

        setCaseDetails(caseData);
        setSessionStatus(toSessionStatus(caseData.status));
        setMessages(messagesData);
        setTasks(toTaskListItems(tasksData));
        setFiles(toStoredUploadedFiles(uploadsData));

        try {
          const recData = await reportsService.getLatestRecommendation(id);
          setRecommendation(recData as RecommendationData);
        } catch {
          // No recommendation yet
          setRecommendation({
            status: "gathering",
            summary: "Waiting for enough data to generate a recommendation.",
            strengths: [],
            risks: []
          });
        }
      } catch (error) {
        console.error("Failed to load case data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      fetchData();
    }
  }, [id]);

  const handleSendMessage = async (content: string, pendingFiles: File[] = []): Promise<boolean> => {
    let messageContent = content.trim();
    let uploadedActions: UploadedTaskAction[] = [];

    try {
      if (pendingFiles.length > 0) {
        const uploadedFiles = await uploadEvidenceFiles(pendingFiles);
        uploadedActions = uploadedFiles.map(toTaskUploadAction);
        const uploadMessage = formatUploadedFilesMessage(uploadedActions);
        messageContent = messageContent ? `${messageContent}\n\n${uploadMessage}` : uploadMessage;

        const uploadTask = tasks.find(t => (t.type === "upload_file" || t.type === "upload_image") && t.status === "pending");
        if (uploadTask) {
          const updatedTask = await tasksService.updateTask(
            id,
            uploadTask.id,
            "completed",
            toTaskUploadedFilesAction(uploadedActions)
          );
          setTasks((prev) =>
            prev.map((task) => (task.id === uploadTask.id ? ({ ...task, ...updatedTask } as Task) : task))
          );
        }
      }
    } catch (error) {
      console.error("Failed to upload attached files", error);
      alert("Failed to upload attached files. Please try again.");
      return false;
    }

    if (!messageContent) return false;

    // Optimistic UI for user message
    const createdAt = new Date().toISOString();
    const userMessage: ChatMessage = {
      id: `local-${createdAt}`,
      role: "user",
      content: messageContent,
      attachments: uploadedActions.map((upload) => upload.uploadId),
      createdAt
    };
    setMessages((prev) => [...prev, userMessage]);
    setRecommendation((prev) => prev ? { ...prev, status: "gathering" } : prev);

    try {
      const aiMessage = await chatService.sendMessage(
        id,
        "default_session",
        messageContent,
        uploadedActions.map((upload) => upload.uploadId)
      );
      setMessages((prev) => [...prev, aiMessage]);
      await refreshTasks();

      try {
        const updatedRec = await reportsService.getLatestRecommendation(id);
        setRecommendation(updatedRec as RecommendationData);
      } catch (error) {
        console.error("Failed to get updated recommendation", error);
      }
    } catch (error) {
      console.error("Failed to send message", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      const createdAt = new Date().toISOString();
      const assistantErrorMessage: ChatMessage = {
        id: `local-send-error-${createdAt}`,
        role: "assistant",
        content: `I could not reach the backend API, so this message was not saved. ${errorMessage}`,
        createdAt
      };
      setMessages((prev) => [...prev, assistantErrorMessage]);
      setRecommendation((prev) =>
        prev ? { ...prev, status: "gathering" } : prev
      );
    }
    return true;
  };

  const handleTaskActionClick = (task: Task) => {
    setActiveTask(task);
    setIsTaskModalOpen(true);
  };

  const handleTaskActionSubmit = async (taskId: string, actionData: TaskActionData) => {
    setIsTaskModalOpen(false);

    try {
      const updatedTask = await tasksService.updateTask(id, taskId, "completed", actionData);
      setTasks((prev) =>
        prev.map((task) => (task.id === taskId ? ({ ...task, ...updatedTask } as Task) : task))
      );
      setStagedTaskActions(prev => ({ ...prev, [taskId]: actionData }));
    } catch (error) {
      console.error("Failed to save task action", error);
      alert("Failed to save task action. Please try again.");
    } finally {
      setActiveTask(null);
    }
  };

  const handleSubmitAllTasks = async () => {
    const tasksToSubmit = Object.entries(stagedTaskActions);
    if (tasksToSubmit.length === 0) return;

    try {
      const contents = [];
      for (const [taskId, actionData] of tasksToSubmit) {
        const task = tasks.find(t => t.id === taskId);
        const taskData = task?.data as TaskModalData | undefined;
        const submitted = actionData as SubmittedTaskAction;
        let content = `I've completed the task: ${task?.title || taskId}.`;
        
        if (task?.type === "choose_option") {
          const option = taskData?.options?.find((option) => option.id === submitted.selectedOption);
          content += `\nSelected option: ${option?.title || submitted.selectedOption}.`;
        } else if (task?.type === "answer_questions") {
          content += "\nProvided details:\n";
          for (const [qId, ans] of Object.entries(submitted.answers || {})) {
            const q = taskData?.questions?.find((question) => question.id === qId);
            content += `- ${q?.label || qId}: ${ans}\n`;
          }
        } else if (task?.type === "provide_text_input") {
          content += `\nInput: ${submitted.text}`;
        } else if (task?.type === "select_location") {
          content += `\nSelected location: ${submitted.location?.address} (${submitted.location?.lat}, ${submitted.location?.lng})`;
        } else if (task?.type === "schedule_event") {
          content += `\nScheduled event for: ${submitted.eventDate}`;
        } else if (task?.type === "upload_file" || task?.type === "upload_image") {
          content += `\nUploaded file: ${submitted.fileName || submitted.uploadId || "uploaded evidence"}.`;
        }
        contents.push(content);
      }
      
      const finalContent = contents.join("\n\n");
      await handleSendMessage(finalContent);
      setStagedTaskActions({});
    } catch (error) {
      console.error("Failed to submit staged tasks", error);
    }
  };

  const handleGenerateVerdict = async () => {
    setRecommendation(prev => prev ? { ...prev, status: "generating_verdict" } : {
      status: "generating_verdict",
      summary: "",
      strengths: [],
      risks: []
    });
    
    try {
      const verdict = await verdictService.generateVerdict(id);
      setRecommendation(prev => ({
        ...(prev || {}),
        status: "ready",
        summary: verdict.reasoning,
        strengths: verdict.strengths || prev?.strengths || [],
        verdict: verdict.verdict,
        verdictReasoning: verdict.reasoning,
        nextSteps: verdict.nextSteps,
        risks: verdict.risks?.map((risk) =>
          [risk.title, risk.reasoning].filter(Boolean).join(": ")
        ) || prev?.risks || []
      }));

      try {
        const updatedRec = await reportsService.getLatestRecommendation(id);
        setRecommendation(updatedRec as RecommendationData);
      } catch (error) {
        console.error("Failed to refresh generated recommendation", error);
      }
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

  const handleSaveDecision = async (decision: "continue" | "archive", insight: FinalInsight) => {
    try {
      await casesService.endSession(id, decision, insight);
      setFinalInsight(insight);
      setSessionStatus(decision === "archive" ? "archived" : "insight_generated");
      setIsEndSessionModalOpen(false);
    } catch (error) {
      console.error("Failed to save decision", error);
    }
  };

  const handleReopenSession = async () => {
    try {
      await casesService.reopenCase(id);
      setSessionStatus("active");
      const systemMessage: ChatMessage = { 
        id: Date.now().toString(), 
        role: "assistant", 
        content: "Session reopened. You can continue the investigation from the saved context.",
        createdAt: new Date().toISOString()
      };
      setMessages((prev) => [...prev, systemMessage]);
    } catch (error) {
      console.error("Failed to reopen case", error);
    }
  };

  const uploadEvidenceFiles = async (pendingFiles: File[]): Promise<EvidenceUpload[]> => {
    const uploadedFiles: EvidenceUpload[] = [];
    for (const file of pendingFiles) {
      uploadedFiles.push(await uploadsService.uploadFile(id, file));
    }
    await refreshUploads();
    return uploadedFiles;
  };

  const uploadEvidenceFile = async (file: File): Promise<EvidenceUpload> => {
    const [uploaded] = await uploadEvidenceFiles([file]);
    return uploaded;
  };

  const handleFileUpload = async (file: File) => {
    try {
      const uploaded = await uploadEvidenceFile(file);

      // Automatically complete "Upload floor plan" task if it exists and is pending
      const uploadTask = tasks.find(t => (t.type === "upload_file" || t.type === "upload_image") && t.status === "pending");
      if (uploadTask) {
        const updatedTask = await tasksService.updateTask(id, uploadTask.id, "completed", toTaskUploadAction(uploaded));
        setTasks((prev) =>
          prev.map((task) => (task.id === uploadTask.id ? ({ ...task, ...updatedTask } as Task) : task))
        );
        await handleSendMessage("I've uploaded the requested file.");
      }
    } catch (error) {
      console.error("Failed to upload file", error);
      alert("Failed to upload file. Please try again.");
    }
  };

  const handleTaskFileUpload = async (_taskId: string, file: File): Promise<UploadedTaskAction> => {
    const uploaded = await uploadEvidenceFile(file);
    return toTaskUploadAction(uploaded);
  };

  const deleteEvidenceFile = async (fileId: string, showAlert = true) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));

    try {
      await uploadsService.deleteUpload(id, fileId);
    } catch (error) {
      if (isUploadNotFoundError(error)) return;

      console.error("Failed to delete file", error);
      await refreshUploads().catch(() => undefined);
      if (showAlert) {
        alert("Failed to delete file. Please try again.");
        return;
      }
      throw error;
    }
  };

  const handleFileDelete = async (fileId: string) => {
    await deleteEvidenceFile(fileId);
  };

  const handleTaskDelete = async (taskId: string) => {
    const task = tasks.find((item) => item.id === taskId);
    const confirmed = window.confirm(`Remove "${task?.title || "this task"}" from this investigation?`);
    if (!confirmed) return;

    try {
      await tasksService.deleteTask(id, taskId);
      setTasks((prev) => prev.filter((item) => item.id !== taskId));
      setStagedTaskActions((prev) => {
        const next = { ...prev };
        delete next[taskId];
        return next;
      });

      if (activeTask?.id === taskId) {
        setIsTaskModalOpen(false);
        setActiveTask(null);
      }
    } catch (error) {
      console.error("Failed to delete task", error);
      alert("Failed to remove task. Please try again.");
    }
  };

  if (isLoading) {
    return (
      <AppShell leftSidebar={<div />} rightSidebar={<div />} onSettingsClick={() => setIsSettingsOpen(true)}>
        <div className="flex items-center justify-center h-full">Loading workspace...</div>
      </AppShell>
    );
  }

  const leftSidebar = (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-slate-100">
        <h2 className="text-sm font-semibold text-slate-900 truncate">
          {caseDetails?.title || "Project Workspace"}
        </h2>
        <p className="text-xs text-slate-500 mt-1">Case #{id.slice(0, 5)} - {sessionStatus}</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        <TaskList 
          tasks={tasks} 
          disabled={sessionStatus === "archived"}
          onTaskUpdate={(taskId, status) => {
            tasksService
              .updateTask(id, taskId, status)
              .then((updatedTask) => {
                setTasks((prev) =>
                  prev.map((task) => (task.id === taskId ? ({ ...task, ...updatedTask } as Task) : task))
                );
              })
              .catch((error) => {
                console.error("Failed to update task", error);
                alert("Failed to update task. Please try again.");
              });
          }} 
          onTaskDelete={handleTaskDelete}
          onTaskAction={handleTaskActionClick} 
        />
        {Object.keys(stagedTaskActions).length > 0 && (
          <div className="px-4 pb-4">
            <button 
              onClick={handleSubmitAllTasks}
              className="w-full py-2.5 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 shadow-sm transition-colors flex items-center justify-center gap-2"
            >
              <span>Submit All Completed Tasks</span>
              <span className="bg-white/20 text-white text-xs px-2 py-0.5 rounded-full">
                {Object.keys(stagedTaskActions).length}
              </span>
            </button>
          </div>
        )}
      </div>
      <UploadPanel
        files={files}
        onFileUpload={handleFileUpload}
        onFileDelete={handleFileDelete}
      />
    </div>
  );

  const rightSidebar = (
    <RecommendationPanel 
      data={recommendation || { status: "gathering", summary: "", strengths: [], risks: [] }} 
      sessionStatus={sessionStatus}
      finalInsight={finalInsight}
      onGenerateVerdict={handleGenerateVerdict} 
      onEndSessionClick={() => setIsEndSessionModalOpen(true)}
      onReopenSessionClick={handleReopenSession}
      onExportPdf={handleExportPdf}
      isExportingPdf={isExportingPdf}
    />
  );

  return (
    <AppShell 
      leftSidebar={leftSidebar} 
      rightSidebar={rightSidebar}
      onSettingsClick={() => setIsSettingsOpen(true)}
    >
      <div className="flex flex-col h-full bg-white ">
        {/* Chat Header (Mobile only / context) */}
        <div className="h-14 border-b border-slate-200 bg-white flex items-center px-4 shrink-0 shadow-sm lg:hidden">
          <span className="font-semibold text-slate-900 ">
            {caseDetails?.title || "Project Workspace"}
          </span>
        </div>
        
        {/* Chat Area */}
        {/* ChatWindow needs to support our ChatMessage which has createdAt instead of role alone if modified, but let's assume it maps correctly */}
        <ChatWindow messages={messages} />
        
        {/* Input Area */}
        <div className="shrink-0">
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={sessionStatus === "archived"}
          />
        </div>
      </div>
      <TaskActionModal 
        key={`${activeTask?.id || "none"}-${isTaskModalOpen ? "open" : "closed"}`}
        isOpen={isTaskModalOpen} 
        onClose={() => setIsTaskModalOpen(false)} 
        task={activeTask} 
        onSubmit={handleTaskActionSubmit}
        onFileUpload={handleTaskFileUpload}
      />
      <EndSessionModal
        isOpen={isEndSessionModalOpen}
        onClose={() => setIsEndSessionModalOpen(false)}
        sessionType={sessionType}
        onSaveDecision={handleSaveDecision}
      />
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
        userEmail={currentUser?.email} 
      />
    </AppShell>
  );
}
