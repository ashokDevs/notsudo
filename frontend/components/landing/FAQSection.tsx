"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

interface FAQ {
  question: string;
  answer: string;
}

const faqs: FAQ[] = [
  {
    question: "How do I use NotSudo to fix an issue?",
    answer: "Simply comment @notsudo on any GitHub issue in your repository. Our AI will analyze the issue, understand the context of your codebase, and create a pull request with the fix – usually within 5 minutes.",
  },
  {
    question: "What types of issues can NotSudo fix?",
    answer: "NotSudo handles bug fixes, simple feature additions, refactoring tasks, dependency updates, documentation updates, and configuration changes. For complex architectural changes, it works great as a first draft you can iterate on.",
  },
  {
    question: "Is my code secure?",
    answer: "Absolutely. All code analysis happens in isolated Docker containers. Your code never leaves your infrastructure, and we don't store any repository data. API keys are encrypted and scoped to minimal permissions.",
  },
  {
    question: "What if the generated PR isn't perfect?",
    answer: "Just comment on the PR with feedback like you would with any developer. NotSudo will read your comments, understand the issues, and push updated commits. It learns from your feedback to get better over time.",
  },
  {
    question: "How fast does it fix issues?",
    answer: "Most issues are resolved in under 5 minutes. Complex issues that require more analysis might take up to 15 minutes. Either way, it's faster than waiting for the next sprint planning meeting.",
  },
  {
    question: "Can it work with my existing CI/CD pipeline?",
    answer: "Yes! NotSudo creates standard pull requests that go through your normal review and CI/CD process. It validates code in Docker containers before creating the PR, so your CI checks usually pass on the first try.",
  },
];

export function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="relative py-32 px-4 bg-black border-t-2 border-orange-500/30">
      <div className="relative z-10 max-w-3xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-2 text-lg font-retro-body text-purple-500 border-2 border-purple-500/50 mb-6 uppercase tracking-wider">
            [ FAQ ]
          </span>
          <h2 className="font-retro-heading text-xl md:text-2xl text-white mb-4 leading-relaxed uppercase tracking-wider">
            All your questions
            <br />
            <span className="text-purple-400">Answered</span>
          </h2>
        </div>

        {/* FAQ Items */}
        <div className="space-y-3">
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index;
            
            return (
              <div
                key={index}
                className="border-2 border-purple-500/30 bg-black overflow-hidden hover:border-purple-500 transition-colors"
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : index)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-purple-500/5 transition-colors"
                >
                  <span className="font-retro-body text-lg text-white pr-4 uppercase tracking-wider">
                    {faq.question}
                  </span>
                  <ChevronDown 
                    className={`w-5 h-5 text-purple-500 flex-shrink-0 transition-transform duration-300 ${
                      isOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
                
                <div
                  className={`overflow-hidden transition-all duration-300 ${
                    isOpen ? "max-h-96" : "max-h-0"
                  }`}
                >
                  <div className="px-6 pb-5 text-gray-400 font-retro-body text-lg leading-relaxed">
                    {faq.answer}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

