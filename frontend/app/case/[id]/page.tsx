"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
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

// --- MOCK DATA FOR NEW BUSINESSES ---
const NEW_BIZ_MESSAGES = [
  { id: "1", role: "assistant" as const, content: "Hello. I've reviewed your initial project details for a new cafe in the downtown area. Before we proceed with the analysis, I need to clarify a few things. What is your primary target demographic? Are you aiming for office workers during lunch hours, or a more casual weekend crowd?" },
  { id: "2", role: "user" as const, content: "Mostly office workers during the week. We want to focus on quick coffee and grab-and-go lunches." },
  { id: "3", role: "assistant" as const, content: "Understood. That changes the foot traffic requirements significantly. Have you secured a specific unit yet, or are you still scouting locations? It would help to upload any street view photos or floor plans if you have them." },
];

const NEW_BIZ_TASKS: Task[] = [
  { 
    id: "t1", 
    title: "Upload floor plan for potential unit", 
    status: "pending",
    type: "upload_file",
    actionLabel: "Upload Now"
  },
  { 
    id: "t2", 
    title: "Review Location Suggestions", 
    status: "pending",
    type: "choose_option",
    actionLabel: "Review Options",
    data: {
      description: "Based on your criteria, here are 3 potential areas for your cafe:",
      options: [
        { id: "loc_1", title: "Financial District", subtitle: "High foot traffic, premium rent", pros: ["Thousands of office workers", "High willingness to pay"], cons: ["Expensive lease", "Dead on weekends"] },
        { id: "loc_2", title: "Arts District", subtitle: "Trendy area, growing foot traffic", pros: ["Lower rent", "Weekend traffic is strong"], cons: ["Fewer office workers", "Highly competitive cafe market"] },
        { id: "loc_3", title: "University Hub", subtitle: "Massive student population", pros: ["High volume", "Consistent demand"], cons: ["Lower price point", "Seasonal fluctuations"] }
      ]
    }
  },
  { 
    id: "t3", 
    title: "Define target audience specifics", 
    status: "pending",
    type: "answer_questions",
    actionLabel: "Answer Questions",
    data: {
      description: "To fine-tune the recommendation, please provide details on:",
      questions: [
        { id: "q1", label: "What is your estimated average ticket size per customer?", placeholder: "e.g., $8 - $12" },
        { id: "q2", label: "Do you plan to offer loyalty programs?", placeholder: "Yes/No/Maybe" }
      ]
    }
  },
];

