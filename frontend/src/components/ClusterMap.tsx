"use client";

import React, { useMemo, useState } from "react";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { motion, AnimatePresence } from "framer-motion";
import { Maximize2, Move, Search } from "lucide-react";
import { AnalysisItem } from "@/components/ResultView";

const CLUSTER_COLORS = [
  "#6366f1", // Indigo
  "#ec4899", // Pink
  "#f59e0b", // Amber
  "#10b981", // Emerald
  "#3b82f6", // Blue
  "#8b5cf6", // Violet
  "#f43f5e", // Rose
  "#06b6d4", // Cyan
  "#ef4444", // Red
  "#84cc16", // Lime
];

interface Point extends AnalysisItem {
  vx: number;
  vy: number;
  color: string;
}

interface ClusterMapProps {
  analysis: AnalysisItem[];
  highlightedId?: string | null;
}

export default function ClusterMap({
  analysis,
  highlightedId,
}: ClusterMapProps) {
  const [hoveredPoint, setHoveredPoint] = useState<Point | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [currentScale, setCurrentScale] = useState(1);

  // 1. Calculate vibrant colors for each cluster
  const clusters = useMemo(
    () => Array.from(new Set(analysis.map((a) => a.folder))),
    [analysis],
  );
  const clusterColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    clusters.forEach((folder, i) => {
      map[folder] = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
    });
    return map;
  }, [clusters]);

  // 2. Data bounds for normalization
  const bounds = useMemo(() => {
    if (analysis.length === 0) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    const xs = analysis.map((a) => a.x);
    const ys = analysis.map((a) => a.y);
    return {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    };
  }, [analysis]);

  // Use a fixed virtual coordinate system for the SVG
  const VIEW_SIZE = 1000;
  const PADDING = 100;

  const points = useMemo<Point[]>(() => {
    const rangeX = bounds.maxX - bounds.minX || 1;
    const rangeY = bounds.maxY - bounds.minY || 1;

    return analysis.map((item) => {
      // Normalize to 0-1 and then scale to VIEW_SIZE
      const nx = (item.x - bounds.minX) / rangeX;
      const ny = (item.y - bounds.minY) / rangeY;

      return {
        ...item,
        vx: nx * (VIEW_SIZE - 2 * PADDING) + PADDING,
        vy: ny * (VIEW_SIZE - 2 * PADDING) + PADDING,
        color: clusterColorMap[item.folder],
      };
    });
  }, [analysis, bounds, clusterColorMap]);

  // 3. Calculate centroids for cluster labels
  const centroids = useMemo(() => {
    const clusterPoints: Record<string, Point[]> = {};
    points.forEach((p) => {
      if (!clusterPoints[p.folder]) clusterPoints[p.folder] = [];
      clusterPoints[p.folder].push(p);
    });

    return Object.entries(clusterPoints)
      .filter(([folder]) => folder !== "Miscellaneous" && folder !== "Misc")
      .map(([folder, pts]) => {
        const avgX = pts.reduce((sum, p) => sum + p.vx, 0) / pts.length;
        const avgY = pts.reduce((sum, p) => sum + p.vy, 0) / pts.length;
        return {
          folder,
          x: avgX,
          y: avgY,
          color: pts[0].color,
        };
      });
  }, [points]);

  const highlightedPoint = useMemo(
    () => (highlightedId ? points.find((p) => p.id === highlightedId) : null),
    [points, highlightedId],
  );

  const handleMouseMove = (e: React.MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });
  };

  return (
    <div className="relative w-full h-[600px] bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden group">
      {/* Header Info ... same as before */}
      <div className="absolute top-6 left-6 z-10 flex flex-col gap-1 pointer-events-none">
        <h3 className="text-sm font-bold text-[#203047] flex items-center gap-2">
          <Maximize2 size={16} className="text-[#4A80A6]" />
          Semantic Document Landscape
        </h3>
        <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">
          AI-Clustered Relationships
        </p>
      </div>

      {/* Controls Overlay ... same as before */}
      <div className="absolute bottom-6 right-6 z-10 flex flex-col gap-2 scale-90 origin-bottom-right opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="bg-white/80 backdrop-blur-md p-3 rounded-2xl border border-gray-100 shadow-xl flex items-center gap-4 text-[10px] text-gray-500 font-bold">
          <div className="flex items-center gap-1.5">
            <Move size={12} /> PAN
          </div>
          <div className="flex items-center gap-1.5">
            <Search size={12} /> SCROLL TO ZOOM
          </div>
        </div>
      </div>

      <TransformWrapper
        initialScale={1}
        minScale={0.5}
        maxScale={10}
        centerOnInit
        onTransformed={(ref) => setCurrentScale(ref.state.scale)}
      >
        <TransformComponent
          wrapperClass="!w-full !h-full"
          contentClass="!w-full !h-full"
        >
          <div
            className="w-full h-full cursor-grab active:cursor-grabbing"
            onMouseMove={handleMouseMove}
          >
            <svg
              viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
              className="w-full h-full overflow-visible"
              preserveAspectRatio="xMidYMid meet"
            >
              <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Data Points */}
              {/* Data Points */}
              {points.map((p, i) => (
                <motion.circle
                  key={i}
                  cx={p.vx}
                  cy={p.vy}
                  r={Math.max(2, 8 / Math.sqrt(currentScale))}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: hoveredPoint === p ? 1.5 : 1, opacity: 1 }}
                  transition={{
                    delay: i * 0.005,
                    type: "spring",
                    stiffness: 300,
                    damping: 15,
                  }}
                  fill={p.color}
                  stroke="white"
                  strokeWidth={1 / currentScale + 1}
                  className="cursor-pointer drop-shadow-sm transition-colors"
                  style={{
                    filter: hoveredPoint === p ? "url(#glow)" : "none",
                  }}
                  onMouseEnter={() => setHoveredPoint(p)}
                  onMouseLeave={() => setHoveredPoint(null)}
                />
              ))}

              {/* Spinning Highlight for hovered file from list */}
              <AnimatePresence>
                {highlightedPoint && (
                  <motion.g
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.5 }}
                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  >
                    <motion.circle
                      cx={highlightedPoint.vx}
                      cy={highlightedPoint.vy}
                      r={Math.max(12, 18 / Math.sqrt(currentScale))}
                      fill="none"
                      stroke={highlightedPoint.color}
                      strokeWidth={3 / currentScale}
                      strokeDasharray={`${8 / currentScale} ${4 / currentScale}`}
                      animate={{ rotate: 360 }}
                      transition={{
                        repeat: Infinity,
                        duration: 4,
                        ease: "linear",
                      }}
                      style={{
                        transformOrigin: `${highlightedPoint.vx}px ${highlightedPoint.vy}px`,
                      }}
                    />
                    <motion.circle
                      cx={highlightedPoint.vx}
                      cy={highlightedPoint.vy}
                      r={Math.max(16, 24 / Math.sqrt(currentScale))}
                      fill="none"
                      stroke={highlightedPoint.color}
                      strokeWidth={1.5 / currentScale}
                      strokeDasharray={`${4 / currentScale} ${8 / currentScale}`}
                      animate={{ rotate: -360 }}
                      transition={{
                        repeat: Infinity,
                        duration: 6,
                        ease: "linear",
                      }}
                      style={{
                        transformOrigin: `${highlightedPoint.vx}px ${highlightedPoint.vy}px`,
                        opacity: 0.5,
                      }}
                    />
                  </motion.g>
                )}
              </AnimatePresence>

              {/* Cluster Labels at Centroids */}
              {centroids.map((c, i) => {
                const labelScale = 2 / currentScale;
                const fontSize = 11 * labelScale;
                const rectWidth = 120 * labelScale;
                const rectHeight = 24 * labelScale;
                const yOffset = 28 * labelScale;
                const rectYOffset = 45 * labelScale;

                return (
                  <g
                    key={`label-${i}`}
                    className="pointer-events-none select-none"
                  >
                    <rect
                      x={c.x - rectWidth / 2}
                      y={c.y - rectYOffset}
                      width={rectWidth}
                      height={rectHeight}
                      rx={rectHeight / 2}
                      fill="white"
                      fillOpacity={0.5}
                      className="drop-shadow-sm"
                    />
                    <text
                      x={c.x}
                      y={c.y - yOffset}
                      textAnchor="middle"
                      fill={c.color}
                      className="font-bold tracking-tight"
                      style={{
                        fontSize: `${fontSize}px`,
                      }}
                    >
                      {c.folder}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </TransformComponent>
      </TransformWrapper>

      {/* Modern Tooltip */}
      <AnimatePresence>
        {hoveredPoint && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed pointer-events-none z-[999] bg-white text-[#203047] p-5 rounded-[24px] shadow-2xl border border-gray-100 min-w-[320px] max-w-[340px]"
            style={{
              left: mousePos.x + 20,
              top: mousePos.y + 20,
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: hoveredPoint.color }}
              />
              <span
                className="text-[10px] uppercase tracking-widest font-black"
                style={{ color: hoveredPoint.color, opacity: 0.6 }}
              >
                AI Metadata Insight
              </span>
            </div>

            <div className="mb-4">
              <span className="text-[11px] text-gray-400 block mb-1">
                Document Path
              </span>
              <span className="text-xs font-bold text-[#203047] block truncate">
                {hoveredPoint.folder} / {hoveredPoint.filename}
              </span>
            </div>

            {hoveredPoint.metadata.suggested_filename && (
              <div className="mb-4">
                <span className="text-[11px] text-gray-400 block mb-1">
                  Proposed Filename
                </span>
                <span
                  className="text-xs font-bold break-all leading-tight"
                  style={{ color: hoveredPoint.color }}
                >
                  {hoveredPoint.metadata.suggested_filename}
                </span>
              </div>
            )}

            {hoveredPoint.metadata.document_type && (
              <div className="mb-4">
                <span className="text-[11px] text-gray-400 block mb-1">
                  Classification
                </span>
                <span className="text-xs font-bold bg-gray-50 text-gray-600 px-2 py-1 rounded-lg border border-gray-100">
                  {hoveredPoint.metadata.document_type}
                </span>
              </div>
            )}

            {hoveredPoint.metadata.summary && (
              <div className="mb-4">
                <span className="text-[11px] text-gray-400 block mb-1.5">
                  AI Summary
                </span>
                <p className="text-xs leading-relaxed text-gray-600 font-medium italic">
                  &ldquo;{hoveredPoint.metadata.summary}&rdquo;
                </p>
              </div>
            )}

            {hoveredPoint.metadata.tags &&
              hoveredPoint.metadata.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-3 border-t border-gray-50">
                  {hoveredPoint.metadata.tags.map((tag, idx) => (
                    <span
                      key={`${tag}-${idx}`}
                      className="text-[9px] font-bold bg-gray-50 px-2 py-0.5 rounded-md"
                      style={{ color: hoveredPoint.color }}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

            <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between opacity-60">
              <div className="text-[10px] text-gray-400 font-medium">
                {hoveredPoint.metadata.file_size_kb} KB
              </div>
              <div className="text-[9px] bg-gray-50 px-2 py-0.5 rounded-full text-gray-500 font-bold uppercase transition-colors">
                {hoveredPoint.metadata.file_type}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
