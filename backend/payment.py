import stripe
from config import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY

def create_checkout_session(amount: int, currency: str = "usd"):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": currency,
                "product_data": {"name": "Mehwish Chat API Key"},
                "unit_amount": amount,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="https://yourdomain.com/success",
        cancel_url="https://yourdomain.com/cancel",
    )
    return session
