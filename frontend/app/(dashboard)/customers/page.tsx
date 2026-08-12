"use client";

import React, { useState } from "react";
import { Search, User, Clock, CheckCircle2, ChevronRight, PackageOpen, Sparkles, Phone } from "lucide-react";

// Mock Data
const mockCustomers = [
  {
    id: "CUST-001",
    name: "Ihsan",
    phone: "+62 812-3456-7890",
    loyaltyScore: 8.5,
    totalOrders: 12,
    lastActive: "2 hours ago",
    history: [
      { id: "TRX-1029", product: "Kopi Arabica 1kg", date: "2023-10-12", finalPrice: "Rp 120.000", rounds: 3, status: "completed" },
      { id: "TRX-1015", product: "Gula Aren 500g", date: "2023-09-28", finalPrice: "Rp 35.000", rounds: 1, status: "completed" },
    ],
    recommendations: [
      { product: "Kopi Robusta 1kg", reason: "Often bought together with Arabica", match: "92%" },
      { product: "Filter Kopi V60", reason: "Complementary brewing equipment", match: "85%" }
    ]
  },
  {
    id: "CUST-002",
    name: "Mustofa",
    phone: "+62 813-9876-5432",
    loyaltyScore: 9.2,
    totalOrders: 24,
    lastActive: "1 day ago",
    history: [
      { id: "TRX-0992", product: "Teh Melati Premium", date: "2023-10-10", finalPrice: "Rp 45.000", rounds: 2, status: "completed" },
    ],
    recommendations: [
      { product: "Madu Hutan 250ml", reason: "High conversion for tea buyers", match: "95%" }
    ]
  },
  {
    id: "CUST-003",
    name: "Lugas",
    phone: "+62 856-1122-3344",
    loyaltyScore: 4.0,
    totalOrders: 2,
    lastActive: "5 mins ago",
    history: [
      { id: "TRX-1045", product: "Sirup Frambozen", date: "2023-10-15", finalPrice: "Rp 25.000", rounds: 5, status: "negotiating" },
    ],
    recommendations: [
      { product: "Susu Kental Manis", reason: "Bundle offer to close deal", match: "88%" }
    ]
  }
];

