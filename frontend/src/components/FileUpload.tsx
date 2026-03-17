"use client";

import React, { useState } from "react";
import Image from "next/image";
import axios from "axios";
import { clsx } from "clsx";
import { FileText, Loader2, FolderInput } from "lucide-react";
import ResultsView, {
  AnalysisItem,
  SummaryData,
} from "@/components/ResultsView";

export default function FileUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [analysisData, setAnalysisData] = useState<AnalysisItem[] | null>(null);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
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
        formData,
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

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const items = e.dataTransfer.items;
    if (!items) return;

    const fileEntries: File[] = [];
    const queue: FileSystemEntry[] = [];

    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) queue.push(entry);
    }

    const processEntry = async (entry: FileSystemEntry): Promise<void> => {
      if (entry.isFile) {
        const file = await new Promise<File>((resolve) =>
          (entry as FileSystemFileEntry).file(resolve),
        );
        fileEntries.push(file);
      } else if (entry.isDirectory) {
        const reader = (entry as FileSystemDirectoryEntry).createReader();
        const entries = await new Promise<FileSystemEntry[]>((resolve) =>
          reader.readEntries(resolve),
        );
        for (const child of entries) {
          await processEntry(child);
        }
      }
    };

    for (const entry of queue) {
      await processEntry(entry);
    }

    if (fileEntries.length > 0) {
      setFiles((prev) => [...prev, ...fileEntries]);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setAnalysisData(null);
    setSummaryData(null);
    setZipBase64("");
    setConsent(false);
  };

  if (analysisData) {
    return (
      <ResultsView
        analysis={analysisData}
        summary={summaryData || undefined}
        zipBase64={zipBase64}
        onReset={handleReset}
      />
    );
  }

  return (
    <div className=" flex flex-col gap-4">
      <div
        className={clsx(
          "h-96 bg-blue-50/50 border border-blue-600 border-dashed rounded-2xl hover:bg-blue-600/5 transition-all duration-300 flex flex-col items-center justify-center text-center p-8 group",
          dragActive ? "bg-blue-600/10" : "bg-blue-50/50",
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
          {...({
            webkitdirectory: "",
            directory: "",
          } as React.InputHTMLAttributes<HTMLInputElement>)}
          onChange={(e) => addFiles(e.target.files)}
        />

        <div className="flex flex-col items-center gap-2">
          <div className="relative h-24 w-24">
            <Image
              src="/images/upload-icon.png"
              alt="Upload"
              fill
              className="object-contain group-hover:scale-110 transition-transform duration-500"
            />
          </div>

          <div>
            <p className="text-lg font-semibold text-gray-900 mb-2">
              Drag & drop anything here
            </p>
            <p className="text-sm text-gray-500 mb-6">
              Upload your files here to start organizing
            </p>

            <div className="flex items-center justify-center gap-3">
              <label
                htmlFor="file-upload"
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm font-medium hover:border-blue-600 hover:text-blue-600 transition-all cursor-pointer shadow-sm"
              >
                <FileText size={16} />
                Select Files
              </label>
              <label
                htmlFor="folder-upload"
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm font-medium hover:border-blue-600 hover:text-blue-600 transition-all cursor-pointer shadow-sm"
              >
                <FolderInput size={16} />
                Select Folder
              </label>
            </div>
          </div>

          {files.length > 0 && (
            <div className="mt-2 flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-full text-xs font-bold shadow-md animate-in fade-in zoom-in-95">
              <FileText size={14} />
              {files.length} items staged
            </div>
          )}
        </div>
      </div>
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          id="consent"
          className="mt-0.5 rounded border-white/20 bg-white/5 text-white focus:ring-white/30 accent-white"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
        />
        <label
          htmlFor="consent"
          className="text-[11px] leading-relaxed cursor-pointer select-none"
        >
          I have read and agree to the{" "}
          <a
            href="/privacy"
            target="_blank"
            className="underline hover:text-white font-bold transition-colors"
          >
            Privacy Policy
          </a>
          , and I understand that my data will be processed by AI subprocessors
          hosted in the EU.
        </label>
      </div>
      <button
        onClick={handleUpload}
        disabled={files.length === 0 || !consent || isUploading}
        className={clsx(
          "w-full h-12 rounded-2xl text-sm font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-all duration-300",
          isUploading || files.length === 0 || !consent
            ? "bg-[#4A80A6]/10 text-[#4A80A6]/10 cursor-not-allowed border border-white/5"
            : "bg-[#4A80A6] text-white hover:bg-[#4A80A6]/80 active:scale-[0.98] shadow-[0_0_20px_rgba(255,255,255,0.3)]",
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
  );
}
