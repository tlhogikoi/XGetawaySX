"""Server-side payment gateway adapters for PayFast and Yoco.

Secrets are read from Django settings/environment and are never returned to clients.
"""
import hashlib
import hmac
import json
import socket
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class GatewayError(Exception):
    pass


def _setting(name, default=""):
    return getattr(settings, name, default)


def build_payfast_checkout(payment):
    merchant_id = _setting("PAYFAST_MERCHANT_ID")
    merchant_key = _setting("PAYFAST_MERCHANT_KEY")
    if not merchant_id or not merchant_key:
        raise ImproperlyConfigured("PayFast merchant credentials are not configured.")
    if not _setting("PAYFAST_NOTIFY_URL"):
        raise ImproperlyConfigured("PAYFAST_NOTIFY_URL must point to the public PayFast webhook endpoint.")
    sandbox = bool(_setting("PAYFAST_SANDBOX", True))
    fields = {
        "merchant_id": merchant_id,
        "merchant_key": merchant_key,
        "return_url": _setting("PAYMENT_RETURN_URL"),
        "cancel_url": _setting("PAYMENT_CANCEL_URL"),
        "notify_url": _setting("PAYFAST_NOTIFY_URL"),
        "m_payment_id": str(payment.pk),
        "amount": f"{payment.amount:.2f}",
        "item_name": f"XGetawaySX reservation {payment.reservation_id}"[:100],
    }
    fields = {key: str(value).strip() for key, value in fields.items() if value not in (None, "")}
    signature_source = "&".join(f"{key}={__import__('urllib.parse', fromlist=['quote_plus']).quote_plus(value)}" for key, value in fields.items())
    passphrase = _setting("PAYFAST_PASSPHRASE")
    if passphrase:
        from urllib.parse import quote_plus
        signature_source += "&passphrase=" + quote_plus(str(passphrase).strip())
    fields["signature"] = hashlib.md5(signature_source.encode("utf-8")).hexdigest()
    action = "https://sandbox.payfast.co.za/eng/process" if sandbox else "https://www.payfast.co.za/eng/process"
    return {"checkout_url": action, "form_fields": fields, "checkout_session_id": str(payment.pk)}


def create_yoco_checkout(payment):
    secret = _setting("YOCO_SECRET_KEY")
    if not secret:
        raise ImproperlyConfigured("Yoco secret key is not configured.")
    if payment.currency != "ZAR":
        raise GatewayError("Yoco Checkout API currently supports ZAR only.")
    amount_cents = int((payment.amount * Decimal("100")).quantize(Decimal("1")))
    payload = {
        "amount": amount_cents,
        "currency": payment.currency,
        "clientReferenceId": str(payment.pk),
        "externalId": str(payment.pk),
        "metadata": {"paymentId": str(payment.pk), "reservationId": str(payment.reservation_id)},
    }
    for key, setting_name in (
        ("successUrl", "PAYMENT_RETURN_URL"),
        ("cancelUrl", "PAYMENT_CANCEL_URL"),
        ("failureUrl", "PAYMENT_FAILURE_URL"),
    ):
        value = _setting(setting_name)
        if value:
            payload[key] = value
    request = Request(
        "https://payments.yoco.com/api/checkouts",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
            "Idempotency-Key": payment.idempotency_key[:128],
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise GatewayError("Yoco checkout could not be created. Retry using the same payment record.") from exc
    redirect_url = result.get("redirectUrl")
    checkout_id = result.get("id")
    if not redirect_url or not checkout_id or result.get("amount") != amount_cents or result.get("currency") != payment.currency:
        raise GatewayError("Yoco returned an incomplete or mismatched checkout response.")
    return {"checkout_url": redirect_url, "form_fields": None, "checkout_session_id": checkout_id}


def verify_yoco_webhook(raw_body, headers, now=None, tolerance_seconds=180):
    secret = _setting("YOCO_WEBHOOK_SECRET")
    if not secret or not secret.startswith("whsec_"):
        return False, "Yoco webhook signing secret is not configured."
    webhook_id = headers.get("webhook-id")
    timestamp = headers.get("webhook-timestamp")
    signatures = headers.get("webhook-signature", "")
    if not webhook_id or not timestamp or not signatures:
        return False, "Required Yoco webhook headers are missing."
    try:
        signed_at = int(timestamp)
    except (TypeError, ValueError):
        return False, "Invalid Yoco webhook timestamp."
    current = int(time.time() if now is None else now)
    if abs(current - signed_at) > tolerance_seconds:
        return False, "Yoco webhook timestamp is outside the allowed replay window."
    secret_bytes = __import__("base64").b64decode(secret.split("_", 1)[1])
    signed_content = webhook_id.encode() + b"." + timestamp.encode() + b"." + raw_body
    expected = __import__("base64").b64encode(
        hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    ).decode("ascii")
    for candidate in signatures.split():
        if candidate.startswith("v1,") and hmac.compare_digest(candidate[3:], expected):
            return True, webhook_id
    return False, "Yoco webhook signature is invalid."


def _payfast_signature(data):
    from urllib.parse import quote_plus
    parts = []
    for key, value in data.items():
        if key == "signature" or value is None or str(value) == "":
            continue
        parts.append(f"{key}={quote_plus(str(value).strip())}")
    passphrase = _setting("PAYFAST_PASSPHRASE")
    if passphrase:
        parts.append("passphrase=" + quote_plus(str(passphrase).strip()))
    return hashlib.md5("&".join(parts).encode("utf-8")).hexdigest()


def verify_payfast_signature(data):
    supplied = str(data.get("signature", ""))
    expected = _payfast_signature(data)
    return bool(supplied) and hmac.compare_digest(supplied.lower(), expected.lower())


def verify_payfast_source_ip(remote_addr):
    allowed_hosts = (
        "www.payfast.co.za", "sandbox.payfast.co.za",
        "w1w.payfast.co.za", "w2w.payfast.co.za",
    )
    allowed_ips = set()
    try:
        for host in allowed_hosts:
            allowed_ips.update(socket.gethostbyname_ex(host)[2])
    except OSError:
        return False
    return bool(remote_addr) and remote_addr in allowed_ips


def validate_payfast_itn(raw_body):
    sandbox = bool(_setting("PAYFAST_SANDBOX", True))
    endpoint = (
        "https://sandbox.payfast.co.za/eng/query/validate"
        if sandbox else "https://www.payfast.co.za/eng/query/validate"
    )
    request = Request(
        endpoint, data=raw_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8").strip() == "VALID"
    except (HTTPError, URLError, TimeoutError):
        return False
