"""
LARISKA AI — Sprint 5A
Hard Business Guardrails — Lapis Pertahanan Anti-Rugi

Tugas: Mengunci harga minimum (floor_price) & batas diskon maksimum secara kaku
di level Python/Code, independen dari prediksi ML maupun prompt LLM.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class ProductConstraint:
    product_price: float
    floor_price: float
    max_discount_pct: float = 0.25  # Batas maksimal diskon standar (25%)


def apply_guardrails(
    proposed_action: str,
    requested_discount_pct: float,
    constraint: ProductConstraint,
) -> Dict[str, Any]:
    """Validasi aksi prediksi ML terhadap batasan finansial bisnis.

    Returns dict berisi:
    - final_action: Aksi akhir setelah disaring guardrails
    - final_price: Harga final dalam Rupiah (dijamin >= floor_price)
    - applied_discount_pct: Persentase diskon terpasang
    - guard_reason: Catatan evaluasi guardrails
    - floor_price_locked: True jika harga menyentuh/dikunci di floor_price
    """
    price = float(constraint.product_price)
    floor = float(constraint.floor_price)

    # Sanity check harga
    if price <= 0:
        return {
            "final_action": "hold_price",
            "final_price": 0.0,
            "applied_discount_pct": 0.0,
            "guard_reason": "Harga produk invalid (<= 0)",
            "floor_price_locked": False,
        }

    # Hitung diskon maksimal yang diizinkan oleh batas margin floor_price
    max_margin_discount = max(0.0, (price - floor) / price)
    effective_max_discount = min(constraint.max_discount_pct, max_margin_discount)

    final_action = proposed_action
    applied_discount_pct = 0.0
    guard_reason = "OK"

    if proposed_action == "discount":
        applied_discount_pct = min(requested_discount_pct, effective_max_discount)
        if applied_discount_pct <= 0:
            final_action = "hold_price"
            guard_reason = "Floor price reached. Discount rejected by Guardrails."

    elif proposed_action == "counter_offer":
        # Ambil titik tengah antara diskon yang diminta pembeli dengan batas aman
        applied_discount_pct = min(requested_discount_pct / 2.0, effective_max_discount)
        if applied_discount_pct <= 0:
            final_action = "hold_price"
            guard_reason = "Margin too tight for counter offer."

    elif proposed_action in ["hold_price", "bonus"]:
        applied_discount_pct = 0.0

    # Calculated price & BENTENG UTAMA floor price locking
    calc_price = price * (1.0 - applied_discount_pct)
    final_price = max(calc_price, floor)

    floor_locked = round(final_price, 2) <= round(floor, 2)

    logger.info(
        f"[Guardrails] Proposed={proposed_action} -> Final={final_action} | "
        f"Price: Rp{price:,.0f} -> Rp{final_price:,.0f} (Floor: Rp{floor:,.0f}) | "
        f"Reason: {guard_reason}"
    )

    return {
        "final_action": final_action,
        "original_action": proposed_action,
        "applied_discount_pct": round(applied_discount_pct, 4),
        "final_price": round(final_price, 2),
        "guard_reason": guard_reason,
        "floor_price_locked": floor_locked,
    }