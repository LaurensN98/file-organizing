import FileUpload from "@/components/FileUpload";
import Image from "next/image";
import { UploadCloud, Brain, FolderTree } from "lucide-react";

export default function Home() {
  return (
    <main className="relative min-h-screen">
      <div className="flex flex-col py-20 px-12 max-w-7xl mx-auto overflow-hidden bg-gray-50">
        <h1 className="font-bold text-5xl mb-6">
          Your Files, <br />
          <span className="text-[#4A80A6]">Neatly Organized.</span>
        </h1>
        <p className="text-xl w-96 mb-12">
          The intelligent file organizer that transforms digital chaos into
          perfect order. Automatically.
        </p>

        <div className="flex justify-between">
          <div className="w-1/2 -ml-14 -mb-1 relative overflow-hidden">
            <Image
              src="/svgs/homepage_visualization.svg"
              alt="galton board visualization"
              fill
              className="object-contain"
            />
          </div>
          <div className="w-1/2 flex flex-col gap-4">
            <FileUpload />
          </div>
        </div>
      </div>

      <div className="bg-[#4A80A6] text-white">
        <div className="flex flex-col py-20 px-12 max-w-7xl mx-auto overflow-hidden">
          <h2 className="text-3xl md:text-5xl font-bold mb-16 text-center">
            How it works
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
            {/* Connecting Line for Desktop */}
            <div className="hidden md:block absolute top-10 left-[16%] right-[16%] h-0.5 bg-white/20 -z-0"></div>

            {/* Step 1 */}
            <div className="flex flex-col items-center text-center group z-10">
              <div className="w-20 h-20 bg-[#5A90B6] rounded-2xl flex items-center justify-center mb-6 border border-white/20 group-hover:scale-110 group-hover:bg-[#6AA0C6] shadow-lg transition-all duration-300">
                <UploadCloud size={36} className="text-white" />
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">
                1. Upload Files
              </h3>
              <p className="text-white/80 leading-relaxed max-w-sm">
                Securely drag and drop your disorganized folders and loose
                documents. We support hundreds of file types out of the box.
              </p>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col items-center text-center group z-10">
              <div className="w-20 h-20 bg-[#5A90B6] rounded-2xl flex items-center justify-center mb-6 border border-white/20 group-hover:scale-110 group-hover:bg-[#6AA0C6] shadow-lg transition-all duration-300">
                <Brain size={36} className="text-white" />
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">
                2. AI Analysis
              </h3>
              <p className="text-white/80 leading-relaxed max-w-sm">
                Our privacy-focused AI securely analyzes the content and context
                of each file without retaining any of your sensitive data.
              </p>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col items-center text-center group z-10">
              <div className="w-20 h-20 bg-[#5A90B6] rounded-2xl flex items-center justify-center mb-6 border border-white/20 group-hover:scale-110 group-hover:bg-[#6AA0C6] shadow-lg transition-all duration-300">
                <FolderTree size={36} className="text-white" />
              </div>
              <h3 className="text-2xl font-semibold mb-4 text-white">
                3. Perfect Order
              </h3>
              <p className="text-white/80 leading-relaxed max-w-sm">
                Files are automatically renamed, categorized, and sorted into a
                logical, perfectly structured nested folder hierarchy.
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
