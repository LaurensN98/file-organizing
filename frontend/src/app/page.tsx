"use client";

import React, { useState } from "react";
import { Upload, Shield, FileText, Check, Loader2, FolderOpen, FolderInput } from "lucide-react";
import axios from "axios";
import { clsx } from "clsx";
import ResultsView from "@/components/ResultsView";

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [zipBase64, setZipBase64] = useState<string>("");
  const [consent, setConsent] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleUpload = async () => {
    if (files.length === 0 || !consent) return;

    setIsUploading(true);
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file, file.webkitRelativePath || file.name);
    });

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/upload`,
        formData
      );

      // Store analysis, summary, and zip
      setAnalysisData(response.data.analysis);
      setSummaryData(response.data.summary);
      setZipBase64(response.data.zip_file);
      
    } catch (error) {
      console.error("Upload failed", error);
      alert("Something went wrong. Please check your connection.");
    } finally {
      setIsUploading(false);
    }
  };

  const addFiles = (newFiles: FileList | null) => {
    if (newFiles) {
      setFiles((prev) => [...prev, ...Array.from(newFiles)]);
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
      addFiles(e.dataTransfer.files);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setAnalysisData(null);
    setSummaryData(null);
    setZipBase64("");
    setConsent(false);
  };

  return (
    <main className="relative min-h-screen flex items-center justify-center p-6 overflow-hidden bg-[#0A0A0A]">
      {/* Full Screen Background with Blur */}
      <div className="absolute inset-0 z-0">
        <img 
          src="/images/backdrop.webp" 
          alt="Background" 
          className="w-full h-full object-cover opacity-40 blur-[1px] scale-105"
        />
      </div>

      <div className="relative z-10 w-full max-w-4xl animate-in fade-in zoom-in-95 duration-500 flex flex-col items-center">
        
        {/* Header - White text for better contrast against darker-balanced bg */}
        {!analysisData && (
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold tracking-tight text-white mb-1">
              DocuSort
            </h1>
            <p className="text-sm font-medium text-white/70">
              Intelligent organization for your unstructured documents.
            </p>
          </div>
        )}

        {analysisData ? (
          <ResultsView 
            analysis={analysisData} 
            summary={summaryData}
            zipBase64={zipBase64} 
            onReset={handleReset} 
          />
        ) : (
          /* Glassmorphism Card */
          <div className="w-full max-w-md bg-white/20 backdrop-blur-md rounded-3xl shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] border border-white/30 overflow-hidden animate-in fade-in zoom-in-95 duration-700">
            <div 
              className={clsx(
                "p-10 transition-colors duration-200 ease-in-out border-b border-white/10 flex flex-col items-center",
                dragActive ? "bg-white/10" : "bg-transparent"
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
                onChange={(e) => addFiles(e.target.files)}
              />
              <input
                type="file"
                className="hidden"
                id="folder-upload"
                {...{ webkitdirectory: "", directory: "" } as any}
                onChange={(e) => addFiles(e.target.files)}
              />
              
              <div className="flex gap-10 w-full justify-center">
                <label 
                  htmlFor="file-upload" 
                  className="flex flex-col items-center justify-center cursor-pointer group flex-1"
                >
                  <div className="mb-4 h-14 w-14 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center group-hover:bg-white group-hover:text-black transition-all duration-500 border border-white/20">
                    <Upload size={24} className="text-white/80 group-hover:text-black" />
                  </div>
                  <p className="text-xs font-bold text-white/90 uppercase tracking-widest group-hover:text-white transition-colors">
                    Files
                  </p>
                </label>

                <div className="w-px bg-white/10 self-stretch my-2" />

                <label 
                  htmlFor="folder-upload" 
                  className="flex flex-col items-center justify-center cursor-pointer group flex-1"
                >
                  <div className="mb-4 h-14 w-14 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center group-hover:bg-white group-hover:text-black transition-all duration-500 border border-white/20">
                    <FolderInput size={24} className="text-white/80 group-hover:text-black" />
                  </div>
                  <p className="text-xs font-bold text-white/90 uppercase tracking-widest group-hover:text-white transition-colors">
                    Folder
                  </p>
                </label>
              </div>

              {files.length > 0 && (
                <div className="mt-8 flex items-center justify-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md text-white rounded-full text-[11px] font-bold w-fit mx-auto border border-white/20 shadow-xl">
                  <FileText size={14} />
                  {files.length} items selected
                </div>
              )}
            </div>

            <div className="p-8 bg-black/10 backdrop-blur-md">
              <div className="flex items-start gap-3 mb-8">
                <input
                  type="checkbox"
                  id="consent"
                  className="mt-1 rounded border-white/20 bg-white/5 text-white focus:ring-white/30 accent-white"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                <label htmlFor="consent" className="text-[11px] text-white/70 leading-relaxed cursor-pointer select-none">
                  I have read and agree to the <a href="/privacy" target="_blank" className="underline hover:text-white font-bold transition-colors">Privacy Policy</a>, and I understand that my data will be processed by AI subprocessors hosted in the EU.
                </label>
              </div>

              <button
                onClick={handleUpload}
                disabled={files.length === 0 || !consent || isUploading}
                className={clsx(
                  "w-full h-12 rounded-2xl text-sm font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-all duration-500",
                  isUploading || files.length === 0 || !consent
                    ? "bg-white/5 text-white/20 cursor-not-allowed border border-white/5"
                    : "bg-white text-black hover:bg-white/90 hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                )}
              >
                {isUploading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Processing
                  </>
                ) : (
                  "Organize Files"
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}