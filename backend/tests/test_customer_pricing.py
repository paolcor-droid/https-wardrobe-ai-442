from services.customer_pricing import PricingPolicy, apply_customer_price, calculate_customer_price


def test_price_is_unavailable_without_explicit_policy():
    assert calculate_customer_price(20.90, None) is None


def test_explicit_policy_calculates_customer_price():
    policy = PricingPolicy(markup_percent=50, fixed_allowance=5, gst_percent=10)
    assert calculate_customer_price(20, policy) == 38.5


def test_pricing_keeps_supplier_cost_separate():
    product = {"external_id": "mh-1", "price": 20.90}
    priced = apply_customer_price(product, PricingPolicy(markup_percent=50))
    assert product["price"] == 20.90
    assert priced["price"] == 20.90
    assert priced["customer_price"] == 31.35
