"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Sparkles, Trash2, Mail, ArrowRight, Settings, Plus, Download } from "lucide-react";

export default function ButtonShowcasePage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-10 flex flex-col gap-10 font-sans">
      <div className="max-w-4xl mx-auto w-full space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
            shadcn/ui Button Component Showcase
          </h1>
          <p className="text-slate-400">
            Visual preview of all variants, sizes, and states defined in <code className="text-indigo-400">button.tsx</code>.
          </p>
        </div>

        {/* Variants Section */}
        <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl backdrop-blur-md">
          <h2 className="text-xl font-semibold text-slate-200 border-b border-slate-800 pb-2">
            1. Button Variants
          </h2>
          <div className="flex flex-wrap items-center gap-4 pt-2">
            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">default</span>
              <Button variant="default">
                <Sparkles className="w-4 h-4 mr-1" /> Primary Button
              </Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">secondary</span>
              <Button variant="secondary">
                <Settings className="w-4 h-4 mr-1" /> Secondary
              </Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">outline</span>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-1" /> Outline
              </Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">ghost</span>
              <Button variant="ghost">Ghost Button</Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">destructive</span>
              <Button variant="destructive">
                <Trash2 className="w-4 h-4 mr-1" /> Destructive
              </Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">link</span>
              <Button variant="link">
                Link Button <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        </section>

        {/* Sizes Section */}
        <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl backdrop-blur-md">
          <h2 className="text-xl font-semibold text-slate-200 border-b border-slate-800 pb-2">
            2. Button Sizes
          </h2>
          <div className="flex flex-wrap items-end gap-4 pt-2">
            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">xs</span>
              <Button size="xs">Extra Small (xs)</Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">sm</span>
              <Button size="sm">Small (sm)</Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">default</span>
              <Button size="default">Default</Button>
            </div>

            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-slate-500 font-mono">lg</span>
              <Button size="lg">Large (lg)</Button>
            </div>
          </div>
        </section>

        {/* Icon Sizes Section */}
        <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl backdrop-blur-md">
          <h2 className="text-xl font-semibold text-slate-200 border-b border-slate-800 pb-2">
            3. Icon Buttons
          </h2>
          <div className="flex flex-wrap items-end gap-4 pt-2">
            <div className="flex flex-col gap-1 items-center">
              <span className="text-xs text-slate-500 font-mono">icon-xs</span>
              <Button size="icon-xs" variant="outline"><Plus /></Button>
            </div>

            <div className="flex flex-col gap-1 items-center">
              <span className="text-xs text-slate-500 font-mono">icon-sm</span>
              <Button size="icon-sm" variant="outline"><Mail /></Button>
            </div>

            <div className="flex flex-col gap-1 items-center">
              <span className="text-xs text-slate-500 font-mono">icon (default)</span>
              <Button size="icon" variant="outline"><Settings /></Button>
            </div>

            <div className="flex flex-col gap-1 items-center">
              <span className="text-xs text-slate-500 font-mono">icon-lg</span>
              <Button size="icon-lg" variant="outline"><Sparkles /></Button>
            </div>
          </div>
        </section>

        {/* States Section */}
        <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl backdrop-blur-md">
          <h2 className="text-xl font-semibold text-slate-200 border-b border-slate-800 pb-2">
            4. Disabled & Special States
          </h2>
          <div className="flex flex-wrap items-center gap-4 pt-2">
            <Button disabled variant="default">Disabled Primary</Button>
            <Button disabled variant="outline">Disabled Outline</Button>
            <Button disabled variant="destructive">Disabled Destructive</Button>
          </div>
        </section>
      </div>
    </div>
  );
}
