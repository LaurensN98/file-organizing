import FileUpload from "@/components/FileUpload";
import Image from "next/image";
import { Search, ChevronsDown, ChevronRight, Map } from "lucide-react";

export default function Home() {
  return (
    <main className="relative min-h-screen bg-white">
      {/* Hero Section */}
      <div className="bg-gradient-to-b from-[#FFFFFF] to-[#F5F9FB]">
        <div className="flex flex-col items-center justify-center pt-20 pb-32 px-6 max-w-7xl mx-auto text-center relative">
          <h1 className="font-extrabold text-[5rem] md:text-[6.5rem] leading-[1.1] tracking-tight mb-8 text-[#0B1021]">
            Your Files, <br />
            <span className="bg-gradient-primary text-transparent bg-clip-text inline-block pb-4 md:pb-6 -mb-4 md:-mb-6">
              Neatly Organized.
            </span>
          </h1>
          <p className="text-[1.35rem] text-gray-500 max-w-[50rem] mb-10 leading-relaxed font-medium">
            Stop hunting for documents. Our intelligent curator automatically
            clusters your files by context, providing editorial precision to
            your digital chaos.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-6">
            <button className="bg-gradient-primary hover:bg-[#1E1753] text-white px-8 py-4 rounded-2xl font-medium text-[1.1rem] transition-all] hover:shadow-[0_8px_30px_rgb(45,36,119,0.4)]">
              Start Your Free Trial
            </button>
            <button className="bg-white border border-gray-100 hover:border-gray-200 text-gray-900 px-8 py-4 rounded-2xl font-medium text-[1.1rem] transition-colors">
              Watch Product Tour
            </button>
          </div>

          {/* Upload Component */}
          <div className="max-w-4xl mx-auto px-6 mt-10 mb-20 relative z-10 w-full">
            <FileUpload />
          </div>
        </div>
      </div>

      {/* Logos Section */}
      <div className="py-20 border-t border-b border-gray-100 bg-white">
        <div className="max-w-7xl px-6 mx-auto text-center">
          <p className="text-[0.65rem] font-bold tracking-[0.2em] text-gray-400 mb-10 uppercase">
            Empowering modern workflows at
          </p>
          <div className="flex flex-wrap justify-center items-center gap-12 md:gap-24 text-gray-400">
            <span className="text-2xl font-bold font-sans tracking-wide">
              QUANTUM
            </span>
            <span className="text-2xl font-extrabold tracking-tight">
              NEXUS.IO
            </span>
            <span className="text-2xl font-black">STARK</span>
            <span className="text-2xl font-bold tracking-widest">VOID</span>
            <span className="text-2xl font-bold tracking-wide">AETHER</span>
          </div>
        </div>
      </div>

      {/* Intelligence at every layer Section */}
      <div className="py-24 bg-[#FDFDFE]">
        <div className="max-w-7xl px-6 mx-auto flex flex-col items-center">
          <h2 className="text-4xl md:text-[2.75rem] font-bold text-[#0B1021] mb-6 text-center tracking-tight">
            Intelligence at every layer
          </h2>
          <p className="text-lg text-gray-500 text-center max-w-2xl mb-16 font-medium">
            Precision-engineered tools to help you find what you need, before
            you even knew you were looking for it.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full">
            {/* Card 1 */}
            <div className="bg-white border border-gray-100 rounded-[2rem] p-8 md:p-10 hover:shadow-md transition-shadow duration-300">
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center mb-8">
                <Image
                  src="/images/neural.png"
                  alt="Cluster Icon"
                  width={100}
                  height={100}
                  className="w-10 translate-x-0.5"
                />
              </div>
              <h3 className="text-xl font-bold text-[#0B1021] mb-4">
                Contextual Clustering
              </h3>
              <p className="text-gray-500 leading-relaxed text-[0.95rem]">
                Files grouped intelligently based on deep content analysis and
                cross-source context.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-white border border-gray-100 rounded-[2rem] p-8 md:p-10 hover:shadow-md transition-shadow duration-300">
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center mb-8">
                <Image
                  src="/images/tag.png"
                  alt="Label Icon"
                  width={100}
                  height={100}
                  className="w-8"
                />
              </div>
              <h3 className="text-xl font-bold text-[#0B1021] mb-4">
                Auto-Labeling
              </h3>
              <p className="text-gray-500 leading-relaxed text-[0.95rem]">
                Sophisticated tags and metadata applied automatically via neural
                document recognition.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-white border border-gray-100 rounded-[2rem] p-8 md:p-10 hover:shadow-md transition-shadow duration-300">
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center mb-8">
                <Image
                  src="/images/search.png"
                  alt="Search Icon"
                  width={100}
                  height={100}
                  className="w-8"
                />
              </div>
              <h3 className="text-xl font-bold text-[#0B1021] mb-4">
                Semantic Search
              </h3>
              <p className="text-gray-500 leading-relaxed text-[0.95rem]">
                Go beyond keywords. Search for concepts, ideas, and visual data
                with natural language.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* From chaos to clarity Section */}
      <div className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left Side */}
          <div className="pr-0 md:pr-8">
            <h2 className="text-[3rem] md:text-[4rem] font-bold text-[#0B1021] leading-[1.1] mb-2 tracking-tight">
              From chaos to <br />
              <span className="bg-gradient-primary text-transparent bg-clip-text">
                clarity.
              </span>
            </h2>
            <div className="mt-16 flex flex-col gap-6">
              {/* Step 1 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-8 text-[#3A32A8] flex items-center justify-center font-bold text-lg">
                  1
                </div>
                <div>
                  <h4 className="text-[1.35rem] font-bold text-[#0B1021] mb-1">
                    Connect Sources
                  </h4>
                  <p className="text-gray-500 leading-relaxed font-medium">
                    Seamlessly link Cloud and Local drives. Neatly ingests your
                    data in real-time without moving original files.
                  </p>
                </div>
              </div>
              {/* Step 2 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-8 text-[#3A32A8] flex items-center justify-center font-bold text-lg">
                  2
                </div>
                <div>
                  <h4 className="text-[1.35rem] font-bold text-[#0B1021] mb-1">
                    Neural Analysis
                  </h4>
                  <p className="text-gray-500 leading-relaxed font-medium">
                    Our AI models map the relationships between every document,
                    image, and data point you own.
                  </p>
                </div>
              </div>
              {/* Step 3 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-8 text-[#3A32A8] flex items-center justify-center font-bold text-lg">
                  3
                </div>
                <div>
                  <h4 className="text-[1.35rem] font-bold text-[#0B1021] mb-1">
                    Smart Hierarchy
                  </h4>
                  <p className="text-gray-500 leading-relaxed font-medium">
                    Folders dynamically reorganize into logical, searchable
                    clusters with meaningful AI labels.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Side (Visual) */}
          <div className="bg-[#F8F9FA] rounded-[3rem] p-8 md:p-14 flex flex-col gap-10 shadow-sm border border-gray-100">
            {/* Files */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between p-2.5 bg-white rounded-xl border border-gray-100 shadow-sm group transition-all hover:border-blue-200">
                <div className="flex items-center gap-3 overflow-hidden">
                  <Image
                    src="/images/document.png"
                    alt="Document Icon"
                    width={18}
                    height={18}
                    className="w-6"
                  />
                  <span className="text-sm text-gray-700 truncate font-medium">
                    Invoice_Draft_24.pdf
                  </span>
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-4 hidden sm:flex">
                  <span className="text-[10px] uppercase bg-gray-100 px-2 py-0.5 rounded-full font-bold text-gray-500">
                    PDF
                  </span>
                  <span className="text-[10px] text-gray-400 font-medium whitespace-nowrap">
                    245 KB
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between p-2.5 bg-white rounded-xl border border-gray-100 shadow-sm group transition-all hover:border-blue-200">
                <div className="flex items-center gap-3 overflow-hidden">
                  <Image
                    src="/images/document.png"
                    alt="Image Icon"
                    width={18}
                    height={18}
                    className="w-6"
                  />
                  <span className="text-sm text-gray-700 truncate font-medium">
                    Header_Asset.png
                  </span>
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-4 hidden sm:flex">
                  <span className="text-[10px] uppercase bg-gray-100 px-2 py-0.5 rounded-full font-bold text-gray-500">
                    PNG
                  </span>
                  <span className="text-[10px] text-gray-400 font-medium whitespace-nowrap">
                    1.2 MB
                  </span>
                </div>
              </div>
            </div>

            {/* Arrows */}
            <div className="flex justify-center -my-2">
              <ChevronsDown className="text-[#473BE8]" size={36} />
            </div>

            {/* Folders */}
            <div className="flex flex-col gap-4">
              <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                <button className="w-full flex items-center justify-between px-6 py-6 hover:bg-gray-50 transition-colors">
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
                        Marketing &amp; Branding
                      </h3>
                      <p className="text-xs text-gray-500">Contains 12 files</p>
                    </div>
                  </div>
                  <ChevronRight
                    size={20}
                    className="text-gray-400 transition-transform duration-300"
                  />
                </button>
              </div>

              <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                <button className="w-full flex items-center justify-between px-6 py-6 hover:bg-gray-50 transition-colors">
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
                        Financial Records
                      </h3>
                      <p className="text-xs text-gray-500">Contains 8 files</p>
                    </div>
                  </div>
                  <ChevronRight
                    size={20}
                    className="text-gray-400 transition-transform duration-300"
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Intelligence Section */}
      <div className="py-24 bg-[#FDFDFE] relative border-t border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left Side (Visual Dashboard) */}
          <div className="relative w-full aspect-[4/3] max-w-2xl mx-auto lg:mx-0">
            <div className="absolute inset-0 bg-white rounded-[2rem] border border-gray-100 overflow-hidden flex flex-col">
              <div className="relative w-full h-full rounded-[1.25rem] overflow-hidden bg-gray-50">
                <Image
                  src="/images/scatter-visual.png"
                  alt="Semantic Document Landscape"
                  fill
                  className="object-cover object-left-top"
                />
              </div>
            </div>
          </div>

          {/* Right Side */}
          <div className="flex flex-col">
            <div className="mb-2">
              <h2 className="text-[2.5rem] md:text-[3.5rem] font-bold text-[#0B1021] leading-[1.1] tracking-tight">
                The Geometry of <br /> Your Knowledge
              </h2>
            </div>

            <div className="mt-8 flex flex-col gap-6">
              {/* Feature 1 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-8 flex items-center justify-center text-[#203047] bg-white">
                  <Map size={22} className="text-[#0B1021]" />
                </div>
                <div>
                  <h4 className="text-xl font-bold text-[#0B1021] mb-1">
                    Semantic Document Landscape
                  </h4>
                  <p className="text-gray-500 leading-relaxed">
                    Neatly maps your entire digital footprint into a visual 2D
                    landscape. Using neural embeddings, we cluster documents
                    based on their underlying meaning and conceptual
                    relationships, letting you navigate your files spatially.
                  </p>
                </div>
              </div>

              {/* Feature 2 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-8 flex items-center justify-center text-[#203047] bg-white">
                  <Search size={22} className="text-[#0B1021]" />
                </div>
                <div>
                  <h4 className="text-xl font-bold text-[#0B1021] mb-1">
                    Vector-Powered Search
                  </h4>
                  <p className="text-gray-500 leading-relaxed">
                    Stop trying to remember filenames. Our vector-based search
                    engine understands the intent behind your query. Search for
                    concepts or ideas, and find the exact paragraph or image you
                    need in milliseconds.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-24 px-6 max-w-7xl mx-auto w-full">
        <div className="bg-gradient-primary rounded-[3rem] p-12 md:p-24 flex flex-col items-center justify-center text-center shadow-2xl shadow-[#3A32A8]/20 relative overflow-hidden">
          {/* subtle glow effect in bg */}
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-white opacity-[0.03] rounded-full blur-3xl pointer-events-none"></div>

          <h2 className="text-4xl md:text-[3.25rem] font-bold text-white mb-6 relative z-10 tracking-tight leading-tight">
            Ready to reclaim your <br className="hidden md:block" /> digital
            headspace?
          </h2>
          <p className="text-indigo-100/90 text-[1.15rem] max-w-2xl mb-12 relative z-10 font-medium leading-relaxed">
            Join 10,000+ creators and professional teams who organized their
            life with Neatly.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-6 relative z-10">
            <button className="bg-white hover:bg-gray-50 text-[#3A32A8] px-10 py-4 rounded-2xl font-bold text-[1.05rem] transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5 whitespace-nowrap">
              Start Free Now
            </button>
            <div className="text-center sm:text-left flex flex-col justify-center">
              <span className="text-white font-bold text-[0.95rem]">
                No credit card required.
              </span>
              <span className="text-indigo-200/80 text-[0.9rem] mt-0.5">
                Free 14-day trial on all plans.
              </span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
