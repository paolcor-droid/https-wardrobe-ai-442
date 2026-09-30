"""Customer pricing boundary for LUMIÈRE-owned catalogue products.

Supplier cost is never a customer price. A customer price is created only when
an explicit pricing policy is configured; otherwise it remains unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class PricingPolicy:
    markup_percent: float
    fixed_allowance: float = 0.0
    gst_percent: float = 0.0


def calculate_customer_price(supplier_cost: float | None, policy: PricingPolicy | None) -> float | None:
    if supplier_cost is None or policy is None:
        return None
    if supplier_cost < 0 or policy.markup_percent < 0 or policy.fixed_allowance < 0 or policy.gst_percent < 0:
        raise ValueError("Pricing inputs cannot be negative")

    base = Decimal(str(supplier_cost))
    markup = Decimal(str(policy.markup_percent)) / Decimal("100")
    allowance = Decimal(str(policy.fixed_allowance))
    gst = Decimal(str(policy.gst_percent)) / Decimal("100")
    price = (base * (Decimal("1") + markup) + allowance) * (Decimal("1") + gst)
    return float(price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def apply_customer_price(product: dict, policy: PricingPolicy | None) -> dict:
    result = dict(product)
    result["customer_price"] = calculate_customer_price(product.get("price"), policy)
    return result
