"use client";

import React, { useState, useEffect } from 'react';
import { 
  Bot, Save, User, Lock, Eye, EyeOff, CheckCircle2, 
  Camera, Trash2
} from 'lucide-react';

export default function SettingsPage() {
  // Profile & Avatar States
  const [userName, setUserName] = useState("Manager kopdes");
  const [userEmail, setUserEmail] = useState("admin@lariska.ai");
  const [userAvatar, setUserAvatar] = useState("");

  // Password States
  const [currentPassword, setCurrentPassword] = useState("password123");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  
  // Password Visibility States (Click & Hover)
  const [showCurrent, setShowCurrent] = useState(false);
  const [hoverCurrent, setHoverCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [hoverNew, setHoverNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [hoverConfirm, setHoverConfirm] = useState(false);

  // AI & Guardrails States
  const [tone, setTone] = useState("friendly");
  const [floorPrice, setFloorPrice] = useState("80");
  const [escalateToHuman, setEscalateToHuman] = useState(true);

  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    const savedName = localStorage.getItem("user_name");
    const savedEmail = localStorage.getItem("user_email");
    const savedAvatar = localStorage.getItem("user_avatar");
    if (savedName) setUserName(savedName);
    if (savedEmail) setUserEmail(savedEmail);
    if (savedAvatar) setUserAvatar(savedAvatar);
  }, []);

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        setUserAvatar(base64);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveAvatar = () => {
    setUserAvatar("");
    localStorage.removeItem("user_avatar");
    window.dispatchEvent(new Event("storage"));
  };

  const handleSave = () => {
    localStorage.setItem("user_name", userName);
    localStorage.setItem("user_email", userEmail);
    if (userAvatar) {
      localStorage.setItem("user_avatar", userAvatar);
    } else {
      localStorage.removeItem("user_avatar");
    }
    window.dispatchEvent(new Event("storage"));
    
    if (newPassword && newPassword === confirmPassword) {
      setCurrentPassword(newPassword);
      setNewPassword("");
      setConfirmPassword("");
    }
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="h-full flex flex-col gap-8 max-w-5xl pb-16">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-semibold text-indigo-950 mb-1">Settings & Controls</h1>
          <p className="text-slate-500 text-sm font-normal">Manage your store account profile, security credentials, and Sales Brain AI behavior.</p>
        </div>

        <div className="flex items-center gap-3">
          {savedSuccess && (
            <div className="flex items-center gap-2 bg-emerald-100 text-emerald-800 px-4 py-2.5 rounded-xl text-xs font-semibold border border-emerald-200 animate-fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Settings saved successfully!
            </div>
          )}
          <button 
            onClick={handleSave}
            className="flex items-center gap-2 bg-[#715bc9] hover:bg-[#5f49b5] text-white px-6 py-2.5 rounded-xl font-semibold text-xs shadow-md transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" /> Save Changes
          </button>
        </div>
      </div>

      <div className="space-y-8">
        
        {/* CARD 1: PROFILE INFORMATION */}
        <section className="bg-white/90 backdrop-blur-md rounded-3xl p-9 shadow-lg shadow-indigo-100/30 border border-slate-200/80 hover:shadow-xl transition-all space-y-7">
          <div className="flex items-center gap-4 pb-5 border-b border-slate-100">
            <div className="p-3 bg-[#715bc9]/10 border border-[#715bc9]/20 rounded-2xl">
              <User className="w-6 h-6 text-[#715bc9]" />
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-indigo-950">Profile Information</h2>
              <p className="text-xs text-slate-500 font-normal mt-0.5">Update your store manager photo, display name, and email address.</p>
            </div>
          </div>

          {/* Profile Picture Upload Section */}
          <div className="flex items-center gap-7 p-6 bg-slate-50/80 border border-slate-100 rounded-2xl">
            <div className="relative group shrink-0">
              {userAvatar ? (
                <img src={userAvatar} alt="Profile" className="w-24 h-24 rounded-2xl object-cover border-2 border-[#715bc9] shadow-md" />
              ) : (
                <div className="w-24 h-24 rounded-2xl bg-[#715bc9] text-white flex items-center justify-center font-semibold text-3xl shadow-md">
                  {userName[0]}
                </div>
              )}
              <label className="absolute -bottom-2 -right-2 bg-[#715bc9] hover:bg-[#5f49b5] text-white p-2.5 rounded-xl shadow-md cursor-pointer transition-all">
                <Camera className="w-4 h-4" />
                <input type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
              </label>
            </div>

            <div className="space-y-1">
              <h4 className="font-semibold text-indigo-950 text-base">Store Avatar Photo</h4>
              <p className="text-slate-500 text-xs font-normal">Upload a high-resolution JPG or PNG photo to customize your avatar across the app.</p>
              <div className="flex gap-3 pt-2">
                <label className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold px-4 py-2 rounded-xl cursor-pointer transition-all shadow-sm">
                  Upload Photo
                  <input type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
                </label>
                {userAvatar && (
                  <button onClick={handleRemoveAvatar} className="bg-rose-50 text-rose-600 border border-rose-200 hover:bg-rose-100 text-xs font-semibold px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 cursor-pointer">
                    <Trash2 className="w-3.5 h-3.5" /> Remove Photo
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Profile Name & Email */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Full Name / Display Name</label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="w-full px-4.5 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#715bc9]/20 focus:border-[#715bc9] transition-all"
                placeholder="Manager kopdes"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Email Address</label>
              <input
                type="email"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                className="w-full px-4.5 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#715bc9]/20 focus:border-[#715bc9] transition-all"
                placeholder="admin@lariska.ai"
              />
            </div>
          </div>
        </section>

        {/* CARD 2: PASSWORD SECURITY */}
        <section className="bg-white/90 backdrop-blur-md rounded-3xl p-9 shadow-lg shadow-indigo-100/30 border border-slate-200/80 hover:shadow-xl transition-all space-y-7">
          <div className="flex items-center gap-4 pb-5 border-b border-slate-100">
            <div className="p-3 bg-purple-100 border border-purple-200/60 rounded-2xl">
              <Lock className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-indigo-950">Password & Security</h2>
              <p className="text-xs text-slate-500 font-normal mt-0.5">Manage and change your password credentials to protect your store.</p>
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Current Password</label>
              <div className="relative max-w-md">
                <input
                  type={showCurrent || hoverCurrent ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full pl-4.5 pr-12 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#715bc9]/20 focus:border-[#715bc9] transition-all"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onMouseEnter={() => setHoverCurrent(true)}
                  onMouseLeave={() => setHoverCurrent(false)}
                  onClick={() => setShowCurrent(!showCurrent)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                >
                  {showCurrent || hoverCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">New Password</label>
                <div className="relative">
                  <input
                    type={showNew || hoverNew ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full pl-4.5 pr-12 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#715bc9]/20 focus:border-[#715bc9] transition-all"
                    placeholder="Enter new password"
                  />
                  <button
                    type="button"
                    onMouseEnter={() => setHoverNew(true)}
                    onMouseLeave={() => setHoverNew(false)}
                    onClick={() => setShowNew(!showNew)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                  >
                    {showNew || hoverNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Confirm New Password</label>
                <div className="relative">
                  <input
                    type={showConfirm || hoverConfirm ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pl-4.5 pr-12 py-3 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#715bc9]/20 focus:border-[#715bc9] transition-all"
                    placeholder="Confirm new password"
                  />
                  <button
                    type="button"
                    onMouseEnter={() => setHoverConfirm(true)}
                    onMouseLeave={() => setHoverConfirm(false)}
                    onClick={() => setShowConfirm(!showConfirm)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                  >
                    {showConfirm || hoverConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CARD 3: SALES BRAIN AI GUARDRAILS */}
        <section className="bg-white/90 backdrop-blur-md rounded-3xl p-9 shadow-lg shadow-indigo-100/30 border border-slate-200/80 hover:shadow-xl transition-all space-y-7">
          <div className="flex items-center gap-4 pb-5 border-b border-slate-100">
            <div className="p-3 bg-amber-100 border border-amber-200/60 rounded-2xl">
              <Bot className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-indigo-950">Sales Brain AI Guardrails</h2>
              <p className="text-xs text-slate-500 font-normal mt-0.5">Configure AI negotiation rules, conversation tone, and human escalation threshold.</p>
            </div>
          </div>

          <div className="space-y-7">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Default Conversation Tone</label>
              <div className="grid grid-cols-3 gap-4">
                {['formal', 'friendly', 'persuasive'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTone(t)}
                    className={`py-3 px-5 rounded-2xl text-xs font-semibold capitalize transition-all border cursor-pointer ${
                      tone === t
                        ? "bg-[#715bc9] text-white border-[#715bc9] shadow-md"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-500 font-normal mt-2.5">
                This tone will be used by default during WhatsApp negotiations, with dynamic emotional adjustments.
              </p>
            </div>

            <hr className="border-slate-100" />

            <div>
              <div className="flex justify-between items-center mb-3">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                  Global Floor Price Modifier (%) 
                  <span className="text-[10px] bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full font-semibold">Strict Rule</span>
                </label>
                <span className="text-base font-semibold text-[#715bc9]">{floorPrice}% minimum</span>
              </div>
              <input
                type="range"
                min="50"
                max="100"
                value={floorPrice}
                onChange={(e) => setFloorPrice(e.target.value)}
                className="w-full h-2.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#715bc9]"
              />
              <p className="text-xs text-slate-500 font-normal mt-2">
                The absolute minimum percentage of base price the AI is allowed to offer. The AI will <b>never</b> negotiate below this limit.
              </p>
            </div>

            <hr className="border-slate-100" />

            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-semibold text-indigo-950 mb-1">Escalate to Human on Low Confidence</label>
                <p className="text-xs text-slate-500 font-normal">
                  If the Sales Brain confidence score drops below 60%, automatically hand over the chat to a human agent.
                </p>
              </div>
              <button 
                onClick={() => setEscalateToHuman(!escalateToHuman)}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors cursor-pointer ${
                  escalateToHuman ? 'bg-[#715bc9]' : 'bg-slate-300'
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

      </div>
    </div>
  );
}


