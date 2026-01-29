import React from "react";
import Link from "next/link";
import { ArrowLeft, Shield, Lock, Server } from "lucide-react";

export default function PrivacyPolicy() {
  return (
    <main className="min-h-screen p-6 bg-[#FAFAFA] flex justify-center">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-sm border border-gray-100 p-8 sm:p-12 my-8">
        <Link 
          href="/" 
          className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-black mb-8 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Tool
        </Link>

        <h1 className="text-2xl font-semibold tracking-tight text-gray-900 mb-2">
          Privacy Policy
        </h1>
        <p className="text-sm text-gray-500 mb-8">
          Last updated: January 27, 2026
        </p>

        <div className="space-y-8">
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Shield size={18} />
              1. Zero Data Retention (ZDR)
            </h2>
            <p className="text-sm text-gray-600 leading-relaxed">
              We operate on a strict "Zero Data Retention" principle. When you upload documents:
            </p>
            <ul className="list-disc pl-5 mt-2 text-sm text-gray-600 space-y-1">
              <li>Files are processed entirely in volatile memory (RAM).</li>
              <li>No file content is ever written to our disk storage.</li>
              <li>Once the organization process is complete and the download stream finishes, the file data is immediately discarded from memory.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Server size={18} />
              2. Data Sovereignty & Infrastructure
            </h2>
            <p className="text-sm text-gray-600 leading-relaxed">
              Our infrastructure is designed to respect EU data sovereignty.
            </p>
            <ul className="list-disc pl-5 mt-2 text-sm text-gray-600 space-y-1">
              <li><strong>Hosting:</strong> Our core processing servers are located within the European Union (Amsterdam/France regions).</li>
              <li><strong>Metadata:</strong> We store only technical metadata (filenames, cluster categories, timestamps) in our database. We do not store the content of your documents.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Lock size={18} />
              3. AI Subprocessors
            </h2>
            <p className="text-sm text-gray-600 leading-relaxed">
              To provide intelligent categorization, we utilize third-party AI subprocessors.
            </p>
            <ul className="list-disc pl-5 mt-2 text-sm text-gray-600 space-y-1">
              <li><strong>Embeddings & Classification:</strong> Text snippets are sent to our AI providers (e.g., Mistral or GPT-OSS via OVHcloud EU endpoints) solely for the purpose of generating mathematical representations (embeddings) and category labels.</li>
              <li><strong>No Training:</strong> We have configured our agreements to ensure your data is <strong>not</strong> used to train their models.</li>
            </ul>
          </section>
        </div>
      </div>
    </main>
  );
}
