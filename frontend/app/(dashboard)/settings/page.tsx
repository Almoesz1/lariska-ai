"use client";

import React, { useState } from 'react';
import { Bot, Save, ShieldAlert, Sparkles, MessageSquare, Zap } from 'lucide-react';

export default function SettingsPage() {
  const [tone, setTone] = useState("friendly");
  const [floorPrice, setFloorPrice] = useState("80");
  const [escalateToHuman, setEscalateToHuman] = useState(true);

  return (
    <div className="h-full flex flex-col gap-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-serif font-bold text-indigo-950 mb-2">Settings</h1>
        <p className="text-slate-600">Configure your Sales Brain behavior and business rules.</p>
      </div>

      <div className="grid grid-cols-1 gap-8">
        
        {/* Agent Persona Settings */}
        <section className="bg-white/60 backdrop-blur-md rounded-3xl p-8 shadow-xl border border-white">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-indigo-100 rounded-xl">
              <MessageSquare className="w-6 h-6 text-indigo-600" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-indigo-950">Agent Persona</h2>
          </div>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Default Conversation Tone</label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {['formal', 'friendly', 'persuasive'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTone(t)}
                    className={`px-4 py-3 rounded-xl border font-medium capitalize transition-all ${
                      tone === t
                        ? "bg-indigo-50 border-indigo-500 text-indigo-700 shadow-sm"
                        : "bg-white/50 border-white/80 text-slate-600 hover:bg-white hover:shadow-sm"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <p className="text-sm text-slate-500 mt-2">
                This tone will be used by default, but the emotion classifier may dynamically adjust it (e.g., if the customer is angry).
              </p>
            </div>
          </div>
        </section>

        {/* Business Logic Constraints */}
        <section className="bg-white/60 backdrop-blur-md rounded-3xl p-8 shadow-xl border border-white relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-amber-100/30 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
          
          <div className="flex items-center gap-3 mb-6 relative z-10">
            <div className="p-2 bg-amber-100 rounded-xl">
              <ShieldAlert className="w-6 h-6 text-amber-600" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-indigo-950">Business Constraints (Guardrails)</h2>
          </div>
          
          <div className="space-y-6 relative z-10">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                Global Floor Price Modifier (%) 
                <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-bold">Strict Rule</span>
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="50"
                  max="100"
                  value={floorPrice}
                  onChange={(e) => setFloorPrice(e.target.value)}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <span className="text-lg font-bold text-indigo-900 w-12">{floorPrice}%</span>
              </div>
              <p className="text-sm text-slate-500 mt-2">
                The absolute minimum percentage of base price the AI is allowed to offer. The AI will <b>never</b> negotiate below this threshold.
              </p>
            </div>

            <hr className="border-indigo-100/50" />

            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Escalate to Human on Low Confidence</label>
                <p className="text-sm text-slate-500">
                  If the Sales Brain confidence score is below 60%, hand over the chat to a human agent.
                </p>
              </div>
              <button 
                onClick={() => setEscalateToHuman(!escalateToHuman)}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors ${
                  escalateToHuman ? 'bg-indigo-600' : 'bg-slate-300'
                }`}
              >
                <span 
                  className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                    escalateToHuman ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </section>

        {/* Action Buttons */}
        <div className="flex justify-end gap-4 mt-4">
          <button className="px-6 py-3 rounded-xl font-semibold text-slate-600 hover:bg-white/60 transition-colors">
            Reset to Defaults
          </button>
          <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-xl font-bold transition-all shadow-lg shadow-indigo-200">
            <Save className="w-5 h-5" /> Save Changes
          </button>
        </div>

      </div>
    </div>
  );
}
