import { Loader2 } from "lucide-react";

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="bg-white p-5 rounded-3xl border border-gray-100 shadow-sm flex flex-col gap-2"
        >
          <div className="w-8 h-8 bg-gray-100 rounded-lg mb-2" />
          <div className="h-8 w-20 bg-gray-200 rounded" />
          <div className="h-3 w-16 bg-gray-100 rounded" />
        </div>
      ))}
    </div>
  );
}

export function MapSkeleton() {
  return (
    <div className="bg-white rounded-3xl h-[600px] border border-gray-100 shadow-sm mb-8 relative overflow-hidden animate-pulse">
      <div className="absolute top-8 left-8 flex flex-col gap-2 opacity-30">
        <div className="h-6 w-56 bg-gray-100 rounded-lg" />
        <div className="h-3 w-64 bg-gray-50 rounded-lg" />
      </div>
      <div className="w-full h-full flex flex-col items-center justify-center gap-6">
        <div className="relative">
          <Loader2 className="text-gray-200 animate-spin" size={64} />
          <div className="absolute inset-0 bg-blue-100/10 blur-xl rounded-full" />
        </div>
        <p className="text-gray-400 font-medium tracking-tight">
          Synthesizing semantic space...
        </p>
      </div>
    </div>
  );
}

export function FoldersSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-white rounded-3xl border border-gray-100 shadow-sm animate-pulse"
        >
          <div className="flex items-center justify-between px-6 py-6">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-gray-100 rounded-xl" />
              <div>
                <div className="h-5 w-48 bg-gray-200 rounded mb-2" />
                <div className="h-3 w-24 bg-gray-100 rounded" />
              </div>
            </div>
            <div className="w-5 h-5 bg-gray-100 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SearchSkeleton() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="flex items-center justify-between mb-4 px-2">
        <div className="h-6 w-40 bg-gray-200 rounded" />
        <div className="h-3.5 w-28 bg-gray-100 rounded" />
      </div>
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div
          key={i}
          className="flex items-center justify-between p-2.5 bg-white rounded-xl border border-gray-100"
        >
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-gray-100 rounded-lg" />
            <div className="h-4 w-48 md:w-64 bg-gray-200 rounded" />
          </div>
          <div className="flex items-center gap-3 shrink-0 ml-4">
            <div className="w-14 h-4 bg-gray-100 rounded-full" />
            <div className="w-12 h-3 bg-gray-50 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ResultSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header Skeleton */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12 animate-pulse">
          <div>
            <div className="h-4 w-32 bg-gray-200 rounded mb-4" />
            <div className="flex items-center gap-3">
              <div className="h-10 w-96 bg-gray-300 rounded-lg" />
              <div className="h-6 w-16 bg-green-100 rounded-full" />
            </div>
            <div className="h-4 w-[500px] bg-gray-200 rounded mt-4" />
          </div>
          <div className="h-12 w-40 bg-gray-300 rounded-2xl" />
        </div>

        <StatsSkeleton />
        <MapSkeleton />

        {/* Search Bar Skeleton */}
        <div className="rounded-2xl border border-gray-100 mb-8 bg-gray-200/50 h-14 animate-pulse" />

        <FoldersSkeleton />
      </div>
    </div>
  );
}
