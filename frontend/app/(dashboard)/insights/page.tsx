"use client";

import React, { useState } from "react";
import { TrendingUp, Clock, Percent, Sparkles, Target, Zap, CheckCircle2 } from "lucide-react";

export default function InsightsPage() {
  const [applied, setApplied] = useState<Record<string, boolean>>({});

  const handleApply = (key: string) => {
    setApplied(prev => ({ ...prev, [key]: true }));
    setTimeout(() => {
      setApplied(prev => ({ ...prev, [key]: false }));
    }, 3000);
  };

  return (
    <div className="h-full flex flex-col gap-8 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-semibold text-indigo-950 mb-1">Business Copilot</h1>
        <p className="text-slate-500 text-xs font-normal">AI-driven operational insights and real-time recommendations.</p>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-3xl p-7 shadow-lg shadow-indigo-100/30 hover:shadow-xl transition-all relative overflow-hidden">
          <div className="relative z-10">
            <div className="w-12 h-12 bg-emerald-50 border border-emerald-100 rounded-2xl flex items-center justify-center mb-4 text-emerald-600 shadow-sm">
              <TrendingUp className="w-6 h-6" />
            </div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Conversion Rate</p>
            <h3 className="text-3xl font-semibold text-indigo-950">24.5%</h3>
            <p className="text-emerald-600 text-xs font-medium mt-2 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" /> +2.1% from yesterday
            </p>
          </div>
        </div>

        <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-3xl p-7 shadow-lg shadow-indigo-100/30 hover:shadow-xl transition-all relative overflow-hidden">
          <div className="relative z-10">
            <div className="w-12 h-12 bg-amber-50 border border-amber-100 rounded-2xl flex items-center justify-center mb-4 text-amber-600 shadow-sm">
              <Clock className="w-6 h-6" />
            </div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Peak Negotiation Hours</p>
            <h3 className="text-3xl font-semibold text-indigo-950">14:00 - 16:00</h3>
            <p className="text-slate-500 text-xs font-normal mt-2">Highest chat traffic period</p>
          </div>
        </div>

        <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-3xl p-7 shadow-lg shadow-indigo-100/30 hover:shadow-xl transition-all relative overflow-hidden">
          <div className="relative z-10">
            <div className="w-12 h-12 bg-[#715bc9]/10 border border-[#715bc9]/20 rounded-2xl flex items-center justify-center mb-4 text-[#715bc9] shadow-sm">
              <Percent className="w-6 h-6" />
            </div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Average Discount Given</p>
            <h3 className="text-3xl font-semibold text-[#715bc9]">8.2%</h3>
            <p className="text-[#715bc9] text-xs font-medium mt-2">Well below 15% floor limit</p>
          </div>
        </div>
      </div>

      {/* AI Recommendations */}
      <div className="space-y-6 pt-2">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-[#715bc9]/10 border border-[#715bc9]/20 rounded-2xl">
            <Sparkles className="w-6 h-6 text-[#715bc9]" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold text-indigo-950">Actionable Insights</h2>
            <p className="text-xs text-slate-500 font-normal">One-click operational adjustments powered by Sales Brain.</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Insight Card 1 */}
          <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-3xl p-8 shadow-lg shadow-indigo-100/30 hover:shadow-xl transition-all flex flex-col justify-between space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="bg-[#715bc9]/10 text-[#715bc9] border border-[#715bc9]/20 text-xs px-3 py-1 rounded-lg font-semibold uppercase tracking-wider flex items-center gap-1.5">
                  <Target className="w-3.5 h-3.5" /> Pricing Strategy
                </span>
                <span className="text-slate-400 text-xs font-normal">Just now</span>
              </div>
              <p className="text-base text-indigo-950 font-normal leading-relaxed">
                &ldquo;Kopi Arabica 1kg received 31 negotiation attempts today, with a 12% conversion rate. Lowering floor price by 5% will optimize conversion.&rdquo;
              </p>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={() => handleApply("pricing")}
                className="flex-1 bg-[#715bc9] hover:bg-[#5f49b5] text-white py-3 rounded-xl font-semibold text-xs shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                {applied["pricing"] ? (
                  <> <CheckCircle2 className="w-4 h-4 text-emerald-300" /> Change Applied! </>
                ) : (
                  "Apply Change"
                )}
              </button>
              <button className="flex-1 bg-white border border-slate-200 text-slate-700 py-3 rounded-xl font-semibold text-xs hover:bg-slate-50 transition-all cursor-pointer">
                Dismiss
              </button>
            </div>
          </div>

          {/* Insight Card 2 */}
          <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-3xl p-8 shadow-lg shadow-indigo-100/30 hover:shadow-xl transition-all flex flex-col justify-between space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="bg-[#715bc9]/10 text-[#715bc9] border border-[#715bc9]/20 text-xs px-3 py-1 rounded-lg font-semibold uppercase tracking-wider flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-[#715bc9]" /> Upsell Opportunity
                </span>
                <span className="text-slate-400 text-xs font-normal">2 hours ago</span>
              </div>
              <p className="text-base text-indigo-950 font-normal leading-relaxed">
                &ldquo;Customers buying &lsquo;Kopi Arabica&rsquo; are highly receptive to bundling. Activate a 10% bundle discount with &lsquo;Gula Aren&rsquo; to boost AOV.&rdquo;
              </p>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={() => handleApply("bundle")}
                className="flex-1 bg-[#715bc9] hover:bg-[#5f49b5] text-white py-3 rounded-xl font-semibold text-xs shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                {applied["bundle"] ? (
                  <> <CheckCircle2 className="w-4 h-4 text-emerald-300" /> Bundle Configured! </>
                ) : (
                  "Configure Bundle"
                )}
              </button>
              <button className="flex-1 bg-white border border-slate-200 text-slate-700 py-3 rounded-xl font-semibold text-xs hover:bg-slate-50 transition-all cursor-pointer">
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


