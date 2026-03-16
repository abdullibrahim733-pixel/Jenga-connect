import logging
import os
import hmac
import hashlib
from typing import Dict, Optional

from .models import Payment

logger = logging.getLogger(__name__)


class PaymentGateway:
    def initiate(self, payment: Payment) -> Dict:
        raise NotImplementedError

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "")
        if not secret or not signature:
            return False
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


class MobileMoneyGateway(PaymentGateway):
    def initiate(self, payment: Payment) -> Dict:
        logger.info("Initiating mobile money payment %s", payment.id)
        return {"status": "initiated", "payment_id": str(payment.id)}


class CardGateway(PaymentGateway):
    def initiate(self, payment: Payment) -> Dict:
        logger.info("Initiating card payment %s", payment.id)
        return {"status": "initiated", "payment_id": str(payment.id)}


def get_gateway(method: str) -> PaymentGateway:
    if method == "card":
        return CardGateway()
    return MobileMoneyGateway()


def initiate_payment(payment: Payment) -> Dict:
    gateway = get_gateway(payment.method)
    return gateway.initiate(payment)
