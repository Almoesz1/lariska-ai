"use client";

import React, { useState } from "react";
import { Search, User, Clock, CheckCircle2, ChevronRight, PackageOpen, Sparkles, Phone } from "lucide-react";

// Mock Data
const mockCustomers = [
  {
    id: "CUST-001",
    name: "Budi Santoso",
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
    name: "Siti Aminah",
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
    name: "Andi Wijaya",
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
          <h1 className="text-4xl font-serif font-bold text-indigo-950 mb-2">Customers</h1>
          <p className="text-slate-600">Manage your customer relationships and view AI insights.</p>
        </div>
      </div>

      <div className="flex gap-6 h-[calc(100vh-180px)]">
        {/* Customer List (Left Pane) */}
        <div className="w-1/3 bg-white/60 backdrop-blur-md border border-white rounded-3xl p-6 shadow-xl flex flex-col">
          <div className="relative mb-6">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input 
              type="text"
              placeholder="Search customers..."
              className="w-full pl-11 pr-4 py-3 bg-white/50 border border-white/80 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-400"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
            {filteredCustomers.map(customer => (
              <div 
                key={customer.id}
                onClick={() => setSelectedCustomer(customer)}
                className={`p-4 rounded-2xl cursor-pointer transition-all duration-200 border ${
                  selectedCustomer.id === customer.id 
                    ? "bg-indigo-600 text-white border-indigo-500 shadow-lg shadow-indigo-200" 
                    : "bg-white/40 border-white/60 hover:bg-white hover:shadow-md text-slate-800"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-lg">{customer.name}</h3>
                  <div className={`text-xs px-2 py-1 rounded-full font-medium ${
                    selectedCustomer.id === customer.id ? "bg-indigo-500 text-white" : "bg-indigo-100 text-indigo-700"
                  }`}>
                    {customer.loyaltyScore} Score
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm opacity-80">
                  <Phone className="w-4 h-4" />
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
              <div className="flex items-start justify-between pb-6 border-b border-indigo-100">
                <div className="flex items-center gap-5">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-200">
                    <User className="w-10 h-10 text-white" />
                  </div>
                  <div>
                    <h2 className="text-3xl font-serif font-bold text-indigo-950">{selectedCustomer.name}</h2>
                    <p className="text-slate-500 text-lg flex items-center gap-2 mt-1">
                      <Phone className="w-5 h-5" /> {selectedCustomer.phone}
                    </p>
                  </div>
                </div>
                <div className="flex gap-4 text-center">
                  <div className="bg-white/50 backdrop-blur-sm px-4 py-3 rounded-xl border border-white shadow-sm">
                    <p className="text-slate-500 text-sm font-medium">Total Orders</p>
                    <p className="text-2xl font-bold text-indigo-900">{selectedCustomer.totalOrders}</p>
                  </div>
                  <div className="bg-white/50 backdrop-blur-sm px-4 py-3 rounded-xl border border-white shadow-sm">
                    <p className="text-slate-500 text-sm font-medium">Last Active</p>
                    <p className="text-lg font-bold text-indigo-900 mt-1">{selectedCustomer.lastActive}</p>
                  </div>
                </div>
              </div>

              {/* AI Recommendations */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-6 h-6 text-purple-600" />
                  <h3 className="text-xl font-bold text-indigo-950">AI Recommendations</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {selectedCustomer.recommendations.map((rec, idx) => (
                    <div key={idx} className="bg-gradient-to-br from-purple-50 to-indigo-50 border border-indigo-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
                      <div className="absolute top-0 right-0 w-24 h-24 bg-white/40 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-purple-200/40 transition-colors" />
                      <div className="flex justify-between items-start mb-2 relative z-10">
                        <h4 className="font-bold text-indigo-900 text-lg">{rec.product}</h4>
                        <span className="bg-purple-100 text-purple-700 text-xs px-2 py-1 rounded-full font-bold">{rec.match} Match</span>
                      </div>
                      <p className="text-slate-600 text-sm relative z-10">{rec.reason}</p>
                      <button className="mt-4 text-sm font-semibold text-indigo-600 flex items-center gap-1 group-hover:gap-2 transition-all">
                        Pitch to Customer <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Transaction History / Memory */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-6 h-6 text-indigo-600" />
                  <h3 className="text-xl font-bold text-indigo-950">Historical Context & Memory</h3>
                </div>
                <div className="bg-white/50 border border-white rounded-2xl overflow-hidden shadow-sm">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-indigo-50/50 text-indigo-900 border-b border-indigo-100 text-sm">
                        <th className="px-6 py-4 font-semibold">Order ID</th>
                        <th className="px-6 py-4 font-semibold">Product</th>
                        <th className="px-6 py-4 font-semibold">Final Price</th>
                        <th className="px-6 py-4 font-semibold text-center">Nego Rounds</th>
                        <th className="px-6 py-4 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-indigo-50">
                      {selectedCustomer.history.map((tx) => (
                        <tr key={tx.id} className="hover:bg-white/60 transition-colors text-slate-700">
                          <td className="px-6 py-4 font-medium">{tx.id}</td>
                          <td className="px-6 py-4 flex items-center gap-2">
                            <PackageOpen className="w-4 h-4 text-slate-400" /> {tx.product}
                          </td>
                          <td className="px-6 py-4 font-semibold text-slate-900">{tx.finalPrice}</td>
                          <td className="px-6 py-4 text-center">
                            <span className="bg-slate-100 text-slate-600 px-2 py-1 rounded-md text-xs font-bold">{tx.rounds}</span>
                          </td>
                          <td className="px-6 py-4">
                            {tx.status === 'completed' ? (
                              <span className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md text-xs font-semibold w-fit">
                                <CheckCircle2 className="w-3 h-3" /> Completed
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-amber-600 bg-amber-50 px-2 py-1 rounded-md text-xs font-semibold w-fit">
                                <Clock className="w-3 h-3" /> Negotiating
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
