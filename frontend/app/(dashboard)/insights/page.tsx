"use client";

import React from "react";
import { TrendingUp, Clock, Percent, Sparkles, ArrowRight, Zap, Target } from "lucide-react";

export default function InsightsPage() {
  return (
    <div className="h-full flex flex-col gap-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-serif font-bold text-indigo-950 mb-2">Business Copilot</h1>
        <p className="text-slate-600 text-lg">AI-driven operational insights and recommendations.</p>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white/60 backdrop-blur-md border border-white rounded-3xl p-6 shadow-xl relative overflow-hidden group hover:shadow-2xl transition-all">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-200/30 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-emerald-300/40 transition-colors" />
          <div className="relative z-10">
            <div className="w-12 h-12 bg-emerald-100 rounded-2xl flex items-center justify-center mb-4 text-emerald-600 shadow-sm">
              <TrendingUp className="w-6 h-6" />
            </div>
            <p className="text-slate-500 font-medium mb-1">Conversion Rate</p>
            <h3 className="text-4xl font-bold text-indigo-950">24.5%</h3>
            <p className="text-emerald-600 text-sm font-semibold mt-2 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" /> +2.1% from yesterday
            </p>
          </div>
        </div>

        <div className="bg-white/60 backdrop-blur-md border border-white rounded-3xl p-6 shadow-xl relative overflow-hidden group hover:shadow-2xl transition-all">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-200/30 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-amber-300/40 transition-colors" />
          <div className="relative z-10">
            <div className="w-12 h-12 bg-amber-100 rounded-2xl flex items-center justify-center mb-4 text-amber-600 shadow-sm">
              <Clock className="w-6 h-6" />
            </div>
            <p className="text-slate-500 font-medium mb-1">Peak Negotiation Hours</p>
            <h3 className="text-4xl font-bold text-indigo-950">14:00 - 16:00</h3>
            <p className="text-slate-600 text-sm mt-2">Highest traffic period</p>
          </div>
        </div>

        <div className="bg-white/60 backdrop-blur-md border border-white rounded-3xl p-6 shadow-xl relative overflow-hidden group hover:shadow-2xl transition-all">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-200/30 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-indigo-300/40 transition-colors" />
          <div className="relative z-10">
            <div className="w-12 h-12 bg-indigo-100 rounded-2xl flex items-center justify-center mb-4 text-indigo-600 shadow-sm">
              <Percent className="w-6 h-6" />
            </div>
            <p className="text-slate-500 font-medium mb-1">Average Discount Given</p>
            <h3 className="text-4xl font-bold text-indigo-950">8.2%</h3>
            <p className="text-indigo-600 text-sm font-semibold mt-2">Well below 15% limit</p>
          </div>
        </div>
      </div>

      {/* AI Recommendations */}
      <div>
        <div className="flex items-center gap-3 mb-6">
          <Sparkles className="w-8 h-8 text-purple-600" />
          <h2 className="text-2xl font-serif font-bold text-indigo-950">Actionable Insights</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Insight Card 1 */}
          <div className="bg-gradient-to-br from-white/80 to-purple-50/80 backdrop-blur-xl border border-white rounded-3xl p-8 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="bg-purple-100 text-purple-700 text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider flex items-center gap-1">
                  <Target className="w-3 h-3" /> Pricing Strategy
                </span>
                <span className="text-slate-400 text-sm">Just now</span>
              </div>
              <p className="text-xl text-indigo-950 font-medium leading-relaxed mb-6">
                "Produk A ditawar 31 kali hari ini, konversi hanya 12%. Saran: turunkan floor price 5% selama 3 hari ke depan."
              </p>
            </div>
            <div className="flex gap-3">
              <button className="flex-1 bg-indigo-600 text-white py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200">
                Apply Change
              </button>
              <button className="flex-1 bg-white border border-indigo-100 text-indigo-600 py-3 rounded-xl font-semibold hover:bg-indigo-50 transition-colors">
                Dismiss
              </button>
            </div>
          </div>

          {/* Insight Card 2 */}
          <div className="bg-gradient-to-br from-white/80 to-emerald-50/80 backdrop-blur-xl border border-white rounded-3xl p-8 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="bg-emerald-100 text-emerald-700 text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Upsell Opportunity
                </span>
                <span className="text-slate-400 text-sm">2 hours ago</span>
              </div>
              <p className="text-xl text-indigo-950 font-medium leading-relaxed mb-6">
                "Customers buying 'Kopi Arabica' are highly receptive to bundling. Activate a 10% bundle discount with 'Gula Aren' to boost AOV."
              </p>
            </div>
            <div className="flex gap-3">
              <button className="flex-1 bg-indigo-600 text-white py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-200">
                Configure Bundle
              </button>
              <button className="flex-1 bg-white border border-indigo-100 text-indigo-600 py-3 rounded-xl font-semibold hover:bg-indigo-50 transition-colors">
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
