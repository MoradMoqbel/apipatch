# target_stripe.py - Simulated e-commerce checkout with deprecated Stripe Charge API

# pyrefly: ignore [missing-import]
import stripe

stripe.api_key = "sk_test_12345"

def process_credit_card_payment(amount_cents: int, card_token: str):
    """
    DEPRECATED STRIPE CHARGE API
    Stripe deprecated Charge.create in favor of PaymentIntents.
    This breaks in modern Stripe API compliance.
    """
    print(f"Charging customer ${amount_cents / 100:.2f}...")
    
    # DEPRECATED STRIPE CALL:
    charge = stripe.Charge.create(
        amount=amount_cents,
        currency="usd",
        source=card_token,
        description="Software Subscription Purchase"
    )
    
    return charge.id

if __name__ == "__main__":
    try:
        charge_id = process_credit_card_payment(2900, "tok_visa")
        print("Payment successful:", charge_id)
    except Exception as e:
        print("Stripe Error:", e)
