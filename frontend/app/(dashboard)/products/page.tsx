"use client";

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Bot } from 'lucide-react';

export default function ProductsPage() {
  return (
    <div className="min-h-screen bg-[#F8F9FF] font-sans text-slate-900 flex items-center justify-center overflow-hidden relative">
      {/* Background gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-300/30 blur-[120px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-300/20 blur-[120px]" />

      {/* Header */}
      <div className="absolute top-0 left-8 flex items-center">
        <Link href="/" className="flex items-center hover:opacity-80 transition-opacity">
          <Image src="/logo.png" alt="Lariska" width={500} height={150} className="w-auto h-[120px] -mt-8" priority />
        </Link>
      </div>

      {/* Main Card */}
      <div className="relative z-10 w-full max-w-2xl mx-4 p-8 bg-white/70 backdrop-blur-xl border border-white rounded-3xl shadow-2xl">
        <h1 className="text-3xl font-serif text-indigo-950 mb-4 text-center">Products</h1>
        <p className="text-slate-600 text-center mb-6">This page will list your products. Add your product components here.</p>
        <div className="flex justify-center">
          <Link href="/" className="px-6 py-2 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 transition-colors">Back to Home</Link>
        </div>
      </div>
    </div>
  );
}
