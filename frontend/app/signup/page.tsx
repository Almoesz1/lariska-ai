"use client";

import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { Bot, ArrowRight, Mail, Lock, User } from 'lucide-react';
import Link from 'next/link';

export default function SignupPage() {
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    gsap.fromTo(cardRef.current, 
      { y: 40, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, ease: 'power3.out' }
    );
  }, []);

  return (
    <div className="min-h-screen bg-[#F8F9FF] font-sans text-slate-900 relative flex items-center justify-center overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-purple-300/30 blur-[120px]" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-300/20 blur-[120px]" />

      {/* Navbar/Logo */}
      <div className="absolute top-8 left-8 flex items-center gap-2">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <Bot className="w-8 h-8 text-indigo-600" />
          <span className="text-2xl font-bold tracking-tight text-indigo-950">LARISKA<span className="text-indigo-600">.</span></span>
        </Link>
      </div>

      <div ref={cardRef} className="relative z-10 w-full max-w-md mx-4">
        <div className="bg-white/70 backdrop-blur-xl border border-white rounded-3xl p-8 shadow-2xl shadow-indigo-100/50">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-serif text-indigo-950 mb-2">Create an Account</h1>
            <p className="text-slate-600">Start automating your sales today</p>
          </div>

          <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 block">Full Name</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-slate-400" />
                </div>
                <input 
                  type="text" 
                  className="w-full pl-10 pr-4 py-3 bg-white/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-700" 
                  placeholder="John Doe" 
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 block">Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-slate-400" />
                </div>
                <input 
                  type="email" 
                  className="w-full pl-10 pr-4 py-3 bg-white/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-700" 
                  placeholder="you@company.com" 
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 block">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input 
                  type="password" 
                  className="w-full pl-10 pr-4 py-3 bg-white/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-700" 
                  placeholder="••••••••" 
                />
              </div>
            </div>

            <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-medium transition-colors shadow-lg shadow-indigo-200 flex items-center justify-center gap-2 group mt-2">
              Sign Up
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="mt-8 text-center text-sm text-slate-600">
            Already have an account?{' '}
            <Link href="/login" className="text-indigo-600 hover:text-indigo-700 font-semibold transition-colors">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
