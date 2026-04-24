"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";

interface NewSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function NewSessionModal({ isOpen, onClose }: NewSessionModalProps) {
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  
  // File state
  const [images, setImages] = useState<File[]>([]);
  const [documents, setDocuments] = useState<File[]>([]);
  
  const imageInputRef = useRef<HTMLInputElement>(null);
  const documentInputRef = useRef<HTMLInputElement>(null);

  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    setIsSubmitting(true);
    // Simulate network delay
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSuccess(true);
      // Wait for success animation then navigate
      setTimeout(() => {
        router.push("/case/demo-session");
      }, 1000);
    }, 800);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setImages(Array.from(e.target.files));
    }
  };

  const handleDocumentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setDocuments(Array.from(e.target.files));
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={!isSubmitting && !isSuccess ? onClose : undefined}
            className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="w-full max-w-2xl bg-white border border-slate-200 shadow-xl rounded-xl overflow-hidden flex flex-col max-h-[90vh]"
            >
              {!isSuccess ? (
                <>
                  <div className="flex justify-between items-center p-6 border-b border-slate-100">
                    <h2 className="text-lg font-semibold text-slate-900">
                      Start New F&B Genie Session
                    </h2>
                    <button
                      onClick={onClose}
                      disabled={isSubmitting}
                      className="text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
                    >
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1 space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">
                        Initial Project Details
                      </label>
                      <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Describe your F&B business idea, location, target audience, and current challenges..."
                        className="w-full bg-white border border-slate-300 rounded-lg p-4 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 transition-shadow resize-none h-32 text-sm"
                        required
                        disabled={isSubmitting}
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Upload Images Card */}
                      <button
                        type="button"
                        onClick={() => imageInputRef.current?.click()}
                        className="relative border border-dashed border-slate-300 rounded-lg p-4 flex flex-col items-center justify-center bg-slate-50 hover:bg-slate-100 hover:border-slate-400 active:bg-slate-200 transition-all cursor-pointer group focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-1"
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 border shadow-sm transition-colors ${
                          images.length > 0 ? "bg-green-50 border-green-200 text-green-600" : "bg-white border-slate-200 text-slate-500"
                        }`}>
                          {images.length > 0 ? (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                          )}
                        </div>
                        <span className="text-sm font-medium text-slate-700">Upload Images</span>
                        <span className="text-xs text-slate-500 mt-1 text-center">
                          {images.length > 0 ? `${images.length} file(s) selected` : "Menus, layout, location"}
                        </span>
                        <input 
                          type="file" 
                          ref={imageInputRef} 
                          onChange={handleImageChange} 
                          accept="image/*" 
                          multiple 
                          className="hidden" 
                        />
                      </button>

                      {/* Attach Files Card */}
                      <button
                        type="button"
                        onClick={() => documentInputRef.current?.click()}
                        className="relative border border-dashed border-slate-300 rounded-lg p-4 flex flex-col items-center justify-center bg-slate-50 hover:bg-slate-100 hover:border-slate-400 active:bg-slate-200 transition-all cursor-pointer group focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-1"
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 border shadow-sm transition-colors ${
                          documents.length > 0 ? "bg-green-50 border-green-200 text-green-600" : "bg-white border-slate-200 text-slate-500"
                        }`}>
                          {documents.length > 0 ? (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                            </svg>
                          ) : (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                            </svg>
                          )}
                        </div>
                        <span className="text-sm font-medium text-slate-700">Attach Files</span>
                        <span className="text-xs text-slate-500 mt-1 text-center">
                          {documents.length > 0 ? `${documents.length} file(s) selected` : "Financials, business plans"}
                        </span>
                        <input 
                          type="file" 
                          ref={documentInputRef} 
                          onChange={handleDocumentChange} 
                          accept=".pdf,.doc,.docx,.xls,.xlsx,.csv" 
                          multiple 
                          className="hidden" 
                        />
                      </button>
                    </div>
                  </form>

                  <div className="p-6 border-t border-slate-100 bg-slate-50 flex justify-end">
                    <button
                      onClick={handleSubmit}
                      disabled={!description.trim() || isSubmitting}
                      className="relative rounded-lg bg-slate-900 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                    >
                      {isSubmitting ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Initializing...
                        </>
                      ) : (
                        "Start Investigation"
                      )}
                    </button>
                  </div>
                </>
              ) : (
                <div className="p-12 flex flex-col items-center justify-center h-[350px]">
                  <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.3 }}
                    className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mb-4 border border-green-100"
                  >
                    <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </motion.div>
                  <motion.h2
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-lg font-medium text-slate-900 mb-1"
                  >
                    Session Created
                  </motion.h2>
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-sm text-slate-500"
                  >
                    Opening workspace...
                  </motion.p>
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
