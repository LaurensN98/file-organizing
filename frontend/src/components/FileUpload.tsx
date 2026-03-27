"use client";

import React, { useState } from "react";
import Image from "next/image";
import axios from "axios";
import { clsx } from "clsx";
import { useRouter } from "next/navigation";
import { FileText, Loader2, FolderInput } from "lucide-react";

export default function FileUpload() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [consent, setConsent] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  // Helper to filter out system files
  const isSystemFile = (filename: string) => {
    return filename.includes(".DS_Store") || 
           filename.includes("__MACOSX") || 
           filename.startsWith(".");
  };

  const handleUpload = async () => {
    if (files.length === 0 || !consent) return;

    setIsUploading(true);
    setUploadProgress(0);
    console.log(`🚀 Starting upload of ${files.length} files...`);
    
    const formData = new FormData();
    files.forEach((file) => {
      // Use webkitRelativePath if available, otherwise just the name
      const path = file.webkitRelativePath || file.name;
      formData.append("files", file, path);
    });

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await axios.post(`${apiUrl}/api/upload`, formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          }
        }
      });
      
      console.log("✅ Upload successful! Batch ID:", response.data.batch_id);
      
      // Navigate to the dynamic persistent results page
      router.push(`/result/${response.data.batch_id}`);
    } catch (error) {
      console.error("❌ Upload failed", error);
      alert("Something went wrong with the upload. Please check your connection or try fewer files.");
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    
    const validFiles = Array.from(newFiles).filter(f => !isSystemFile(f.name));
    console.log(`Staging ${validFiles.length} files from input...`);
    setFiles((prev) => [...prev, ...validFiles]);
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

    console.log("📂 processing drop...");
    const fileEntries: File[] = [];

    // Recursive function to correctly read all files in all subdirectories
    const readAllFiles = async (entry: FileSystemEntry, path: string = ""): Promise<void> => {
      if (entry.isFile) {
        const file = await new Promise<File>((resolve) =>
          (entry as FileSystemFileEntry).file(resolve),
        );
        
        if (!isSystemFile(file.name)) {
          fileEntries.push(file);
        }
      } else if (entry.isDirectory) {
        const reader = (entry as FileSystemDirectoryEntry).createReader();
        
        const readEntries = async (): Promise<FileSystemEntry[]> => {
          return new Promise((resolve) => {
            reader.readEntries(resolve);
          });
        };

        let entries = await readEntries();
        while (entries.length > 0) {
          for (const child of entries) {
            await readAllFiles(child, `${path}${entry.name}/`);
          }
          entries = await readEntries();
        }
      }
    };

    const tasks: Promise<void>[] = [];
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) {
        tasks.push(readAllFiles(entry));
      }
    }

    await Promise.all(tasks);
    console.log(`Staged ${fileEntries.length} files from drop.`);
    if (fileEntries.length > 0) {
      setFiles((prev) => [...prev, ...fileEntries]);
    }
  };

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
          // @ts-expect-error - directory and webkitdirectory are standard but sometimes miss types
          webkitdirectory=""
          directory=""
          onChange={(e) => addFiles(e.target.files)}
        />

        <div className="flex flex-col items-center gap-2">
          <div className="relative h-24 w-24">
            <Image
              src="/images/upload-icon.png"
              alt="Upload"
              fill
              sizes="96px"
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
            <div className="mt-4 flex flex-col items-center gap-2">
              <div className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-full text-[10px] font-bold shadow-md">
                <FileText size={12} />
                {files.length} ITEMS READY
              </div>
              <button 
                onClick={() => setFiles([])}
                className="text-[10px] text-gray-400 hover:text-red-500 font-bold uppercase tracking-wider transition-colors"
                type="button"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      </div>
      
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          id="consent"
          className="mt-0.5 rounded border-gray-300 text-[#4A80A6] focus:ring-[#4A80A6]"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
        />
        <label
          htmlFor="consent"
          className="text-[11px] leading-relaxed cursor-pointer select-none text-gray-600"
        >
          I have read and agree to the{" "}
          <a
            href="/privacy"
            target="_blank"
            className="underline hover:text-[#4A80A6] font-bold transition-colors text-gray-900"
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
        type="button"
        className={clsx(
          "relative w-full h-12 rounded-2xl text-sm font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-all duration-300 overflow-hidden",
          isUploading || files.length === 0 || !consent
            ? "bg-gray-100 text-gray-400 cursor-not-allowed"
            : "bg-[#4A80A6] text-white hover:bg-[#3A7096] active:scale-[0.98] shadow-lg shadow-[#4A80A6]/20",
        )}
      >
        {/* Progress Bar Background fill */}
        {isUploading && uploadProgress > 0 && (
          <div 
            className="absolute left-0 top-0 h-full bg-[#4A80A6]/20 transition-all duration-300" 
            style={{ width: `${uploadProgress}%` }}
          />
        )}
        
        <div className="relative z-10 flex items-center gap-2">
          {isUploading ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              {uploadProgress < 100 ? `Uploading... ${uploadProgress}%` : "Organizing..."}
            </>
          ) : (
            "Start Organization"
          )}
        </div>
      </button>
    </div>
  );
}
