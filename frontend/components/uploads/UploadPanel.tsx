"use client";

import { useRef } from "react";

export interface UploadedFile {
  id: string;
  name: string;
  size: string;
  type: "image" | "document";
}

interface UploadPanelProps {
  files: UploadedFile[];
  onFileUpload: (file: File) => void;
}

export default function UploadPanel({ files, onFileUpload }: UploadPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileUpload(e.target.files[0]);
      // Reset input so the same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="p-4 border-t border-slate-100 transition-colors">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Evidence & Files
      </h3>
      
      <div className="space-y-2 mb-4">
        {files.map(file => (
          <div key={file.id} className="flex items-center justify-between p-2 rounded-lg border border-slate-200 bg-white group hover:border-slate-300 transition-colors">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-8 h-8 rounded bg-slate-50 flex items-center justify-center flex-shrink-0 text-slate-400">
                {file.type === "image" ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                )}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700  truncate">{file.name}</p>
                <p className="text-xs text-slate-400 ">{file.size}</p>
              </div>
            </div>
            <button className="text-slate-400  hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all p-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
        {files.length === 0 && (
          <p className="text-sm text-slate-500  italic">No files uploaded.</p>
        )}
      </div>

      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
        className="hidden" 
      />
      <button 
        onClick={() => fileInputRef.current?.click()}
        className="w-full py-2 border border-dashed border-slate-300  rounded-lg text-sm text-slate-600  hover:bg-slate-50  hover:text-slate-900  transition-colors flex items-center justify-center gap-2"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Upload New File
      </button>
    </div>
  );
}
