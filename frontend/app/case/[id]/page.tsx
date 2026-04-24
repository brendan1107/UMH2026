"use client";

import { useState } from "react";
import AppShell from "../../../components/layout/AppShell";
import ChatWindow from "../../../components/chat/ChatWindow";
import ChatInput from "../../../components/chat/ChatInput";
import TaskList, { Task } from "../../../components/tasks/TaskList";
import UploadPanel, { UploadedFile } from "../../../components/uploads/UploadPanel";
import RecommendationPanel, { RecommendationData } from "../../../components/report/RecommendationPanel";

const INITIAL_MESSAGES = [
  { id: "1", role: "assistant" as const, content: "Hello. I've reviewed your initial project details for a new cafe in the downtown area. Before we proceed with the analysis, I need to clarify a few things. What is your primary target demographic? Are you aiming for office workers during lunch hours, or a more casual weekend crowd?" },
  { id: "2", role: "user" as const, content: "Mostly office workers during the week. We want to focus on quick coffee and grab-and-go lunches." },
  { id: "3", role: "assistant" as const, content: "Understood. That changes the foot traffic requirements significantly. Have you secured a specific unit yet, or are you still scouting locations? It would help to upload any street view photos or floor plans if you have them." },
];

const INITIAL_TASKS: Task[] = [
  { id: "t1", title: "Upload floor plan for potential unit", status: "pending" },
  { id: "t2", title: "Verify local parking restrictions for peak hours", status: "scheduled" },
  { id: "t3", title: "Define initial menu pricing strategy", status: "completed" },
];

const INITIAL_FILES: UploadedFile[] = [
  { id: "f1", name: "menu_draft_v2.pdf", size: "2.4 MB", type: "document" },
  { id: "f2", name: "street_view_front.jpg", size: "4.1 MB", type: "image" },
];

const INITIAL_RECOMMENDATION: RecommendationData = {
  status: "ready",
  summary: "Based on current inputs, a grab-and-go cafe targeting office workers in the downtown core has strong potential, provided the lease terms allow for high turnover without excessive fixed seating costs.",
  strengths: [
    "High density of target demographic within a 3-block radius.",
    "Proposed menu matches speed-of-service requirements.",
  ],
  risks: [
    "High local competition (4 existing coffee shops within 2 blocks).",
    "Dependency on weekday traffic; weekends may be unviable.",
  ],
};

export default function CaseWorkspace() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [tasks, setTasks] = useState<Task[]>(INITIAL_TASKS);
  const [files, setFiles] = useState<UploadedFile[]>(INITIAL_FILES);
  const [recommendation, setRecommendation] = useState<RecommendationData>(INITIAL_RECOMMENDATION);

  const handleSendMessage = (content: string) => {
    // 1. Add User Message
    const userMessage = { id: Date.now().toString(), role: "user" as const, content };
    setMessages((prev) => [...prev, userMessage]);

    // 2. Simulate AI thinking and update recommendation status to "gathering"
    setRecommendation((prev) => ({ ...prev, status: "gathering" }));

    // 3. Simulate AI reply after a short delay
    setTimeout(() => {
      const aiMessage = { 
        id: (Date.now() + 1).toString(), 
        role: "assistant" as const, 
        content: "That's a helpful detail. I've updated my analysis based on what you just shared. Feel free to provide more files or check the updated tasks on the left." 
      };
      setMessages((prev) => [...prev, aiMessage]);

      // Update recommendation dynamically based on new "knowledge"
      setRecommendation({
        status: "ready",
        summary: "The strategy focuses firmly on weekday grab-and-go office workers. Fast service and layout optimization for queues are now the primary success factors.",
        strengths: [
          ...INITIAL_RECOMMENDATION.strengths,
          "Clear target audience minimizes marketing spend.",
        ],
        risks: [
          ...INITIAL_RECOMMENDATION.risks,
          "Queue management during 12pm-1pm rush will be critical.",
        ],
      });
    }, 1500);
  };

  const handleTaskUpdate = (taskId: string, newStatus: Task["status"]) => {
    setTasks((prev) =>
      prev.map((task) =>
        task.id === taskId ? { ...task, status: newStatus } : task
      )
    );
  };

  const handleFileUpload = (file: File) => {
    const isImage = file.type.startsWith("image/");
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(1);
    
    const newFile: UploadedFile = {
      id: Date.now().toString(),
      name: file.name,
      size: `${sizeInMB} MB`,
      type: isImage ? "image" : "document",
    };
    
    setFiles((prev) => [...prev, newFile]);

    // Automatically complete "Upload floor plan" task if it exists and is pending
    setTasks((prev) => 
      prev.map(task => 
        (task.id === "t1" && task.status === "pending") ? { ...task, status: "completed" } : task
      )
    );
    
    // Simulate recommendation refresh on new file
    setRecommendation((prev) => ({ ...prev, status: "gathering" }));
    setTimeout(() => {
      setRecommendation((prev) => ({
        ...prev,
        status: "ready",
        summary: "New evidence received. Floor plan layout analysis indicates space is adequate for queue management, though kitchen prep area might be constrained.",
      }));
    }, 1000);
  };

  const leftSidebar = (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-slate-100">
        <h2 className="text-sm font-semibold text-slate-900 truncate">Downtown Cafe Project</h2>
        <p className="text-xs text-slate-500 mt-1">Case #892-A • Active</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        <TaskList tasks={tasks} onTaskUpdate={handleTaskUpdate} />
      </div>
      <UploadPanel files={files} onFileUpload={handleFileUpload} />
    </div>
  );

  const rightSidebar = (
    <RecommendationPanel data={recommendation} />
  );

  return (
    <AppShell leftSidebar={leftSidebar} rightSidebar={rightSidebar}>
      <div className="flex flex-col h-full">
        {/* Chat Header (Mobile only / context) */}
        <div className="h-14 border-b border-slate-200 bg-white flex items-center px-4 shrink-0 shadow-sm lg:hidden">
          <span className="font-semibold text-slate-900">Downtown Cafe Project</span>
        </div>
        
        {/* Chat Area */}
        <ChatWindow messages={messages} />
        
        {/* Input Area */}
        <div className="shrink-0">
          <ChatInput onSendMessage={handleSendMessage} />
        </div>
      </div>
    </AppShell>
  );
}
