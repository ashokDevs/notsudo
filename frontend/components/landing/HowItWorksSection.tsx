"use client";

interface Step {
  number: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const steps: Step[] = [
  {
    number: "1",
    title: "Select your GitHub repository and branch. Write a detailed prompt for NotSudo.",
    description: "Use the \"notsudo\" label in an issue to assign a task directly in GitHub.",
    icon: (
      <div className="w-full h-32 bg-gray-900 border border-gray-700 rounded-sm p-4 font-mono text-xs text-gray-400 overflow-hidden relative">
        <div className="absolute top-2 left-2 text-orange-500">@kathy/flipdisc main</div>
        <div className="mt-6 text-gray-300">
          Can you bump the version of next.js to v15 and convert the project to use app directory?
        </div>
      </div>
    ),
  },
  {
    number: "2",
    title: "NotSudo fetches your repository, clones it to a Cloud VM, and develops a plan utilizing the latest model.",
    description: "",
    icon: (
      <div className="w-full h-32 bg-gray-900 border border-gray-700 rounded-sm p-4 font-mono text-xs text-gray-400 overflow-hidden relative">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-4 h-4 rounded-full bg-orange-500/20 flex items-center justify-center text-orange-500 text-[8px]">N</div>
          <span className="text-gray-500">NotSudo Avatar</span>
        </div>
        <div className="text-gray-300">
          Here is my plan: I plan to update the following files to the new app directory structure.
        </div>
        <div className="mt-2 text-green-500">Update 22 Files</div>
      </div>
    ),
  },
  {
    number: "3",
    title: "NotSudo provides a diff of the changes. Quickly browse and approve code edits.",
    description: "",
    icon: (
      <div className="w-full h-32 bg-gray-900 border border-gray-700 rounded-sm p-4 font-mono text-xs overflow-hidden relative leading-relaxed">
        <div className="text-gray-500">"dependencies": {"{"}</div>
        <div className="text-red-500 bg-red-900/10">- "next": "10.2.3",</div>
        <div className="text-green-500 bg-green-900/10">+ "next": "15.4.5",</div>
        <div className="text-gray-300">"react": "19.1.1",</div>
        <div className="text-gray-500">{"}"}</div>
      </div>
    ),
  },
  {
    number: "4",
    title: "NotSudo creates a PR of the changes. Approve the PR, merge it to your branch, and publish it on GitHub.",
    description: "",
    icon: (
      <div className="w-full h-32 bg-gray-900 border border-gray-700 rounded-sm flex items-center justify-center">
        <button className="bg-green-600 text-white px-4 py-2 text-xs font-mono rounded hover:bg-green-500">
          Publish Branch
        </button>
      </div>
    ),
  },
];

export function HowItWorksSection() {
  return (
    <section className="relative py-24 px-4 bg-black">
      <div className="max-w-6xl mx-auto">
        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {steps.map((step, index) => (
            <div
              key={index}
              className="flex flex-col gap-4"
            >
              {/* Step Number */}
              <div className="w-8 h-8 rounded-full border border-gray-700 flex items-center justify-center text-gray-500 font-mono text-sm">
                {step.number}
              </div>

              {/* Title */}
              <h3 className="text-sm font-bold text-white font-mono leading-relaxed min-h-[80px]">
                {step.title}
              </h3>

              {/* Icon/Visual */}
              <div className="mb-4">
                {step.icon}
              </div>

              {/* Description */}
              {step.description && (
                <p className="text-xs text-gray-500 font-mono leading-relaxed">
                  {step.description}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
