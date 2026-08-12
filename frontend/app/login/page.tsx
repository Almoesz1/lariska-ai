"use client";

import React, { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
<<<<<<< HEAD
import { ArrowRight, Mail, Lock, Eye, EyeOff } from 'lucide-react';
=======
import { Bot, ArrowRight, Mail, Lock, Eye, EyeOff } from 'lucide-react';
>>>>>>> 1bbde33 (update login page)
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const cardRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    gsap.fromTo(cardRef.current,
      { y: 40, opacity: 0 },
      { y: 0, opacity: 1, duration: 1, ease: 'power3.out' }
    );
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    router.push('/products');
  };

  return (
    <div className="min-h-screen bg-[#F8F9FF] font-sans text-slate-900 relative flex items-center justify-center overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-300/30 blur-[120px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-300/20 blur-[120px]" />

      {/* Navbar/Logo */}
      <div className="absolute top-8 left-8 flex items-center">
        <Link href="/" className="flex items-center hover:opacity-80 transition-opacity">
          <Image src="/logo.png" alt="Lariska" width={500} height={150} className="w-auto h-[120px]" priority />
        </Link>
      </div>

      <div ref={cardRef} className="relative z-10 w-full max-w-md mx-4">
        <div className="bg-white/70 backdrop-blur-xl border border-white rounded-3xl p-8 shadow-2xl shadow-indigo-100/50">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-serif text-indigo-950 mb-2">Welcome Back</h1>
            <p className="text-slate-600">Sign in to your LARISKA account</p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 block">Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="email"
                  defaultValue="admin@lariska.ai"
                  className="w-full pl-10 pr-4 py-3 bg-white/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-700"
                  placeholder="you@company.com"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700 block">Password</label>
                <Link href="#" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">Forgot?</Link>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  defaultValue="password123"
                  className="w-full pl-10 pr-12 py-3 bg-white/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-slate-700"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-medium transition-colors shadow-lg shadow-indigo-200 flex items-center justify-center gap-2 group mt-2">
              Sign In
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="mt-8 text-center text-sm text-slate-600">
            Don&apos;t have an account?{' '}
            <Link href="/signup" className="text-indigo-600 hover:text-indigo-700 font-semibold transition-colors">
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
