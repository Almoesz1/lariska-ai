"use client";

import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { TextPlugin } from 'gsap/TextPlugin';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Play, ArrowRight, MessageSquare, Bot, Zap, Brain, Mic, CheckCircle2, ChevronDown } from 'lucide-react';
import Link from 'next/link';

if (typeof window !== "undefined") {
  gsap.registerPlugin(TextPlugin, ScrollTrigger);
}

export default function LandingPage() {
  const msg1Ref = useRef<HTMLParagraphElement>(null);
  const msg2Ref = useRef<HTMLParagraphElement>(null);
  const msg3Ref = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    // 1. Chat Animation
    const tl = gsap.timeline({ repeat: -1, repeatDelay: 4 });

    tl.set(msg1Ref.current, { text: "" })
      .to(msg1Ref.current, {
        text: "Halo Kak! Ada yang bisa Lariska bantu? Produk yang kakak tanyakan ready stok 15 pcs nih.",
        duration: 2.5,
        ease: "none"
      })
      .set(msg2Ref.current, { text: "" })
      .to(msg2Ref.current, {
        text: "Bisa kurang gak kak harganya? Jadi 150rb aja deh kalo boleh lgsg trf.",
        duration: 2,
        ease: "none",
        delay: 0.5
      })
      .set(msg3Ref.current, { text: "" })
      .to(msg3Ref.current, {
        text: "Waduh kak, harga pasnya 165rb nih, udah best price banget. Kalo setuju, Lariska kasih free ongkir deh! Gimana kak? 😄",
        duration: 3,
        ease: "none",
        delay: 0.5
      });

    // 2. Scroll Animations for Captions
    const captions = gsap.utils.toArray('.animate-caption');
    captions.forEach((caption: any) => {
      gsap.fromTo(caption, 
        { y: 40, opacity: 0 },
        {
          scrollTrigger: {
            trigger: caption,
            start: 'top 85%',
            toggleActions: "play none none reverse"
          },
          y: 0,
          opacity: 1,
          duration: 1,
          ease: 'power3.out'
        }
      );
    });

    // 3. Animate logos sequentially
    gsap.fromTo(".animate-logo", 
      { y: 20, opacity: 0 },
      {
        scrollTrigger: {
          trigger: ".logos-container",
          start: "top 90%",
        },
        y: 0,
        opacity: 1,
        stagger: 0.15,
        duration: 0.8,
        ease: "back.out(1.5)"
      }
    );

    return () => {
      tl.kill();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#F8F9FF] font-sans text-slate-900 relative overflow-x-clip">
      {/* Background gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-300/30 blur-[120px]" />
      <div className="absolute top-[20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-300/20 blur-[120px]" />
      <div className="absolute bottom-[-10%] left-[20%] w-[50%] h-[50%] rounded-full bg-blue-300/20 blur-[120px]" />

      {/* Navbar */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <Bot className="w-8 h-8 text-indigo-600" />
          <span className="text-2xl font-bold tracking-tight text-indigo-950">LARISKA<span className="text-indigo-600">.</span></span>
        </div>

        <div className="hidden md:flex items-center gap-8 bg-white/50 backdrop-blur-md px-8 py-3 rounded-full border border-white/50 shadow-sm">
          <Link href="#home" className="text-sm font-medium text-slate-700 hover:text-indigo-600">Home</Link>
          <Link href="#features" className="text-sm font-medium text-slate-700 hover:text-indigo-600">Features</Link>
          <Link href="#why" className="text-sm font-medium text-slate-700 hover:text-indigo-600">Why LARISKA</Link>
          <Link href="#pricing" className="text-sm font-medium text-slate-700 hover:text-indigo-600">Pricing</Link>
        </div>

        <div className="flex items-center gap-4">
          <Link href="/login" className="hidden md:block text-sm font-medium text-slate-700 hover:text-indigo-600">Login</Link>
          <Link href="/signup" className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-full text-sm font-medium transition-all shadow-md shadow-indigo-200">
            Sign Up
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main id="home" className="relative z-10 flex flex-col items-center justify-center text-center px-4 pt-24 pb-16 max-w-5xl mx-auto">
        <h1 className="text-5xl md:text-7xl font-serif text-indigo-950 leading-tight mb-6 tracking-tight">
          Automate, Engage, and <br />
          <span className="italic font-light">Grow with AI Chat</span>
        </h1>
        <p className="text-lg md:text-xl text-slate-600 max-w-2xl mb-10">
          Meet LARISKA, the Sales Intelligence Platform for Indonesian SMEs. Your digital sales agent that understands customers, negotiates naturally, and closes deals via WhatsApp.
        </p>

        <div className="flex items-center gap-4">
          <Link href="/signup" className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3.5 rounded-full text-base font-medium transition-all shadow-lg shadow-indigo-200 flex items-center gap-2">
            Try It Free
          </Link>
          <button className="bg-white/70 hover:bg-white text-indigo-950 px-8 py-3.5 rounded-full text-base font-medium transition-all shadow-sm flex items-center gap-2 border border-slate-100">
            <div className="bg-indigo-100 rounded-full p-1"><Play className="w-4 h-4 text-indigo-600 fill-indigo-600" /></div>
            Watch Demo
          </button>
        </div>

        {/* Hero Image/Mockup */}
        <div className="mt-20 w-full max-w-4xl bg-white/60 backdrop-blur-xl border border-white rounded-3xl p-6 shadow-2xl shadow-indigo-100/50 hover:shadow-indigo-200/60 hover:scale-[1.01] transition-all duration-500 group cursor-default">
          <div className="flex items-center gap-3 border-b border-slate-100 pb-4 mb-4">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-slate-300 group-hover:bg-red-400 transition-colors duration-300"></div>
              <div className="w-3 h-3 rounded-full bg-slate-300 group-hover:bg-amber-400 transition-colors duration-300 delay-75"></div>
              <div className="w-3 h-3 rounded-full bg-slate-300 group-hover:bg-green-400 transition-colors duration-300 delay-150"></div>
            </div>
            <div className="text-sm text-slate-400 font-medium ml-2">WhatsApp Web - Lariska Sales Brain</div>
          </div>
          <div className="space-y-4 text-left">
            <div className="flex gap-4 group/msg">
              <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 group-hover/msg:bg-indigo-200 transition-colors duration-300">
                <Bot className="w-5 h-5 text-indigo-600 group-hover/msg:scale-110 group-hover/msg:rotate-3 transition-transform duration-300" />
              </div>
              <div className="bg-white p-4 rounded-2xl rounded-tl-none shadow-sm border border-slate-50 w-full max-w-lg group-hover/msg:-translate-y-1 group-hover/msg:shadow-md transition-all duration-300">
                <p ref={msg1Ref} className="text-slate-700 min-h-[48px]"></p>
              </div>
            </div>
            <div className="flex gap-4 flex-row-reverse group/msg2">
              <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 group-hover/msg2:bg-slate-300 transition-colors duration-300">
                <span className="text-slate-500 font-medium">U</span>
              </div>
              <div className="bg-indigo-600 text-white p-4 rounded-2xl rounded-tr-none shadow-sm w-full max-w-lg group-hover/msg2:-translate-y-1 group-hover/msg2:shadow-md transition-all duration-300">
                <p ref={msg2Ref} className="min-h-[48px]"></p>
              </div>
            </div>
            <div className="flex gap-4 group/msg3">
              <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 group-hover/msg3:bg-indigo-200 transition-colors duration-300">
                <Bot className="w-5 h-5 text-indigo-600 group-hover/msg3:scale-110 group-hover/msg3:-rotate-3 transition-transform duration-300" />
              </div>
              <div className="bg-white p-4 rounded-2xl rounded-tl-none shadow-sm border border-slate-50 w-full max-w-lg group-hover/msg3:-translate-y-1 group-hover/msg3:shadow-md transition-all duration-300">
                <p ref={msg3Ref} className="text-slate-700 min-h-[72px]"></p>
              </div>
            </div>
          </div>
        </div>

        {/* Integration Logos */}
        <div className="mt-24 text-center w-full">
          <p className="text-sm font-semibold tracking-wider text-slate-500 uppercase mb-8 flex items-center justify-center gap-2">
            <Zap className="w-4 h-4 text-amber-400 fill-amber-400" />
            Connect LARISKA to the apps you love
          </p>
          <div className="logos-container flex flex-wrap justify-center gap-12 items-center opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
            <div className="animate-logo text-2xl font-bold font-serif">WhatsApp</div>
            <div className="animate-logo text-2xl font-bold tracking-tight">Supabase</div>
            <div className="animate-logo text-xl font-bold font-mono">Midtrans</div>
            <div className="animate-logo text-2xl font-bold italic">Meta</div>
          </div>
        </div>
      </main>

      {/* Features Section */}
      <section id="features" className="relative z-10 py-24 max-w-7xl mx-auto px-8">
        <div className="animate-caption text-center mb-16">
          <h2 className="text-4xl font-serif text-indigo-950 mb-4">Powerful Features</h2>
          <h3 className="text-3xl italic text-slate-600 font-light">Effortless Conversations</h3>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          <FeatureCard
            icon={<Mic className="w-6 h-6 text-indigo-600" />}
            title="Speech-to-Text"
            description="Process WhatsApp voice notes effortlessly. LARISKA translates spoken audio into text so your business never misses an order."
          />
          <FeatureCard
            icon={<Brain className="w-6 h-6 text-indigo-600" />}
            title="Sales Brain"
            description="Adaptive negotiation engine. LARISKA decides pricing actions, discount levels, and offers bonuses autonomously."
          />
          <FeatureCard
            icon={<MessageSquare className="w-6 h-6 text-indigo-600" />}
            title="Emotion Classifier"
            description="Adapts tone based on customer mood. Whether they are rushed, relaxed, or angry, LARISKA adjusts perfectly."
          />
        </div>
      </section>

      {/* Why Lariska */}
      <section id="why" className="relative z-10 py-24 bg-white/40 backdrop-blur-sm border-y border-white">
        <div className="max-w-7xl mx-auto px-8 grid lg:grid-cols-2 gap-16 items-center">
          <div className="animate-caption">
            <h2 className="text-4xl font-serif text-indigo-950 mb-6">Why LARISKA?</h2>
            <p className="text-lg text-slate-600 mb-8">
              Smart. Reliable. Scalable. LARISKA is the AI partner that transforms the way your business communicates, handling multiple chats concurrently without losing the human touch.
            </p>

            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <Zap className="w-6 h-6 text-indigo-600" />
                </div>
                <div>
                  <h4 className="text-xl font-semibold text-indigo-950 mb-2">Fast Response</h4>
                  <p className="text-slate-600">Meets customer demands instantly, delivering personalized replies within seconds.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h4 className="text-xl font-semibold text-indigo-950 mb-2">Automated Invoicing</h4>
                  <p className="text-slate-600">Generates invoices and QRIS payment links automatically when deals are closed.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="relative group cursor-pointer animate-caption">
            <div className="absolute inset-0 bg-indigo-400/10 blur-2xl rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <div className="relative bg-white/80 backdrop-blur-xl border border-white rounded-3xl p-8 shadow-xl shadow-indigo-100/50 group-hover:-translate-y-2 group-hover:shadow-2xl group-hover:shadow-indigo-200/60 transition-all duration-500">
              <div className="mb-6 flex justify-between items-center">
                <div className="font-medium text-slate-800">Say Hello to <span className="font-serif italic text-indigo-600">Effortless AI</span>.</div>
              </div>
              <div className="bg-slate-50 rounded-2xl p-6 border border-slate-100 overflow-hidden">
                <div className="flex flex-col gap-4">
                  <div className="bg-indigo-600 text-white p-3 px-4 rounded-2xl rounded-br-none self-end max-w-[80%] text-sm shadow-sm hover:scale-[1.03] origin-bottom-right transition-transform duration-300">
                    Hi kak, mau order dong.
                  </div>
                  <div className="bg-white p-3 px-4 rounded-2xl rounded-bl-none self-start max-w-[80%] text-sm border border-slate-100 shadow-sm hover:scale-[1.03] origin-top-left transition-transform duration-300">
                    Tentu kak! Produk apa yang ingin dipesan?
                  </div>
                  <div className="bg-indigo-600 text-white p-3 px-4 rounded-2xl rounded-br-none self-end max-w-[80%] text-sm shadow-sm flex items-center gap-2 hover:scale-[1.03] origin-bottom-right transition-transform duration-300">
                    <Mic className="w-4 h-4" /> 0:04 Voice note
                  </div>
                  <div className="bg-white p-3 px-4 rounded-2xl rounded-bl-none self-start max-w-[80%] text-sm border border-slate-100 shadow-sm flex items-center gap-2 text-indigo-600 font-medium hover:scale-[1.03] origin-top-left transition-transform duration-300">
                    Processing audio... <Brain className="w-4 h-4 animate-pulse" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="relative z-10 py-24 max-w-7xl mx-auto px-8">
        <div className="animate-caption text-center mb-16">
          <h2 className="text-4xl font-serif text-indigo-950 mb-4">Flexible Pricing for Every Need</h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Choose a plan that fits your needs. Whether you're a single seller just starting out or a business seeking advanced features.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:max-w-4xl mx-auto gap-8">
          {/* Pro Plan */}
          <div className="bg-white rounded-3xl p-8 shadow-xl shadow-indigo-100/40 border border-slate-100 relative">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-indigo-100 text-indigo-700 px-4 py-1 rounded-full text-sm font-semibold">Pro Plan</div>
            <div className="mt-4 mb-6">
              <span className="text-5xl font-bold text-indigo-950">Rp 299k</span>
              <span className="text-slate-500"> /mo</span>
            </div>
            <div className="space-y-4 mb-8">
              <PricingFeature text="Up to 1,000 conversations / month" />
              <PricingFeature text="WhatsApp Cloud API Integration" />
              <PricingFeature text="Sales Brain + Emotion Classifier" />
              <PricingFeature text="Voice Note Support (Whisper)" />
              <PricingFeature text="Business Copilot Insights" />
            </div>
            <button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-medium transition-colors">
              Upgrade to Pro
            </button>
          </div>

          {/* Enterprise Plan */}
          <div className="bg-white/60 backdrop-blur-sm rounded-3xl p-8 border border-white">
            <div className="inline-block bg-slate-100 text-slate-700 px-4 py-1 rounded-full text-sm font-semibold mb-6">Enterprise Plan</div>
            <div className="mb-6">
              <span className="text-4xl font-bold text-indigo-950">Custom</span>
              <span className="text-slate-500"> (Contact Us)</span>
            </div>
            <div className="space-y-4 mb-8">
              <PricingFeature text="Unlimited conversations" />
              <PricingFeature text="Custom Model Training (ASE)" />
              <PricingFeature text="Dedicated Account Manager" />
              <PricingFeature text="SLA-backed performance guarantees" />
              <PricingFeature text="24/7 Priority Support" />
            </div>
            <button className="w-full bg-white hover:bg-slate-50 text-indigo-950 py-3 rounded-xl font-medium border border-slate-200 transition-colors">
              Contact us
            </button>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="relative z-10 py-24 max-w-3xl mx-auto px-8">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-serif text-indigo-950 mb-4">Frequently Asked Questions</h2>
          <p className="text-slate-600">Smart. Reliable. Scalable. LARISKA is the AI partner that transforms the way your business communicates.</p>
        </div>

        <div className="space-y-4">
          <FAQItem question="What is LARISKA AI?" answer="LARISKA AI is a Sales Intelligence Platform that gives Indonesian SMEs a digital sales agent capable of understanding customers, making adaptive business decisions, and communicating naturally via WhatsApp." />
          <FAQItem question="How can LARISKA help my business?" answer="It acts as an autonomous sales agent that can handle negotiations, product recommendations, process voice notes, and automatically generate invoices to close deals." />
          <FAQItem question="Can LARISKA be customized for my company's needs?" answer="Yes! You can configure base prices, floor prices, and custom product catalogs which the Sales Brain will use during negotiations." />
          <FAQItem question="Is my business data safe with LARISKA?" answer="Absolutely. We comply with Indonesian UU PDP and never share your negotiation logic or customer data with other users." />
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-12 text-center border-t border-slate-200/50">
        <p className="text-slate-500 text-sm">© 2026 LARISKA AI. All rights reserved.</p>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="bg-white/70 backdrop-blur-sm border border-white rounded-3xl p-8 hover:shadow-xl hover:shadow-indigo-100/50 transition-all duration-300">
      <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6">
        {icon}
      </div>
      <h4 className="text-xl font-semibold text-indigo-950 mb-3">{title}</h4>
      <p className="text-slate-600 leading-relaxed">{description}</p>
    </div>
  );
}

function PricingFeature({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3">
      <CheckCircle2 className="w-5 h-5 text-indigo-500 flex-shrink-0" />
      <span className="text-slate-600">{text}</span>
    </div>
  );
}

function FAQItem({ question, answer }: { question: string, answer: string }) {
  return (
    <div className="bg-white/80 backdrop-blur-sm border border-slate-100 rounded-2xl p-6 hover:shadow-md transition-shadow cursor-pointer group">
      <div className="flex justify-between items-center">
        <h5 className="font-semibold text-indigo-950">{question}</h5>
        <ChevronDown className="w-5 h-5 text-slate-400 group-hover:text-indigo-600 transition-colors" />
      </div>
      <div className="mt-4 text-slate-600 text-sm hidden group-hover:block">
        {answer}
      </div>
    </div>
  );
}