const NEW_BIZ_RECOMMENDATION: RecommendationData = {
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

// --- MOCK DATA FOR EXISTING BUSINESSES ---
const EXISTING_BIZ_MESSAGES = [
  { id: "1", role: "assistant" as const, content: "Hello. I'm analyzing the performance of your existing restaurant. You mentioned recent challenges with profitability. Can you provide more details about your current monthly revenue trend?" },
];

const EXISTING_BIZ_TASKS: Task[] = [
  { 
    id: "et1", 
    title: "Upload recent P&L statements", 
    status: "pending",
    type: "upload_file",
    actionLabel: "Upload Financials"
  },
  { 
    id: "et2", 
    title: "Clarify main cost drivers", 
    status: "pending",
    type: "answer_questions",
    actionLabel: "Provide Details",
    data: {
      description: "Please help identify where costs are escalating:",
      questions: [
        { id: "q1", label: "Have ingredients/food costs increased significantly?", placeholder: "Yes, specifically..." },
        { id: "q2", label: "Are labor costs becoming unmanageable?", placeholder: "Describe staffing issues..." }
      ]
    }
  },
];

const EXISTING_BIZ_RECOMMENDATION: RecommendationData = {
  status: "ready",
  summary: "Initial analysis indicates that the business is facing margin compression. Further data on cost-of-goods-sold (COGS) and labor costs is required to formulate a turnaround strategy.",
  strengths: [
    "Established brand presence in the neighborhood.",
    "Loyal customer base for weekend brunch.",
  ],
  risks: [
    "Declining weekday dinner revenue.",
    "Rising food costs are eroding margins.",
  ],
};

const INITIAL_FILES: UploadedFile[] = [
  { id: "f1", name: "menu_draft_v2.pdf", size: "2.4 MB", type: "document" },
];

export default function CaseWorkspace() {
  const searchParams = useSearchParams();
  const typeParam = searchParams.get("type");
  
  const [sessionType, setSessionType] = useState<"new" | "existing">("new");
  
  const [messages, setMessages] = useState(NEW_BIZ_MESSAGES);
  const [tasks, setTasks] = useState<Task[]>(NEW_BIZ_TASKS);
  const [recommendation, setRecommendation] = useState<RecommendationData>(NEW_BIZ_RECOMMENDATION);
  const [files, setFiles] = useState<UploadedFile[]>(INITIAL_FILES);
  
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
      setMessages(EXISTING_BIZ_MESSAGES);
      setTasks(EXISTING_BIZ_TASKS);
      setRecommendation(EXISTING_BIZ_RECOMMENDATION);
    } else {
      setSessionType("new");
      setMessages(NEW_BIZ_MESSAGES);
      setTasks(NEW_BIZ_TASKS);
      setRecommendation(NEW_BIZ_RECOMMENDATION);
    }
  }, [typeParam]);

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
          ...recommendation.strengths,
          "Clear target audience minimizes marketing spend.",
        ],
        risks: [
          ...recommendation.risks,
          "Queue management during 12pm-1pm rush will be critical.",
        ],
      });
    }, 1500);
  };

  const handleTaskActionClick = (task: Task) => {
    setActiveTask(task);
    setIsTaskModalOpen(true);
  };

  const handleTaskActionSubmit = (taskId: string, actionData: any) => {
    setIsTaskModalOpen(false);
    
    // 1. Mark task as completed
    handleTaskUpdate(taskId, "completed");
    
    // 2. Generate a user message based on the action
    let content = "I've completed the task.";
    if (activeTask?.type === "choose_option") {
      const option = activeTask.data.options.find((o: any) => o.id === actionData.selectedOption);
      content = `I have selected the option: ${option?.title || actionData.selectedOption}.`;
    } else if (activeTask?.type === "answer_questions") {
      content = "I have provided the requested details in the form.";
    } else if (activeTask?.type === "provide_text_input") {
      content = `Here is my input: ${actionData.text}`;
    }

    const userMessage = { id: Date.now().toString(), role: "user" as const, content };
    setMessages((prev) => [...prev, userMessage]);

    // 3. Trigger AI response update
    setRecommendation((prev) => ({ ...prev, status: "gathering" }));
    setTimeout(() => {
      const aiMessage = { 
        id: (Date.now() + 1).toString(), 
        role: "assistant" as const, 
        content: "Thank you for the information. I've incorporated this into the analysis and updated the recommendation." 
      };
      setMessages((prev) => [...prev, aiMessage]);
      setRecommendation((prev) => ({
        ...prev,
        status: "ready",
        summary: prev.summary + " New data has been processed and integrated."
      }));
    }, 1500);
    
    setActiveTask(null);
  };

  const handleGenerateVerdict = () => {
    setRecommendation(prev => ({ ...prev, status: "generating_verdict" }));
    
    setTimeout(() => {
      if (sessionType === "existing") {
        setRecommendation(prev => ({
          ...prev,
          status: "ready",
          verdict: "Stop / Cancel",
          verdictReasoning: "Based on the continuing margin compression, rising COGS, and declining foot traffic, the business model is no longer viable. To prevent further personal financial loss and minimize debt accumulation, it is recommended to halt operations and begin winding down.",
          nextSteps: [
            "Consult with a financial advisor to manage outstanding liabilities.",
            "Review lease exit clauses.",
            "Begin liquidating inventory and assets."
          ]
        }));
      } else {
        setRecommendation(prev => ({
          ...prev,
          status: "ready",
          verdict: "Continue with caution",
          verdictReasoning: "The grab-and-go cafe concept in the target area has merit due to the demographic density, but the high competition and premium lease rates pose a significant risk to early cash flow.",
          nextSteps: [
            "Secure a lease agreement with favorable early termination clauses.",
            "Execute a soft launch to test menu pricing.",
            "Aggressively market to local office buildings prior to opening."
          ]
        }));
      }
    }, 2500);
  };

  const handleSaveDecision = (decision: "continue" | "archive", insight: FinalInsight) => {
    setFinalInsight(insight);
    if (decision === "archive") {
      setSessionStatus("archived");
    } else {
      setSessionStatus("insight_generated");
    }
    setIsEndSessionModalOpen(false);
  };

  const handleReopenSession = () => {
    setSessionStatus("active");
    // TODO: Future backend integration should send stored message history / case summary to GLM so reopened sessions preserve AI context.
    const systemMessage = { 
      id: Date.now().toString(), 
      role: "assistant" as const, 
      content: "Session reopened. You can continue the investigation from the saved context." 
    };
    setMessages((prev) => [...prev, systemMessage]);
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
        <p className="text-xs text-slate-500 mt-1">Case #892-A - Active</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        <TaskList 
          tasks={tasks} 
          disabled={sessionStatus === "archived"}
          onTaskUpdate={handleTaskUpdate} 
          onTaskAction={handleTaskActionClick} 
        />
      </div>
      <UploadPanel files={files} onFileUpload={handleFileUpload} />
    </div>
  );

  const rightSidebar = (
    <RecommendationPanel 
      data={recommendation} 
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
        <div className="h-14 border-b border-slate-200  bg-white  flex items-center px-4 shrink-0 shadow-sm lg:hidden">
          <span className="font-semibold text-slate-900 ">Downtown Cafe Project</span>
        </div>
        
        {/* Chat Area */}
        <ChatWindow messages={messages} />
        
        {/* Input Area */}
        <div className="shrink-0">
          <ChatInput onSendMessage={handleSendMessage} disabled={sessionStatus === "archived"} />
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
