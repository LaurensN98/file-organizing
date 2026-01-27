"use client";

import { useState } from "react";
import { Upload, Shield, FileText, Download, Check, Loader2, FolderOpen } from "lucide-react";
import axios from "axios";
import { clsx } from "clsx";

export default function Home() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [consent, setConsent] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleUpload = async () => {
    if (!files || !consent) return;

    setIsUploading(true);
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/upload`,
        formData,
        {
          responseType: "blob",
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "organized_documents.zip");
      document.body.appendChild(link);
      link.click();
      setIsDone(true);
    } catch (error) {
      console.error("Upload failed", error);
      alert("Something went wrong. Please check your connection.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFiles(e.dataTransfer.files);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-[#FAFAFA]">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="mb-8 text-center sm:text-left">
          <div className="flex items-center justify-center sm:justify-start gap-2 mb-2">
            <div className="h-6 w-6 bg-black rounded-md flex items-center justify-center">
               <FolderOpen size={14} className="text-white" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight text-gray-900">
              DocuSort
            </h1>
          </div>
          <p className="text-sm text-gray-500">
            Secure, automated document organization.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.04)] border border-gray-100 overflow-hidden">
          
          {/* Upload Area */}
          <div 
            className={clsx(
              "p-8 transition-colors duration-200 ease-in-out border-b border-gray-50",
              dragActive ? "bg-gray-50" : "bg-white"
            )}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              multiple
              className="hidden"
              id="file-upload"
              onChange={(e) => setFiles(e.target.files)}
            />
            
            <label 
              htmlFor="file-upload" 
              className="flex flex-col items-center justify-center cursor-pointer group"
            >
              <div className="mb-4 h-12 w-12 rounded-full bg-gray-50 flex items-center justify-center group-hover:bg-gray-100 transition-colors">
                <Upload size={20} className="text-gray-400 group-hover:text-gray-600" />
              </div>
              <p className="text-sm font-medium text-gray-900 mb-1">
                Upload documents
              </p>
              <p className="text-xs text-gray-400">
                Drag and drop or click to select
              </p>
            </label>

            {files && (
              <div className="mt-6 flex items-center justify-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-xs font-medium text-gray-600 w-fit mx-auto border border-gray-100">
                <FileText size={14} />
                {files.length} {files.length === 1 ? 'file' : 'files'} selected
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="p-6 bg-gray-50/50">
            <div className="flex items-start gap-3 mb-6">
              <input
                type="checkbox"
                id="consent"
                className="mt-0.5 rounded border-gray-300 text-black focus:ring-black/5"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              <label htmlFor="consent" className="text-xs text-gray-500 leading-relaxed cursor-pointer select-none">
                I have read and agree to the <a href="/privacy" target="_blank" className="underline hover:text-black">Privacy Policy</a>, and I understand that my data will be processed by AI subprocessors hosted in the EU.
              </label>
            </div>

            <button
              onClick={handleUpload}
              disabled={!files || !consent || isUploading}
              className={clsx(
                "w-full h-10 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all",
                isUploading || !files || !consent
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-black text-white hover:bg-gray-800 shadow-sm"
              )}
            >
              {isUploading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Processing...
                </>
              ) : isDone ? (
                <>
                  <Check size={16} />
                  Download Complete
                </>
              ) : (
                "Start Organizing"
              )}
            </button>
          </div>
        </div>

        {/* Footer/Status */}
        {isDone && (
          <div className="mt-6 flex items-center gap-3 text-xs text-gray-500 justify-center animate-in fade-in slide-in-from-top-2">
            <div className="h-1.5 w-1.5 rounded-full bg-green-500" />
            Processed successfully. Zip file downloaded.
          </div>
        )}

        <div className="mt-12 flex justify-center gap-6">
            <div className="flex items-center gap-1.5 text-[10px] text-gray-400 font-medium uppercase tracking-wider">
                <Shield size={10} />
                Zero Data Retention
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-gray-400 font-medium uppercase tracking-wider">
                EU Sovereign
            </div>
        </div>
      </div>
    </main>
  );
}