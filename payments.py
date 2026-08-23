import os
import razorpay
from dotenv import load_dotenv

load_dotenv()


class PaymentProcessor:
    """Wraps Razorpay test mode. Only ever called after the gate says ALLOW."""

    def __init__(self):
        self.client = razorpay.Client(auth=(
            os.environ["RAZORPAY_KEY_ID"],
            os.environ["RAZORPAY_KEY_SECRET"],
        ))

    def create_order(self, amount_paise, receipt, notes=None):
        return self.client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes or {},
            "payment_capture": 1,
        })