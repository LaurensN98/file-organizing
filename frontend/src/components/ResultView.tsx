"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import Image from "next/image";
import {
  FileText,
  Search,
  ChevronRight,
  Download,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import { clsx } from "clsx";
import { motion, AnimatePresence } from "framer-motion";
import ClusterMap from "@/components/ClusterMap";
import { MapSkeleton } from "@/components/ResultSkeleton";

export interface AnalysisItem {
  id: string;
  filename: string;
  folder: string;
  x: number;
  y: number;
  metadata: {
    file_size_kb: number;
    file_type: string;
    page_count?: number;
    language?: string;
    // New LLM Fields
    summary?: string;
    suggested_filename?: string;
    document_type?: string;
    tags?: string[];
  };
}

export interface SummaryData {
  total_files: number;
  total_size_kb: number;
  avg_size_kb: number;
  largest_file_kb: number;
  processing_time_sec: number;
  cluster_count: number;
  description: string;
}

interface ResultViewProps {
  batchId: string;
  initialAnalysis?: AnalysisItem[];
  initialSummary?: SummaryData | null;
  serverZip?: string;
  initialStatus?: string;
}

export default function ResultView({
  batchId,
  initialAnalysis = [],
  initialSummary = null,
  serverZip = "",
  initialStatus = "PENDING",
}: ResultViewProps) {
  const router = useRouter();
  const [status, setStatus] = useState(initialStatus);
  const [analysis, setAnalysis] = useState<AnalysisItem[]>(initialAnalysis);
  const [summary, setSummary] = useState<SummaryData | null>(initialSummary);
  const [zip, setZip] = useState(serverZip || "");
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [vectorResultScores, setVectorResultScores] = useState<Record<
    string,
    number
  > | null>(null);
  const [hoveredFileId, setHoveredFileId] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<
    Record<string, boolean>
  >({});

  const fetchResults = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await axios.get(`${apiUrl}/api/results/${batchId}`);
      const data = response.data;

      setStatus(data.status);
      if (data.status === "SUCCESS") {
        setAnalysis(data.analysis);
        setSummary(data.summary);
        setZip(data.zip_file);
      } else if (data.status === "FAILED") {
        setError(data.error || "Analysis failed. Please try again.");
      }
    } catch (err) {
      console.error("Polling error:", err);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (status === "PENDING" || status === "PROCESSING") {
      fetchResults(); // Fetch immediately
      interval = setInterval(fetchResults, 2000); // And then poll
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [status, batchId]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setVectorResultScores(null);
      return;
    }

    setIsSearching(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await axios.post(`${apiUrl}/api/vector-search`, null, {
        params: { query: searchQuery, limit: 25, batch_id: batchId },
      });
      // The endpoint returns a list of {id, filename, folder, score}
      const scoreMap: Record<string, number> = {};
      response.data.forEach((res: { id: string; score: number }) => {
        scoreMap[res.id] = res.score;
      });
      setVectorResultScores(scoreMap);
    } catch (err) {
      console.error("Vector search failed:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  useEffect(() => {
    // Auto-expand the first folder found in the dataset
    if (
      analysis &&
      analysis.length > 0 &&
      Object.keys(expandedFolders).length === 0
    ) {
      const firstFolder = analysis[0].folder;
      setExpandedFolders({ [firstFolder]: true });
    }
  }, [analysis, expandedFolders]);

  const formatMB = (kb: number) => Math.round((kb / 1024) * 10) / 10;

  const handleDownload = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const url = `${apiUrl}/api/download/${batchId}`;
    const link = document.createElement("a");
    link.href = url;
    link.download = "organized_documents.zip";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // --- LOADING / ERROR STATES ---

  if (status === "FAILED") {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center mb-6">
          <Image
            src="/images/neural.png"
            alt="Error"
            width={40}
            height={40}
            className="grayscale brightness-50 contrast-200"
          />
        </div>
        <h2 className="text-2xl font-bold text-[#203047] mb-2">
          Organization Failed
        </h2>
        <p className="text-red-500/70 max-w-sm mb-8">{error}</p>
        <button
          onClick={() => router.push("/")}
          className="bg-white border border-gray-200 px-6 py-3 rounded-2xl font-bold text-sm hover:border-blue-600 hover:text-blue-600 transition-all shadow-sm"
        >
          Try Again
        </button>
      </div>
    );
  }

  // --- SUCCESS STATE ---

  const filteredAnalysis = [...analysis]
    .filter((item) => {
      // If we have vector search results, filter by the score map keys
      if (vectorResultScores !== null) {
        return item.id in vectorResultScores;
      }

      // Default: client-side text filtering
      const query = searchQuery.toLowerCase();
      return (
        item.filename.toLowerCase().includes(query) ||
        item.folder.toLowerCase().includes(query)
      );
    })
    .sort((a, b) => {
      // If we have vector search scores, sort by score descending
      if (vectorResultScores !== null) {
        return (
          (vectorResultScores[b.id] || 0) - (vectorResultScores[a.id] || 0)
        );
      }
      return 0; // Maintain original order otherwise
    });

  const groupedFiles = filteredAnalysis.reduce(
    (acc, item) => {
      if (!acc[item.folder]) acc[item.folder] = [];
      acc[item.folder].push(item);
      return acc;
    },
    {} as Record<string, AnalysisItem[]>,
  );

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
          <div>
            <div className="flex items-center gap-3 text-gray-400 text-sm font-medium mb-4">
              <button
                onClick={() => router.push("/")}
                className="flex items-center gap-1 hover:text-blue-600 transition-colors"
              >
                <ArrowLeft size={16} /> Dashboard
              </button>
              <span>/</span>
              <span className="text-gray-900">Analysis Results</span>
            </div>
            <div className="flex items-center gap-3 mb-4">
              <h1 className="text-4xl font-bold text-[#203047]">
                Smart Report
              </h1>
            </div>
            <p className="text-gray-500 max-w-2xl leading-relaxed">
              {status === "PROCESSING"
                ? "Our AI is currently clustering your documents and generating semantic labels. Results will appear live below."
                : summary?.description ||
                  "Detailed results and semantic classification of your uploaded documents."}
            </p>
          </div>

          <button
            onClick={handleDownload}
            className="flex items-center gap-3 bg-gradient-primary text-sm text-white px-4 py-2.5 rounded-2xl font-semibold hover:bg-[#3A7096] transition-all  active:scale-95 whitespace-nowrap"
          >
            <Download size={16} />
            Download ZIP
          </button>
        </div>
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {!summary
            ? [1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="bg-white p-5 rounded-3xl border border-gray-100 shadow-sm flex flex-col gap-2 animate-pulse"
                >
                  <div className="w-8 h-8 bg-gray-100 rounded-lg mb-2" />
                  <div className="h-8 w-20 bg-gray-200 rounded" />
                  <div className="h-3 w-16 bg-gray-100 rounded" />
                </div>
              ))
            : [
                {
                  label: "Total Files",
                  value: summary.total_files,
                  icon: (
                    <Image
                      src="/images/paper-sizes.png"
                      alt="Total Files"
                      width={18}
                      height={18}
                      className="w-6"
                    />
                  ),
                },
                {
                  label: "Total Size",
                  value: `${formatMB(summary.total_size_kb)} MB`,
                  icon: (
                    <Image
                      src="/images/folder.png"
                      alt="Total Size"
                      width={18}
                      height={18}
                      className="w-6"
                    />
                  ),
                },
                {
                  label: "Clusters",
                  value: summary.cluster_count,
                  icon: (
                    <Image
                      src="/images/neural.png"
                      alt="Clusters"
                      width={18}
                      height={18}
                      className="w-6"
                    />
                  ),
                },
                {
                  label: "Process Time",
                  value: `${summary.processing_time_sec}s`,
                  icon: (
                    <Image
                      src="/images/hour-glass.png"
                      alt="Process Time"
                      width={18}
                      height={18}
                      className="w-6"
                    />
                  ),
                },
              ].map((stat, i) => (
                <div
                  key={i}
                  className="bg-white p-5 rounded-3xl border border-gray-100 shadow-sm flex flex-col gap-1"
                >
                  <div className="text-[#4A80A6] mb-2">{stat.icon}</div>
                  <div className="text-2xl font-bold text-[#203047]">
                    {stat.value}
                  </div>
                  <div className="text-[11px] text-gray-400 font-bold uppercase tracking-wider">
                    {stat.label}
                  </div>
                </div>
              ))}
        </div>

        {/* Semantic Map Visualization */}
        <div className="mb-8 relative">
          {analysis.length > 0 ? (
            <ClusterMap
              analysis={filteredAnalysis}
              highlightedId={hoveredFileId}
            />
          ) : (
            <MapSkeleton />
          )}
        </div>

        <div className="mb-8 flex items-center">
          <div className="relative flex-1">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
              size={20}
            />
            <input
              type="text"
              placeholder="Search through organized files..."
              className="w-full pl-12 pr-4 py-3 bg-white border border-gray-100 shadow-sm rounded-2xl outline-none focus:outline-none focus:border-[#4A80A6]/50 focus:ring-4 focus:ring-[#4A80A6]/10 transition-all"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if (!e.target.value.trim()) setVectorResultScores(null);
              }}
              onKeyDown={handleKeyDown}
              disabled={isSearching}
            />
            {isSearching && (
              <div className="absolute right-4 top-1/2 -translate-y-1/2">
                <Loader2 className="animate-spin text-blue-600" size={16} />
              </div>
            )}
          </div>
        </div>
        {!vectorResultScores && (
          <p className="text-[11px] text-gray-400 mt-[-24px] mb-8 ml-2 flex items-center gap-1.5 animate-in fade-in slide-in-from-top-1 duration-700">
            <Search size={12} className="opacity-50" />
            Tip: Press{" "}
            <kbd className="bg-gray-100 px-1 rounded border border-gray-200 font-sans">
              Enter
            </kbd>{" "}
            to unlock semantic hybrid search across all your documents.
          </p>
        )}

        <div className="grid grid-cols-1 gap-8">
          {status === "PROCESSING" && analysis.length === 0 ? (
            /* Folders Skeleton List */
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-white rounded-3xl p-6 border border-gray-100 shadow-sm animate-pulse"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-gray-100 rounded-2xl" />
                      <div>
                        <div className="h-5 w-48 bg-gray-200 rounded mb-2" />
                        <div className="h-3 w-24 bg-gray-100 rounded" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredAnalysis.length === 0 ? (
            <div className="bg-white rounded-3xl p-20 text-center border-2 border-dashed border-gray-100 text-gray-400">
              {status === "PROCESSING" || status === "PENDING"
                ? "Starting analysis..."
                : "No files found matching your search."}
            </div>
          ) : vectorResultScores !== null ? (
            /* Flat List for Vector Search */
            <div className="space-y-2">
              <div className="flex items-center justify-between mb-4 px-2">
                <h2 className="text-lg font-bold text-[#203047]">
                  Search Results
                </h2>
                <span className="text-xs text-gray-400 font-medium">
                  Sorted by relevance
                </span>
              </div>
              {filteredAnalysis.map((doc) => (
                <div key={doc.id} className="relative group/file">
                  <div
                    className="flex items-center justify-between p-2.5 bg-white rounded-xl border border-gray-100 group transition-all hover:border-blue-200 hover:shadow-sm"
                    onMouseEnter={() => setHoveredFileId(doc.id)}
                    onMouseLeave={() => setHoveredFileId(null)}
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <Image
                        src="/images/document.png"
                        alt="Doc"
                        width={18}
                        height={18}
                        className="w-6"
                      />
                      <span className="text-sm text-gray-700 truncate font-medium">
                        {doc.filename}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 ml-4">
                      <span className="text-[10px] uppercase bg-gray-100 px-2 py-0.5 rounded-full font-bold text-gray-500">
                        {doc.metadata.file_type}
                      </span>
                      <span className="text-[10px] text-gray-400 font-medium whitespace-nowrap">
                        {doc.metadata.file_size_kb} KB
                      </span>
                    </div>
                  </div>

                  {/* Tooltip Overlay */}
                  <AnimatePresence>
                    {hoveredFileId === doc.id && doc.metadata.summary && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 5 }}
                        className="absolute z-[100] bottom-full left-0 mb-3 w-[340px] bg-white text-[#203047] p-5 rounded-[24px] shadow-2xl border border-gray-100 pointer-events-none origin-bottom-left"
                      >
                        <div className="flex items-center gap-2 mb-4">
                          <div className="w-2 h-2 rounded-full bg-[#4A80A6]" />
                          <span className="text-[10px] uppercase tracking-widest font-black text-[#4A80A6]/60">
                            AI Metadata Insight
                          </span>
                        </div>

                        {doc.metadata.suggested_filename && (
                          <div className="mb-4">
                            <span className="text-[11px] text-gray-400 block mb-1">
                              Proposed Filename
                            </span>
                            <span className="text-xs font-bold text-[#4A80A6] break-all leading-tight">
                              {doc.metadata.suggested_filename}
                            </span>
                          </div>
                        )}

                        {doc.metadata.document_type && (
                          <div className="mb-4">
                            <span className="text-[11px] text-gray-400 block mb-1">
                              Classification
                            </span>
                            <span className="text-xs font-bold bg-gray-50 text-gray-600 px-2 py-1 rounded-lg border border-gray-100">
                              {doc.metadata.document_type}
                            </span>
                          </div>
                        )}

                        <div className="mb-4">
                          <span className="text-[11px] text-gray-400 block mb-1.5">
                            AI Summary
                          </span>
                          <p className="text-xs leading-relaxed text-gray-600 font-medium italic">
                            &ldquo;{doc.metadata.summary}&rdquo;
                          </p>
                        </div>

                        {doc.metadata.tags && doc.metadata.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-3 border-t border-gray-50">
                            {doc.metadata.tags.map((tag) => (
                              <span
                                key={tag}
                                className="text-[9px] font-bold text-[#4A80A6]/70 bg-[#4A80A6]/5 px-2 py-0.5 rounded-md"
                              >
                                #{tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          ) : (
            /* Grouped View for Normal Exploration */
            <div className="space-y-4">
              {Object.entries(groupedFiles).map(([folder, folderFiles]) => (
                <div
                  key={folder}
                  className={clsx(
                    "bg-white rounded-3xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow relative",
                    hoveredFileId ? "!overflow-visible" : "overflow-hidden",
                  )}
                >
                  <button
                    onClick={() =>
                      setExpandedFolders((p) => ({
                        ...p,
                        [folder]: !p[folder],
                      }))
                    }
                    className="w-full flex items-center justify-between px-6 py-6 hover:bg-gray-50 transition-colors rounded-t-3xl"
                  >
                    <div className="flex items-center gap-4 text-left">
                      <div className="w-10 h-10 flex items-center justify-center shrink-0">
                        <Image
                          src="/images/folder.png"
                          alt="Folder Icon"
                          width={40}
                          height={40}
                          className="opacity-90"
                        />
                      </div>
                      <div>
                        <h3 className="font-bold text-[#203047] text-md">
                          {folder}
                        </h3>
                        <p className="text-xs text-gray-500">
                          Contains {folderFiles.length} files
                        </p>
                      </div>
                    </div>
                    <ChevronRight
                      size={20}
                      className={clsx(
                        "text-gray-400 transition-transform duration-300",
                        expandedFolders[folder] && "rotate-90",
                      )}
                    />
                  </button>

                  <AnimatePresence>
                    {expandedFolders[folder] && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{
                          height: { duration: 0.4, ease: [0.4, 0, 0.2, 1] },
                          opacity: { duration: 0.25, delay: 0.05 },
                        }}
                        className={clsx(
                          hoveredFileId
                            ? "overflow-visible"
                            : "overflow-hidden",
                        )}
                      >
                        <div className="px-6 pb-8 pt-4 space-y-3 bg-gray-50/40 border-t border-gray-100/50">
                          {folderFiles.map((file, idx) => (
                            <div key={idx} className="relative group/file">
                              <div
                                className="flex items-center justify-between p-2.5 bg-white rounded-2xl border border-gray-100 group transition-all hover:border-[#4A80A6]/30 hover:shadow-md hover:shadow-blue-500/5"
                                onMouseEnter={() => setHoveredFileId(file.id)}
                                onMouseLeave={() => setHoveredFileId(null)}
                              >
                                <div className="flex items-center gap-4 overflow-hidden">
                                  <div className="flex items-center justify-center rounded-lg transition-colors">
                                    <Image
                                      src="/images/document.png"
                                      alt="Doc"
                                      width={18}
                                      height={18}
                                      className="w-6 h-6 opacity-80"
                                    />
                                  </div>
                                  <span className="text-sm text-[#203047]/90 truncate font-semibold">
                                    {file.filename}
                                  </span>
                                </div>
                                <div className="flex items-center gap-3 shrink-0 ml-4">
                                  <span className="text-[10px] uppercase bg-gray-100 text-gray-500 px-2 py-0.5 rounded-md font-black tracking-tight border border-gray-200/50">
                                    {file.metadata.file_type}
                                  </span>
                                  <span className="text-[10px] text-gray-400 font-bold whitespace-nowrap">
                                    {file.metadata.file_size_kb} KB
                                  </span>
                                </div>
                              </div>

                              {/* Tooltip Overlay */}
                              <AnimatePresence>
                                {hoveredFileId === file.id &&
                                  file.metadata.summary && (
                                    <motion.div
                                      initial={{
                                        opacity: 0,
                                        scale: 0.95,
                                        y: 10,
                                      }}
                                      animate={{ opacity: 1, scale: 1, y: 0 }}
                                      exit={{ opacity: 0, scale: 0.95, y: 5 }}
                                      className="absolute z-[100] bottom-full left-0 mb-3 w-[340px] bg-white text-[#203047] p-5 rounded-[24px] shadow-2xl border border-gray-100 pointer-events-none origin-bottom-left"
                                    >
                                      <div className="flex items-center gap-2 mb-4">
                                        <div className="w-2 h-2 rounded-full bg-[#4A80A6]" />
                                        <span className="text-[10px] uppercase tracking-widest font-black text-[#4A80A6]/60">
                                          AI Metadata Insight
                                        </span>
                                      </div>

                                      {file.metadata.suggested_filename && (
                                        <div className="mb-4">
                                          <span className="text-[11px] text-gray-400 block mb-1">
                                            Proposed Filename
                                          </span>
                                          <span className="text-sm font-bold text-[#4A80A6] break-all leading-tight">
                                            {file.metadata.suggested_filename}
                                          </span>
                                        </div>
                                      )}

                                      {file.metadata.document_type && (
                                        <div className="mb-4">
                                          <span className="text-[11px] text-gray-400 block mb-1">
                                            Classification
                                          </span>
                                          <span className="text-xs font-bold bg-gray-50 text-gray-600 px-2 py-1 rounded-lg border border-gray-100">
                                            {file.metadata.document_type}
                                          </span>
                                        </div>
                                      )}

                                      <div className="mb-4">
                                        <span className="text-[11px] text-gray-400 block mb-1.5">
                                          AI Summary
                                        </span>
                                        <p className="text-xs leading-relaxed text-gray-600 font-medium italic">
                                          &ldquo;{file.metadata.summary}&rdquo;
                                        </p>
                                      </div>

                                      {file.metadata.tags &&
                                        file.metadata.tags.length > 0 && (
                                          <div className="flex flex-wrap gap-1.5 pt-3 border-t border-gray-50">
                                            {file.metadata.tags.map((tag) => (
                                              <span
                                                key={tag}
                                                className="text-[9px] font-bold text-[#4A80A6]/70 bg-[#4A80A6]/5 px-2 py-0.5 rounded-md"
                                              >
                                                #{tag}
                                              </span>
                                            ))}
                                          </div>
                                        )}
                                    </motion.div>
                                  )}
                              </AnimatePresence>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
