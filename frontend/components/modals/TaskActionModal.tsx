"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { InvestigationTask } from "../../lib/api/types";
type Task = InvestigationTask;

const defaultCenter = { lat: 37.7749, lng: -122.4194 };
const googleMapsScriptId = "google-maps-js-api";

type SelectedLocation = { lat: number; lng: number; address: string };
type MapPoint = Pick<SelectedLocation, "lat" | "lng">;
type GoogleMapsLatLng = { lat: () => number; lng: () => number };
type GoogleMapsMouseEvent = { latLng?: GoogleMapsLatLng | null };
type GoogleMapsListener = { remove: () => void };
type GoogleMapsMap = {
  addListener: (eventName: "click", handler: (event: GoogleMapsMouseEvent) => void) => GoogleMapsListener;
  panTo: (position: MapPoint) => void;
};
type GoogleMapsMarker = {
  setMap: (map: GoogleMapsMap | null) => void;
  setPosition: (position: MapPoint) => void;
};
type GoogleMapsApi = {
  Map: new (element: HTMLElement, options: { center: MapPoint; zoom: number; clickableIcons: boolean }) => GoogleMapsMap;
  Marker: new (options: { position: MapPoint; map: GoogleMapsMap }) => GoogleMapsMarker;
};
type GoogleMapsWindow = Window & {
  google?: { maps?: GoogleMapsApi };
  __googleMapsLoadPromise?: Promise<GoogleMapsApi>;
};
type ChoiceOption = {
  id: string;
  title: string;
  subtitle?: string;
  pros?: string[];
  cons?: string[];
};
type Question = {
  id: string;
  label: string;
  placeholder?: string;
};
type TaskData = {
  description?: string;
  options?: ChoiceOption[];
  questions?: Question[];
  eventTitle?: string;
  eventDuration?: string;
};
type UploadedTaskFile = {
  uploadId: string;
  fileName: string;
  fileType?: string;
  fileSize?: number;
  storagePath?: string;
  storageMode?: string;
  url?: string;
};
type TaskActionData =
  | { text: string }
  | { answers: Record<string, string> }
  | { selectedOption: string | null }
  | { location: SelectedLocation | null }
  | { eventDate: string }
  | UploadedTaskFile
  | Record<string, never>;

const BLOCKED_PATTERNS = [
  "firebase-service-account",
  "service-account",
  ".env",
  "env.backend",
  "credentials.json",
];

const BLOCKED_EXTENSIONS = [".pem", ".key", ".p12", ".pfx"];

const ALLOWED_EXTENSIONS = [
  ".png", ".jpg", ".jpeg", ".webp",
  ".pdf", ".doc", ".docx", ".ppt", ".pptx",
  ".csv", ".xls", ".xlsx",
];

function validateEvidenceFile(file: File): string | null {
  const filename = file.name.toLowerCase();

  if (
    BLOCKED_PATTERNS.some((pattern) => filename.includes(pattern)) ||
    BLOCKED_EXTENSIONS.some((ext) => filename.endsWith(ext))
  ) {
    return "Sensitive configuration or credential files cannot be uploaded as evidence.";
  }

  if (!ALLOWED_EXTENSIONS.some((ext) => filename.endsWith(ext))) {
    return `Unsupported file type. Allowed types: ${ALLOWED_EXTENSIONS.join(", ")}`;
  }

  return null;
}

function getGoogleMapsWindow() {
  if (typeof window === "undefined") return {} as GoogleMapsWindow;
  return window as unknown as GoogleMapsWindow;
}

function getTaskData(task: Task): TaskData {
  return (task.data ?? {}) as TaskData;
}

