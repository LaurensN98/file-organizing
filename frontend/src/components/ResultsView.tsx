"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, ZAxis, Cell } from "recharts";
import { Download, FileText, ArrowLeft, Database, HardDrive, Move, Activity, Layers } from "lucide-react";

// ... (Interfaces and COLORS constant remain the same) ...
interface AnalysisItem {
  filename: string;
  folder: string;
  x: number;
  y: number;
  metadata: {
    file_size_kb: number;
    file_type: string;
    page_count?: number;
    language?: string;
  };
}

interface SummaryData {
  total_files: number;
  total_size_kb: number;
  avg_size_kb: number;
  largest_file_kb: number;
  processing_time_sec: number;
  cluster_count: number;
  description: string;
}

interface ResultsViewProps {
  analysis: AnalysisItem[];
  summary?: SummaryData;
  zipBase64: string;
  onReset: () => void;
}

const COLORS = [
  "#2563eb", "#db2777", "#ea580c", "#65a30d", "#16a34a", 
  "#0891b2", "#7c3aed", "#9333ea", "#4f46e5", "#dc2626"
];


const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white/95 backdrop-blur-xl p-3 border border-white/20 rounded-xl shadow-2xl text-xs z-50">
        <p className="font-semibold text-gray-900 mb-1">{data.filename}</p>
        <div className="space-y-1 text-gray-500">
          <p className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: data.fill }} />
            {data.folder}
          </p>
          <div className="flex gap-3 mt-2 pt-2 border-t border-gray-100">
            <span className="flex items-center gap-1"><HardDrive size={10} /> {data.metadata.file_size_kb} KB</span>
            <span className="uppercase bg-gray-100 px-1.5 py-0.5 rounded text-[9px] font-medium">{data.metadata.file_type}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function ResultsView({ analysis, summary, zipBase64, onReset }: ResultsViewProps) {
  const [zoom, setZoom] = useState(1);
  const [center, setCenter] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });
  const chartContainerRef = useRef<HTMLDivElement>(null);

  const handleDownload = () => {
    const byteCharacters = atob(zipBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: "application/zip" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "organized_documents.zip";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const clusters = useMemo(() => Array.from(new Set(analysis.map(a => a.folder))), [analysis]);
  const clusterColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    clusters.forEach((folder, i) => {
      map[folder] = COLORS[i % COLORS.length];
    });
    return map;
  }, [clusters]);

  const data = useMemo(() => {
    let rawData = analysis.map((item, index) => ({
      ...item,
      id: index,
      fill: clusterColorMap[item.folder]
    }));
    const MAX_POINTS = 800;
    if (rawData.length > MAX_POINTS) {
      const stride = Math.ceil(rawData.length / MAX_POINTS);
      return rawData.filter((_, i) => i % stride === 0);
    }
    return rawData;
  }, [analysis, clusterColorMap]);

  const { baseRangeX, baseRangeY, midX, midY } = useMemo(() => {
    if (data.length === 0) return { baseRangeX: 2, baseRangeY: 2, midX: 0, midY: 0 };
    const allX = data.map(d => d.x);
    const allY = data.map(d => d.y);
    const minDataX = Math.min(...allX);
    const maxDataX = Math.max(...allX);
    const minDataY = Math.min(...allY);
    const maxDataY = Math.max(...allY);
    const paddingX = (maxDataX - minDataX) * 0.1 || 1;
    const paddingY = (maxDataY - minDataY) * 0.1 || 1;
    const baseMinX = minDataX - paddingX;
    const baseMaxX = maxDataX + paddingX;
    const baseMinY = minDataY - paddingY;
    const baseMaxY = maxDataY + paddingY;
    return {
      baseRangeX: baseMaxX - baseMinX,
      baseRangeY: baseMaxY - baseMinY,
      midX: (baseMaxX + baseMinX) / 2,
      midY: (baseMaxY + baseMinY) / 2,
    };
  }, [data]);

  const currentRangeX = baseRangeX / zoom;
  const currentRangeY = baseRangeY / zoom;

  const currentDomainX = [midX + center.x - currentRangeX / 2, midX + center.x + currentRangeX / 2];
  const currentDomainY = [midY + center.y - currentRangeY / 2, midY + center.y + currentRangeY / 2];

  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const zoomSensitivity = 0.001;
      const delta = -e.deltaY * zoomSensitivity;
      const rect = container.getBoundingClientRect();
      const containerWidth = rect.width;
      const containerHeight = rect.height;
      const ratioX = (e.clientX - rect.left) / containerWidth;
      const ratioY = (e.clientY - rect.top) / containerHeight;
      
      setZoom(prevZoom => {
        const newZoom = Math.min(Math.max(prevZoom + delta * prevZoom, 0.5), 20);
        if (newZoom !== prevZoom) {
          const scaleChange = 1 / prevZoom - 1 / newZoom;
          setCenter(prev => ({
            x: prev.x + (ratioX - 0.5) * baseRangeX * scaleChange,
            y: prev.y - (ratioY - 0.5) * baseRangeY * scaleChange,
          }));
        }
        return newZoom;
      });
    };

    container.addEventListener('wheel', onWheel, { passive: false });
    return () => container.removeEventListener('wheel', onWheel);
  }, [baseRangeX, baseRangeY]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setStartPan({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const dxPx = e.clientX - startPan.x;
      const dyPx = e.clientY - startPan.y;
      const domainPerPixelX = currentRangeX / chartContainerRef.current!.clientWidth;
      const domainPerPixelY = currentRangeY / chartContainerRef.current!.clientHeight;
      setCenter(prev => ({
        x: prev.x - dxPx * domainPerPixelX,
        y: prev.y + dyPx * domainPerPixelY
      }));
      setStartPan({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => setIsDragging(false);
  
  const totalFiles = summary?.total_files || analysis.length;
  const totalClusters = summary?.cluster_count || clusters.length;

  return (
    <div className="w-full max-w-6xl animate-in fade-in slide-in-from-bottom-4 duration-700 flex flex-col gap-6">
      <div className="flex justify-between items-end text-white">
        <div>
          <button 
            onClick={onReset}
            className="flex items-center gap-2 text-white/70 hover:text-white text-xs font-medium mb-2 transition-colors"
          >
            <ArrowLeft size={14} />
            Analyze New Batch
          </button>
          <h2 className="text-2xl font-bold tracking-tight">Analysis Complete</h2>
          <p className="text-white/70 text-sm">
            Organized {totalFiles} documents into {totalClusters} intelligent clusters.
          </p>
        </div>
        <button
          onClick={handleDownload}
          className="bg-white text-black hover:bg-white/90 px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 shadow-lg transition-all"
        >
          <Download size={16} />
          Download Zip
        </button>
      </div>

      {summary && (
        <div className="bg-white/20 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] border border-white/10 p-6 flex flex-col md:flex-row gap-6 text-white">
          <div className="flex-1">
            <h3 className="font-semibold mb-2 flex items-center gap-2 text-sm text-white/90">
              <Activity size={16} className="text-blue-200" />
              Dataset Summary
            </h3>
            <p className="text-sm text-white/80 leading-relaxed">
              {summary.description}
            </p>
          </div>
          <div className="flex gap-8 border-t md:border-t-0 md:border-l border-white/10 pt-4 md:pt-0 md:pl-8">
            <div>
              <p className="text-[10px] text-white/50 uppercase font-bold tracking-wider mb-1">Total Size</p>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold">{Math.round(summary.total_size_kb / 1024 * 10) / 10}</span>
                <span className="text-xs text-white/60">MB</span>
              </div>
            </div>
            <div>
              <p className="text-[10px] text-white/50 uppercase font-bold tracking-wider mb-1">Avg File</p>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold">{summary.avg_size_kb}</span>
                <span className="text-xs text-white/60">KB</span>
              </div>
            </div>
            <div>
              <p className="text-[10px] text-white/50 uppercase font-bold tracking-wider mb-1">Time</p>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold">{summary.processing_time_sec}</span>
                <span className="text-xs text-white/60">s</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
        <div className="lg:col-span-2 bg-white/20 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] border border-white/10 p-6 flex flex-col relative overflow-hidden">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold flex items-center gap-2 text-sm text-white/90">
              <Database size={16} className="text-blue-200" />
              Semantic Map
            </h3>
            <button onClick={() => { setZoom(1); setCenter({x:0, y:0}); }} className="px-3 py-1 bg-white/10 rounded-lg hover:bg-white/20 text-white/80 transition-colors text-xs font-medium border border-white/10">
              Reset View
            </button>
          </div>
          <div 
            ref={chartContainerRef}
            className={`flex-1 w-full min-h-0 cursor-${isDragging ? 'grabbing' : 'grab'} border border-white/10 rounded-2xl bg-black/10 touch-none`}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <XAxis type="number" dataKey="x" name="x" hide domain={currentDomainX} allowDataOverflow />
                <YAxis type="number" dataKey="y" name="y" hide domain={currentDomainY} allowDataOverflow />
                <ZAxis type="number" range={[150, 500]} />
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.3)' }} />
                <Scatter name="Documents" data={data} animationDuration={300}>
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} fillOpacity={0.9} stroke="#fff" strokeWidth={1} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <div className="absolute bottom-8 right-8 pointer-events-none flex items-center gap-2 text-[10px] text-white/50 bg-black/20 px-3 py-1.5 rounded-full border border-white/5 backdrop-blur-sm">
            <Move size={12} />
            Scroll to Zoom • Drag to Pan
          </div>
        </div>

        <div className="bg-white/20 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(0,0,0,0.3)] border border-white/10 p-6 flex flex-col overflow-hidden">
          <h3 className="font-semibold mb-4 text-sm flex items-center gap-2 text-white/90">
            <Layers size={16} className="text-blue-200" />
            Clusters
          </h3>
          <div className="overflow-y-auto pr-2 space-y-3 scrollbar-hide flex-1">
            {clusters.map(folder => (
              <div key={folder} className="bg-white/5 hover:bg-white/10 rounded-xl p-3 border border-white/5 transition-colors group">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 overflow-hidden">
                    <span className="w-2 h-2 rounded-full flex-shrink-0 shadow-[0_0_8px_rgba(255,255,255,0.4)]" style={{ backgroundColor: clusterColorMap[folder] }} />
                    <span className="font-medium text-xs text-white/90 truncate" title={folder}>{folder}</span>
                  </div>
                  <span className="bg-white/10 text-white/80 text-[10px] px-2 py-0.5 rounded-full border border-white/10 font-medium">
                    {analysis.filter(a => a.folder === folder).length}
                  </span>
                </div>
                <div className="space-y-1">
                  {analysis.filter(a => a.folder === folder).slice(0, 3).map((file, i) => (
                    <div key={i} className="flex items-center gap-2 text-[10px] text-white/50 truncate pl-4 group-hover:text-white/70 transition-colors">
                      <FileText size={10} className="shrink-0" />
                      {file.filename}
                    </div>
                  ))}
                  {analysis.filter(a => a.folder === folder).length > 3 && (
                    <div className="text-[10px] text-white/30 pl-8 pt-1 font-medium">
                      + {analysis.filter(a => a.folder === folder).length - 3} more...
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}