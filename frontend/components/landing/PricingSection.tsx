"use client";

interface PricingTier {
  tier: string;
  name: string;
  price: string;
  priceSubtext?: string;
  features: string[];
  cta: string;
  ctaStyle: "outline" | "filled";
  footer: string;
  featured?: boolean;
}

const pricingTiers: PricingTier[] = [
  {
    tier: "Starter",
    name: "Free",
    price: "",
    features: [
      "Up to 10 issues resolved /month",
      "Basic bug fixes & refactoring",
      "Community Discord support",
      "Public repos only",
    ],
    cta: "START FOR FREE",
    ctaStyle: "outline",
    footer: "(✓) NO CC REQUIRED",
  },
  {
    tier: "Pro",
    name: "$49",
    price: "/MO",
    features: [
      "Unlimited issues resolved",
      "Feature development & tests",
      "Private repos supported",
      "Priority PR reviews",
      "Slack integration",
    ],
    cta: "GET STARTED",
    ctaStyle: "filled",
    footer: "($) CANCEL ANYTIME",
    featured: true,
  },
  {
    tier: "Team",
    name: "Custom",
    price: "",
    features: [],
    cta: "CONTACT US",
    ctaStyle: "outline",
    footer: "($) VOLUME DISCOUNTS",
  },
];

export function PricingSection() {
  return (
    <section className="relative py-24 px-4 bg-black">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center mb-12">
          <span className="inline-block px-3 py-1 text-xs font-mono text-gray-400 border border-gray-700 mb-6">
            [ PRICING ]
          </span>

          <h2 className="font-mono text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 tracking-tight">
            SIMPLE{" "}
            <span className="inline-block border-2 border-orange-500 px-2 py-0.5">
              PRICING
            </span>
          </h2>

          <p className="text-gray-400 max-w-lg mx-auto font-mono text-sm">
            Cheaper than an intern. Works harder than your best engineer.
            <br />
            No benefits, no drama, just code.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border border-gray-700">
          {pricingTiers.map((tier, index) => (
            <div
              key={index}
              className={`relative p-8 flex flex-col ${
                tier.featured
                  ? "bg-white border-x border-gray-700"
                  : "bg-black"
              } ${index !== 0 ? "md:border-l border-t md:border-t-0 border-gray-700" : ""}`}
            >
              {/* Tier Label */}
              <div className="text-center mb-2">
                <span
                  className={`text-sm ${
                    tier.featured ? "text-orange-500" : "text-gray-500"
                  }`}
                >
                  {tier.tier}
                </span>
              </div>

              {/* Price */}
              <div className="text-center mb-2">
                <span className={`text-3xl md:text-4xl font-bold font-serif ${tier.featured ? 'text-black' : 'text-white'}`}>
                  {tier.name}
                </span>
                {tier.price && (
                  <span className="text-sm text-gray-500">{tier.price}</span>
                )}
              </div>

              {/* Features */}
              <div className="flex-1 mb-8">
                {tier.features.length > 0 ? (
                  <ul className="space-y-3">
                    {tier.features.map((feature, featureIndex) => (
                      <li
                        key={featureIndex}
                        className={`flex items-start gap-2 text-sm ${tier.featured ? 'text-gray-700' : 'text-gray-300'}`}
                      >
                        <span className="text-orange-500 mt-0.5">✓</span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-center text-sm text-gray-500">
                    Contact us for custom solution
                    <br />
                    with special pricing.
                  </p>
                )}
              </div>

              {/* CTA Button */}
              <div className="text-center">
                <a
                  href="#"
                  className={`inline-block px-8 py-3 text-xs font-mono tracking-wider transition-all duration-200 ${
                    tier.ctaStyle === "filled"
                      ? "bg-black text-white hover:bg-gray-800"
                      : tier.featured
                        ? "bg-transparent text-black border border-black hover:bg-black hover:text-white"
                        : "bg-transparent text-white border border-white hover:bg-white hover:text-black"
                  }`}
                >
                  {tier.cta}
                </a>
              </div>

              {/* Footer */}
              <div className="text-center mt-4">
                <span className="text-xs font-mono text-gray-500">
                  {tier.footer}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