function loadGoogleMaps(apiKey: string): Promise<GoogleMapsApi> {
  const browserWindow = getGoogleMapsWindow();

  if (browserWindow.google?.maps) {
    return Promise.resolve(browserWindow.google.maps);
  }

  if (browserWindow.__googleMapsLoadPromise) {
    return browserWindow.__googleMapsLoadPromise;
  }

  browserWindow.__googleMapsLoadPromise = new Promise((resolve, reject) => {
    const existingScript = document.getElementById(googleMapsScriptId) as HTMLScriptElement | null;
    const handleLoad = () => {
      if (browserWindow.google?.maps) {
        resolve(browserWindow.google.maps);
      } else {
        reject(new Error("Google Maps API failed to initialize."));
      }
    };
    const handleError = () => reject(new Error("Google Maps API failed to load."));

    if (existingScript) {
      existingScript.addEventListener("load", handleLoad, { once: true });
      existingScript.addEventListener("error", handleError, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = googleMapsScriptId;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}`;
    script.async = true;
    script.defer = true;
    script.addEventListener("load", handleLoad, { once: true });
    script.addEventListener("error", handleError, { once: true });
    document.head.appendChild(script);
  });

  return browserWindow.__googleMapsLoadPromise;
}

function MapSelector({ currentLocation, onSelect }: { currentLocation: SelectedLocation | null, onSelect: (loc: SelectedLocation) => void }) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<GoogleMapsMap | null>(null);
  const markerRef = useRef<GoogleMapsMarker | null>(null);
  const currentLocationRef = useRef(currentLocation);
  const onSelectRef = useRef(onSelect);
  const [loadStatus, setLoadStatus] = useState<"loading" | "ready" | "error">("loading");
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";
  const status = apiKey ? loadStatus : "missing-key";

  useEffect(() => {
    currentLocationRef.current = currentLocation;
  }, [currentLocation]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    if (!apiKey) {
      return;
    }

    let cancelled = false;
    let clickListener: GoogleMapsListener | undefined;

    loadGoogleMaps(apiKey)
      .then((maps) => {
        if (cancelled || !mapRef.current) return;

        const initialLocation = currentLocationRef.current;
        const initialMarker = initialLocation ? { lat: initialLocation.lat, lng: initialLocation.lng } : null;
        const map = new maps.Map(mapRef.current, {
          center: initialMarker || defaultCenter,
          zoom: 12,
          clickableIcons: false,
        });

        mapInstanceRef.current = map;
        if (initialMarker) {
          markerRef.current = new maps.Marker({ position: initialMarker, map });
        }

        clickListener = map.addListener("click", (event: GoogleMapsMouseEvent) => {
          if (!event.latLng) return;

          const lat = event.latLng.lat();
          const lng = event.latLng.lng();
          const nextLocation = {
            lat,
            lng,
            address: `Selected Location (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
          };

          onSelectRef.current(nextLocation);
        });

        setLoadStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setLoadStatus("error");
      });

    return () => {
      cancelled = true;
      if (clickListener) clickListener.remove();
      if (markerRef.current) markerRef.current.setMap(null);
      markerRef.current = null;
      mapInstanceRef.current = null;
    };
  }, [apiKey]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    const maps = getGoogleMapsWindow().google?.maps;

    if (!map || !maps) return;

    const markerPos = currentLocation ? { lat: currentLocation.lat, lng: currentLocation.lng } : null;

    if (!markerPos) {
      if (markerRef.current) markerRef.current.setMap(null);
      markerRef.current = null;
      return;
    }

    if (markerRef.current) {
      markerRef.current.setPosition(markerPos);
    } else {
      markerRef.current = new maps.Marker({ position: markerPos, map });
    }
    map.panTo(markerPos);
  }, [currentLocation]);

  return (
    <div className="relative h-full w-full">
      <div ref={mapRef} className="h-full w-full" />
      {status === "loading" && (
        <div className="absolute inset-0 p-4 text-slate-500 bg-slate-100 flex justify-center items-center">
          Loading Maps...
        </div>
      )}
      {status === "missing-key" && (
        <div className="absolute inset-0 p-4 text-amber-700 bg-amber-50 flex justify-center items-center text-center">
          Google Maps API key is missing.
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 p-4 text-red-500 bg-red-50 flex justify-center items-center text-center">
          Error loading maps.
        </div>
      )}
    </div>
  );
}

interface TaskActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: Task | null;
  onSubmit: (taskId: string, actionData: TaskActionData) => void;
  onFileUpload?: (taskId: string, file: File) => Promise<UploadedTaskFile>;
}