export default function CustomersPage() {
  const [selectedCustomer, setSelectedCustomer] = useState(mockCustomers[0]);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredCustomers = mockCustomers.filter(c =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.phone.includes(searchTerm)
  );

  return (
    <div className="h-full flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-semibold text-indigo-950 mb-1">Customers</h1>
          <p className="text-slate-500 text-xs font-normal">Manage your customer relationships and view AI insights.</p>
        </div>
      </div>

      <div className="flex gap-6 h-[calc(100vh-180px)]">
        {/* Customer List (Left Pane) */}
        <div className="w-1/3 bg-white/60 backdrop-blur-md border border-white rounded-3xl p-6 shadow-xl flex flex-col">
          <div className="relative mb-6">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text"
              placeholder="Search customers..."
              className="w-full pl-10 pr-4 py-2.5 bg-white/50 border border-white/80 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#715bc9]/20 transition-all placeholder:text-slate-400 text-xs font-normal"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
            {filteredCustomers.map(customer => (
              <div
                key={customer.id}
                onClick={() => setSelectedCustomer(customer)}
                className={`p-4 rounded-2xl cursor-pointer transition-all border ${
                  selectedCustomer.id === customer.id
                    ? "bg-white border-2 border-[#715bc9] shadow-md shadow-[#715bc9]/15 text-indigo-950"
                    : "bg-white/50 border-white/80 hover:bg-white hover:shadow-md text-slate-800"
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <h3 className="font-semibold text-sm text-indigo-950">{customer.name}</h3>
                  <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-[#715bc9]/10 text-[#715bc9]">
                    {customer.loyaltyScore} Score
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500 font-normal">
                  <Phone className="w-3.5 h-3.5" />
                  <span>{customer.phone}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Customer Details (Right Pane) */}
        <div className="w-2/3 bg-white/60 backdrop-blur-md border border-white rounded-3xl p-8 shadow-xl overflow-y-auto custom-scrollbar">
          {selectedCustomer ? (
            <div className="space-y-8 relative">
              {/* Profile Header */}
              <div className="flex items-start justify-between pb-6 border-b border-slate-100">
                <div className="flex items-center gap-5">
                  <div className="w-20 h-20 rounded-2xl bg-[#715bc9] text-white flex items-center justify-center shadow-lg shadow-[#715bc9]/25 font-semibold text-3xl">
                    {selectedCustomer.name[0]}
                  </div>
                  <div>
                    <h2 className="text-2xl font-semibold text-indigo-950">{selectedCustomer.name}</h2>
                    <p className="text-slate-500 text-xs font-normal flex items-center gap-2 mt-1">
                      <Phone className="w-4 h-4 text-[#715bc9]" /> {selectedCustomer.phone}
                    </p>
                  </div>
                </div>
                <div className="flex gap-4 text-center">
                  <div className="bg-white/80 backdrop-blur-sm px-4 py-3 rounded-xl border border-slate-200/80 shadow-sm">
                    <p className="text-slate-500 text-[10px] font-semibold uppercase tracking-wider">Total Orders</p>
                    <p className="text-xl font-semibold text-indigo-950">{selectedCustomer.totalOrders}</p>
                  </div>
                  <div className="bg-white/80 backdrop-blur-sm px-4 py-3 rounded-xl border border-slate-200/80 shadow-sm">
                    <p className="text-slate-500 text-[10px] font-semibold uppercase tracking-wider">Last Active</p>
                    <p className="text-xs font-medium text-[#715bc9] mt-1">{selectedCustomer.lastActive}</p>
                  </div>
                </div>
              </div>

              {/* AI Recommendations */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-5 h-5 text-[#715bc9]" />
                  <h3 className="text-xl font-semibold text-indigo-950">AI Recommendations</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {selectedCustomer.recommendations.map((rec, idx) => (
                    <div key={idx} className="bg-white/90 border border-slate-200/80 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
                      <div className="flex justify-between items-start mb-2 relative z-10">
                        <h4 className="font-semibold text-indigo-950 text-sm">{rec.product}</h4>
                        <span className="bg-[#715bc9]/10 text-[#715bc9] text-xs px-2.5 py-0.5 rounded-full font-medium">{rec.match} Match</span>
                      </div>
                      <p className="text-slate-600 text-xs font-normal relative z-10">{rec.reason}</p>
                      <button className="mt-4 text-xs font-medium text-[#715bc9] flex items-center gap-1 group-hover:gap-2 transition-all cursor-pointer">
                        Pitch to Customer <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Transaction History / Memory */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-5 h-5 text-[#715bc9]" />
                  <h3 className="text-xl font-semibold text-indigo-950">Historical Context & Memory</h3>
                </div>
                <div className="bg-white/90 border border-slate-200/80 rounded-2xl overflow-hidden shadow-sm">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 text-indigo-950 border-b border-slate-100 text-xs font-bold uppercase tracking-wider">
                        <th className="px-6 py-4">Order ID</th>
                        <th className="px-6 py-4">Product</th>
                        <th className="px-6 py-4">Final Price</th>
                        <th className="px-6 py-4 text-center">Nego Rounds</th>
                        <th className="px-6 py-4">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-sm">
                      {selectedCustomer.history.map((tx) => (
                        <tr key={tx.id} className="hover:bg-slate-50/80 transition-colors text-slate-700">
                          <td className="px-6 py-4 font-mono font-bold text-[#715bc9]">{tx.id}</td>
                          <td className="px-6 py-4 flex items-center gap-2 font-medium">
                            <PackageOpen className="w-4 h-4 text-slate-400" /> {tx.product}
                          </td>
                          <td className="px-6 py-4 font-bold text-slate-900">{tx.finalPrice}</td>
                          <td className="px-6 py-4 text-center">
                            <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded-md text-xs font-bold">{tx.rounds}</span>
                          </td>
                          <td className="px-6 py-4">
                            {tx.status === 'completed' ? (
                              <span className="flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full text-xs font-bold w-fit">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Completed
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full text-xs font-bold w-fit">
                                <Clock className="w-3.5 h-3.5" /> Negotiating
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-400">
              <User className="w-16 h-16 mb-4 opacity-20" />
              <p>Select a customer to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
