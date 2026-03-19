'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Result Page Error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
      <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center mb-6 animate-in zoom-in duration-300">
        <AlertCircle size={40} className="text-red-500" />
      </div>
      
      <h2 className="text-2xl font-bold text-[#203047] mb-2">
        Something went wrong
      </h2>
      
      <p className="text-gray-500 max-w-sm mb-8 leading-relaxed">
        {error.message || "We encountered an error while processing your request. Please try again or return to the dashboard."}
      </p>

      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={() => reset()}
          className="flex items-center justify-center gap-2 bg-[#4A80A6] text-white px-8 py-3 rounded-2xl font-bold text-sm hover:bg-[#3A7096] transition-all shadow-sm active:scale-95"
        >
          <RefreshCw size={18} />
          Try Again
        </button>
        
        <button
          onClick={() => router.push("/")}
          className="flex items-center justify-center gap-2 bg-white border border-gray-200 text-gray-600 px-8 py-3 rounded-2xl font-bold text-sm hover:border-[#4A80A6] hover:text-[#4A80A6] transition-all shadow-sm active:scale-95"
        >
          <ArrowLeft size={18} />
          Go Home
        </button>
      </div>
      
      {error.digest && (
        <p className="mt-8 text-[10px] text-gray-300 font-mono uppercase tracking-widest">
          Error ID: {error.digest}
        </p>
      )}
    </div>
  );
}