export default function TaskActionModal({ isOpen, onClose, task, onSubmit, onFileUpload }: TaskActionModalProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [textInput, setTextInput] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [location, setLocation] = useState<{lat: number, lng: number, address: string} | null>(null);
  const [eventDate, setEventDate] = useState<string>("");
  const [selectedUploadFile, setSelectedUploadFile] = useState<File | null>(null);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);

  useEffect(() => {
    if (isOpen && task) {
      const val = task.submittedValue as any;
      if (val) {
        if (task.type === "provide_text_input" || task.type === "review_ai_suggestions") setTextInput(val.text || "");
        if (task.type === "answer_questions") setAnswers(val.answers || {});
        if (task.type === "choose_option") setSelectedOption(val.selectedOption || null);
        if (task.type === "select_location") setLocation(val.location || null);
        if (task.type === "schedule_event") setEventDate(val.eventDate || "");
      } else {
        // Reset if no submitted value
        setTextInput("");
        setAnswers({});
        setSelectedOption(null);
        setLocation(null);
        setEventDate("");
      }
    }
  }, [isOpen, task]);

  if (!task) return null;
  const taskData = getTaskData(task);

  const closeModal = () => {
    setSelectedUploadFile(null);
    setUploadError(null);
    setIsDraggingFile(false);
    onClose();
  };

  const handleSelectUploadFile = (file: File | undefined) => {
    if (!file) return;

    const validationError = validateEvidenceFile(file);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setUploadError(null);
    setSelectedUploadFile(file);
    setIsDraggingFile(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const submitAction = async (status: string = "completed") => {
    let submitData: TaskActionData = {};
    if (task.type === "provide_text_input") submitData = { text: textInput };
    if (task.type === "answer_questions") submitData = { answers };
    if (task.type === "choose_option") submitData = { selectedOption };
    if (task.type === "select_location") submitData = { location };
    if (task.type === "schedule_event") submitData = { eventDate };
    if (task.type === "upload_file" || task.type === "upload_image") {
      if (!selectedUploadFile) return;
      if (!onFileUpload) {
        setUploadError("File upload is not available for this task.");
        return;
      }

      setIsUploadingFile(true);
      setUploadError(null);
      try {
        submitData = await onFileUpload(task.id, selectedUploadFile);
      } catch (error) {
        setUploadError(error instanceof Error ? error.message : "Failed to upload file.");
        setIsUploadingFile(false);
        return;
      }
      setIsUploadingFile(false);
    }
    
    // Pass status in payload if possible or via a wrapped data structure
    // Since onSubmit signature is (taskId, actionData), we might need to wrap it
    onSubmit(task.id, { ...submitData, status } as any);
    
    // Reset state
    setTextInput("");
    setAnswers({});
    setSelectedOption(null);
    setLocation(null);
    setEventDate("");
    setSelectedUploadFile(null);
    setUploadError(null);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    void submitAction("completed");
  };

  const renderContent = () => {
    switch (task.type) {
      case "choose_option":
        const options = taskData.options || [];
        return (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 mb-4">{taskData.description || "Select an option below:"}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {options.map((opt) => (
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
        const rawQuestions = taskData.questions || (task as any).questions || [];
        const normalizedQuestions = rawQuestions.map((q: any) => 
          typeof q === 'string' ? { id: q, label: q } : q
        );
        return (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 mb-4">{taskData.description || "Please provide some additional details:"}</p>
            {normalizedQuestions.map((q: any) => (
              <div key={q.id}>
                <label className="block text-sm font-medium text-slate-700 mb-1">{q.label}</label>
                <textarea
                  value={answers[q.id] || ""}
                  onChange={(e) => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                  placeholder={q.placeholder || "Type your answer here..."}
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
             <p className="text-sm text-slate-600 mb-2">{taskData.description || "Provide your input:"}</p>
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
          <div className="space-y-3">
            <input
              ref={fileInputRef}
              type="file"
              accept={ALLOWED_EXTENSIONS.join(",")}
              className="hidden"
              onChange={(event) => handleSelectUploadFile(event.target.files?.[0])}
            />
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDraggingFile(true);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDraggingFile(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                setIsDraggingFile(false);
              }}
              onDrop={(event) => {
                event.preventDefault();
                handleSelectUploadFile(event.dataTransfer.files?.[0]);
              }}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-300 ${
                isDraggingFile
                  ? "border-slate-500 bg-slate-100"
                  : "border-slate-300 bg-slate-50 hover:border-slate-400 hover:bg-white"
              }`}
            >
              <svg className="w-10 h-10 text-slate-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-sm font-medium text-slate-700">
                {isUploadingFile ? "Uploading..." : selectedUploadFile ? selectedUploadFile.name : "Click or drag files here"}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {selectedUploadFile ? "Ready to upload on Save Action." : "PDF, images, documents, spreadsheets, or slides."}
              </p>
            </div>
            {uploadError && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {uploadError}
              </p>
            )}
          </div>
        );

      case "select_location":
        return (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 mb-4">{taskData.description || "Select your location from the map:"}</p>
            <div className="w-full h-64 bg-slate-100 rounded-lg overflow-hidden border border-slate-300 relative">
              <MapSelector currentLocation={location} onSelect={setLocation} />
            </div>
            {location && (
              <p className="text-xs text-green-600 font-medium">Selected: {location.address} ({location.lat}, {location.lng})</p>
            )}
          </div>
        );

      case "schedule_event":
        const handleAutoGenerate = () => {
          // Simulate AI filling in the event details
          const tomorrow = new Date();
          tomorrow.setDate(tomorrow.getDate() + 1);
          tomorrow.setHours(10, 0, 0, 0); // 10 AM tomorrow
          
          const offset = tomorrow.getTimezoneOffset() * 60000;
          const localISOTime = (new Date(tomorrow.getTime() - offset)).toISOString().slice(0, 16);
          setEventDate(localISOTime);
        };

        return (
          <div className="space-y-4">
            <div className="flex justify-between items-center mb-4">
              <p className="text-sm text-slate-600">{taskData.description || "Save an event to Google Calendar:"}</p>
              <button 
                type="button" 
                onClick={handleAutoGenerate}
                className="text-xs font-semibold text-purple-600 bg-purple-50 hover:bg-purple-100 px-2.5 py-1.5 rounded-md transition-colors flex items-center gap-1 shadow-sm border border-purple-100"
              >
                ✨ Auto-generate with AI
              </button>
            </div>
            <div className="p-4 border border-slate-200 rounded-lg bg-white">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-medium text-slate-900">{taskData.eventTitle || "Investigation Meeting"}</h4>
                  <p className="text-xs text-slate-500">{taskData.eventDuration || "1 hour"}</p>
                </div>
              </div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Select Date & Time</label>
              <input 
                type="datetime-local" 
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-500">Requires Google Calendar permission</span>
                <button type="button" className="text-xs text-blue-600 hover:text-blue-800 font-medium" onClick={async () => {
                  try {
                    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
                    const domain = baseUrl.replace(/\/api$/, '');
                    const response = await fetch(`${domain}/api/calendar/auth/url`);
                    const data = await response.json();
                    if (data.auth_url) {
                      window.open(data.auth_url, "_blank");
                    }
                  } catch {
                    alert("Failed to request calendar access.");
                  }
                }}>
                  Grant Access
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return <p className="text-sm text-slate-600">Action details not available.</p>;
    }
  };

  const isSubmitDisabled = () => {
    if (task.type === "choose_option") return !selectedOption;
    if (task.type === "answer_questions") {
      const requiredCount = taskData.questions?.length || 0;
      return Object.keys(answers).length < requiredCount || Object.values(answers).some(val => !val.trim());
    }
    if (task.type === "provide_text_input") return !textInput.trim();
    if (task.type === "select_location") return !location;
    if (task.type === "schedule_event") return !eventDate;
    if (task.type === "upload_file" || task.type === "upload_image") return !selectedUploadFile || isUploadingFile;
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
            onClick={closeModal}
            className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40"
          />
          <div className="fixed inset-y-0 right-0 z-50 flex items-center justify-end pointer-events-none sm:pr-4 py-4 w-full sm:w-[450px]">
            <motion.div
              initial={{ opacity: 0, x: 100 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 100 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              className="w-full h-full bg-white border border-slate-200 shadow-2xl sm:rounded-2xl overflow-hidden flex flex-col pointer-events-auto"
            >
              <div className="flex justify-between items-center p-5 border-b border-slate-100">
                <h2 className="text-lg font-semibold text-slate-900">
                  {task.title}
                </h2>
                <button
                  type="button"
                  onClick={closeModal}
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

              <div className="p-5 border-t border-slate-100 bg-slate-50 flex justify-between items-center">
                <button
                  type="button"
                  onClick={() => void submitAction("pending")}
                  className="px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-900 transition-colors"
                >
                  Save as Draft
                </button>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={closeModal}
                    className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => void submitAction("completed")}
                    disabled={isSubmitDisabled()}
                    className="px-6 py-2 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {task.status === 'completed' ? 'Update Answer' : 'Complete Task'}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
