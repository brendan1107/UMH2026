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
  EvidenceUpload
} from "../../../lib/api";

const toStoredUploadedFiles = (uploads: EvidenceUpload[]): UploadedFile[] =>
  uploads
    .filter((upload) => Boolean(upload.storagePath))
    .map((upload) => ({
      id: upload.id,
      name: upload.name || upload.fileName || "Uploaded file",
      size: upload.size,
      type: upload.type
    }));

export default function CaseWorkspace() {
  const params = useParams();
  const id = params.id as string;
  const searchParams = useSearchParams();
  const typeParam = searchParams.get("type");
  
  const [sessionType, setSessionType] = useState<"new" | "existing">("new");
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [recommendation, setRecommendation] = useState<RecommendationData | null>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [caseDetails, setCaseDetails] = useState<BusinessCase | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Session Status State
  const [sessionStatus, setSessionStatus] = useState<"active" | "insight_generated" | "archived">("active");
  const [finalInsight, setFinalInsight] = useState<FinalInsight | null>(null);

  // Modal state
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isEndSessionModalOpen, setIsEndSessionModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const currentUser = auth.currentUser;

  useEffect(() => {
    if (typeParam === "existing") {
      setSessionType("existing");
    } else {
      setSessionType("new");
    }
  }, [typeParam]);

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
        setSessionStatus(caseData.status as any);
        setMessages(messagesData);
        setTasks(tasksData as any);
        setFiles(toStoredUploadedFiles(uploadsData));

        try {
          const recData = await reportsService.getLatestRecommendation(id);
          setRecommendation(recData as RecommendationData);
        } catch (e) {
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

  const handleSendMessage = async (content: string) => {
    // Optimistic UI for user message
    const userMessage: ChatMessage = { id: Date.now().toString(), role: "user", content, createdAt: new Date().toISOString() };
    setMessages((prev) => [...prev, userMessage]);
    setRecommendation((prev) => prev ? { ...prev, status: "gathering" } : prev);

    try {
      const aiMessage = await chatService.sendMessage(id, "default_session", content);
      setMessages((prev) => [...prev, aiMessage]);

      try {
        const updatedRec = await reportsService.getLatestRecommendation(id);
        setRecommendation(updatedRec as RecommendationData);
      } catch (e) {
        console.error("Failed to get updated recommendation", e);
      }
    } catch (error) {
      console.error("Failed to send message", error);
      // Optional: remove optimistic message on failure or show error state
    }
  };

  const handleTaskActionClick = (task: Task) => {
    setActiveTask(task);
    setIsTaskModalOpen(true);
  };

  const handleTaskActionSubmit = async (taskId: string, actionData: any) => {
    setIsTaskModalOpen(false);
    
    try {
      // 1. Mark task as completed on backend
      await tasksService.updateTask(taskId, "completed");
      handleTaskUpdate(taskId, "completed");
      
      // 2. Generate a user message based on the action
      let content = "I've completed the task.";
      if (activeTask?.type === "choose_option") {
        const option = activeTask.data?.options?.find((o: any) => o.id === actionData.selectedOption);
        content = `I have selected the option: ${option?.title || actionData.selectedOption}.`;
      } else if (activeTask?.type === "answer_questions") {
        content = "I have provided the requested details in the form.";
      } else if (activeTask?.type === "provide_text_input") {
        content = `Here is my input: ${actionData.text}`;
      }

      // 3. Send message
      await handleSendMessage(content);
    } catch (error) {
      console.error("Failed to submit task action", error);
    }
    
    setActiveTask(null);
  };

  const handleGenerateVerdict = async () => {
    setRecommendation(prev => prev ? { ...prev, status: "generating_verdict" } : prev);
    
    try {
      const verdict = await verdictService.generateVerdict(id);
      setRecommendation(prev => prev ? {
        ...prev,
        status: "ready",
        verdict: verdict.verdict as any,
        verdictReasoning: verdict.reasoning,
        nextSteps: verdict.nextSteps
      } : prev);
    } catch (error) {
      console.error("Failed to generate verdict", error);
      setRecommendation(prev => prev ? { ...prev, status: "ready" } : prev);
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

  const handleTaskUpdate = (taskId: string, newStatus: Task["status"]) => {
    setTasks((prev) =>
      prev.map((task) =>
        task.id === taskId ? { ...task, status: newStatus } : task
      )
    );
  };

  const handleFileUpload = async (file: File) => {
    try {
      const uploaded = await uploadsService.uploadFile(id, file);
      if (uploaded.storageMode !== "firebase_storage" || !uploaded.storagePath) {
        throw new Error("Upload did not complete in Firebase Storage.");
      }

      const uploadsData = await uploadsService.listUploads(id);
      setFiles(toStoredUploadedFiles(uploadsData));

      // Automatically complete "Upload floor plan" task if it exists and is pending
      const uploadTask = tasks.find(t => t.type === "upload_file" && t.status === "pending");
      if (uploadTask) {
        await tasksService.updateTask(uploadTask.id, "completed");
        handleTaskUpdate(uploadTask.id, "completed");
        await handleSendMessage("I've uploaded the requested file.");
      }
    } catch (error) {
      console.error("Failed to upload file", error);
      alert("Failed to upload file to Firebase Storage. Please try again.");
    }
  };

  const handleFileDelete = async (fileId: string) => {
    try {
      await uploadsService.deleteUpload(id, fileId);
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
    } catch (error) {
      console.error("Failed to delete file", error);
      alert("Failed to delete file. Please try again.");
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
            tasksService.updateTask(taskId, status).then(() => handleTaskUpdate(taskId, status));
          }} 
          onTaskAction={handleTaskActionClick} 
        />
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
        <ChatWindow messages={messages as any} />
        
        {/* Input Area */}
        <div className="shrink-0">
          <ChatInput
            onSendMessage={handleSendMessage}
            onFileUpload={handleFileUpload}
            disabled={sessionStatus === "archived"}
          />
        </div>
      </div>
      <TaskActionModal 
        isOpen={isTaskModalOpen} 
        onClose={() => setIsTaskModalOpen(false)} 
        task={activeTask} 
        onSubmit={handleTaskActionSubmit}
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
