import logging
import re
import secrets
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RoleName
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Order, PaymentTransaction, PlantRentalOrder, User
from app.schemas.payment import PaymentInitiateRequest, PaymentInitiateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payment", tags=["Payments"])
CENT = Decimal("0.01")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _provider_url() -> str:
    if settings.SSLCOMMERZ_IS_SANDBOX:
        return "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
    return "https://securepay.sslcommerz.com/gwprocess/v4/api.php"


def _log_gateway_response(response: httpx.Response) -> None:
    response_body = response.text
    store_password = settings.SSLCOMMERZ_STORE_PASSWORD
    if store_password:
        response_body = response_body.replace(store_password, "[REDACTED]")
    logger.error(
        "SSLCommerz initiation response (HTTP %s): %s",
        response.status_code,
        response_body,
    )


def _callback_url(request: Request, endpoint: str) -> str:
    if settings.PUBLIC_BASE_URL:
        origin = settings.PUBLIC_BASE_URL.rstrip("/")
    elif request.url.hostname in {"localhost", "127.0.0.1"}:
        origin = str(request.base_url).rstrip("/")
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Set PUBLIC_BASE_URL to the public API origin before accepting payments",
        )
    return f"{origin}/api/v1/payment/{endpoint}"


def _get_order(db: Session, order_type: str, order_id: int, user_id: int):
    if order_type == "purchase":
        order = db.scalar(
            select(Order).where(Order.id == order_id, Order.user_id == user_id)
        )
        amount = Decimal(str(order.total_amount)).quantize(CENT) if order else None
    else:
        order = db.scalar(
            select(PlantRentalOrder).where(
                PlantRentalOrder.rental_id == order_id,
                PlantRentalOrder.user_id == user_id,
            )
        )
        amount = Decimal(str(order.total_amount)).quantize(CENT) if order else None
    return order, amount


def _payment_order(db: Session, transaction: PaymentTransaction):
    if transaction.order_type == "purchase":
        return db.get(Order, transaction.order_id)
    return db.get(PlantRentalOrder, transaction.order_id)


def _gateway_is_valid(
    validation: dict,
    transaction: PaymentTransaction,
) -> bool:
    if validation.get("status") not in {"VALID", "VALIDATED"}:
        return False
    if validation.get("tran_id") != transaction.transaction_id:
        return False
    if str(validation.get("currency", "")).upper() != transaction.currency:
        return False
    try:
        amount = Decimal(str(validation.get("amount"))).quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        return False
    return amount == Decimal(transaction.amount).quantize(CENT)


def _validation_response(validation_id: str, transaction: PaymentTransaction) -> dict:
    if not settings.SSLCOMMERZ_STORE_ID or not settings.SSLCOMMERZ_STORE_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured",
        )
    endpoint = (
        "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
        if settings.SSLCOMMERZ_IS_SANDBOX
        else "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"
    )
    try:
        response = httpx.get(
            endpoint,
            params={
                "val_id": validation_id,
                "store_id": settings.SSLCOMMERZ_STORE_ID,
                "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
                "format": "json",
            },
            timeout=15,
        )
        response.raise_for_status()
        validation = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("SSLCommerz transaction validation failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to validate payment with the gateway",
        ) from exc
    if not isinstance(validation, dict) or not _gateway_is_valid(validation, transaction):
        return {}
    return validation


@router.post("/initiate", response_model=PaymentInitiateResponse)
def initiate_payment(
    payload: PaymentInitiateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.USER)),
):
    if not settings.SSLCOMMERZ_STORE_ID or not settings.SSLCOMMERZ_STORE_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured",
        )

    order, amount = _get_order(db, payload.order_type, payload.order_id, current_user.id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if amount is None or amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order amount must be greater than zero",
        )
    if order.payment_status.upper() == "PAID":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is already paid")
    expected_status = "Approved" if payload.order_type == "rental" else "Pending"
    if getattr(order.status, "value", order.status) != expected_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Rental requests can only be paid after nursery approval"
                if payload.order_type == "rental"
                else "Only pending orders can be paid"
            ),
        )
    if payload.cart_items is not None:
        requested_items = sorted(
            (item.plant_id, item.quantity) for item in payload.cart_items
        )
        if payload.order_type == "purchase":
            order_items = sorted(
                (item.plant_id, item.quantity) for item in order.items
            )
        else:
            order_items = [(order.plant_id, order.quantity)]
        if requested_items != order_items:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cart items do not match this order. Refresh your cart and try again.",
            )
    customer_name = current_user.name.strip()[:100]
    customer_email = current_user.email.strip()
    customer_phone = re.sub(r"\D", "", payload.phone)
    if not customer_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer name is required for payment",
        )
    if not _EMAIL_PATTERN.fullmatch(customer_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid customer email is required for payment",
        )
    if not 5 <= len(customer_phone) <= 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid customer phone number is required for payment",
        )
    pending_transaction = db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.order_type == payload.order_type,
            PaymentTransaction.order_id == payload.order_id,
            PaymentTransaction.status == "Pending",
        )
    )
    if pending_transaction:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A payment attempt is already in progress for this order",
        )

    transaction_id = f"GN{secrets.token_hex(12)}"
    transaction = PaymentTransaction(
        transaction_id=transaction_id,
        order_type=payload.order_type,
        order_id=payload.order_id,
        user_id=current_user.id,
        amount=amount,
        currency="BDT",
        status="Pending",
    )
    order.payment_status = "PENDING"
    order.payment_transaction_id = transaction_id
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    callback_base = {
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "total_amount": format(amount, ".2f"),
        "currency": "BDT",
        "tran_id": transaction_id,
        "success_url": _callback_url(request, "success"),
        "fail_url": _callback_url(request, "fail"),
        "cancel_url": _callback_url(request, "cancel"),
        "cus_name": customer_name,
        "cus_email": customer_email,
        "cus_add1": payload.address,
        "cus_city": payload.city,
        "cus_postcode": payload.postcode,
        "cus_country": "Bangladesh",
        "cus_phone": customer_phone,
        "shipping_method": "YES",
        "num_of_item": "1",
        "ship_name": customer_name,
        "ship_add1": payload.address,
        "ship_city": payload.city,
        "ship_postcode": payload.postcode,
        "ship_country": "Bangladesh",
        "product_name": "GreenNest plant order",
        "product_category": "Plants",
        "product_profile": "physical-goods",
    }
    response: httpx.Response | None = None
    try:
        response = httpx.post(
            _provider_url(),
            data=callback_base,
            timeout=20,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        gateway_response = response.json()
    except httpx.HTTPStatusError as exc:
        transaction.status = "Failed"
        order.payment_status = "Failed"
        db.commit()
        _log_gateway_response(exc.response)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to start payment with the gateway",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        transaction.status = "Failed"
        order.payment_status = "Failed"
        db.commit()
        if response is not None:
            _log_gateway_response(response)
        else:
            logger.error(
                "SSLCommerz payment initiation failed before receiving a response (%s)",
                type(exc).__name__,
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to start payment with the gateway",
        ) from exc

    if not isinstance(gateway_response, dict):
        gateway_response = {}
    if gateway_response.get("status") != "SUCCESS":
        transaction.status = "Failed"
        order.payment_status = "Failed"
        db.commit()
        _log_gateway_response(response)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="SSLCommerz rejected payment initiation",
        )

    gateway_url = gateway_response.get("GatewayPageURL")
    parsed_url = urlparse(gateway_url) if isinstance(gateway_url, str) else None
    if (
        not parsed_url
        or parsed_url.scheme != "https"
        or not parsed_url.hostname
        or not (
            parsed_url.hostname == "sslcommerz.com"
            or parsed_url.hostname.endswith(".sslcommerz.com")
        )
    ):
        transaction.status = "Failed"
        order.payment_status = "Failed"
        db.commit()
        logger.warning("SSLCommerz returned an invalid gateway URL")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment gateway returned an invalid checkout URL",
        )
    return PaymentInitiateResponse(gateway_url=gateway_url, transaction_id=transaction_id)



from urllib.parse import urlencode
from app.core.config import settings
from fastapi.responses import RedirectResponse
from fastapi import HTTPException, status

def _redirect(status_value: str, transaction_id: str = "") -> RedirectResponse:
    query = {"status": status_value}
    if transaction_id:
        query["order_id"] = transaction_id

    frontend_base = settings.FRONTEND_BASE_URL
    if not frontend_base:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Frontend URL is not configured for payment redirects",
        )

    target = f"{frontend_base.rstrip('/')}/payment-result.html?{urlencode(query)}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


async def _form_value(request: Request, key: str) -> str:
    form = await request.form()
    value = form.get(key)
    return value.strip() if isinstance(value, str) else ""


@router.post("/success")
async def payment_success(request: Request, db: Session = Depends(get_db)):
    transaction_id = await _form_value(request, "tran_id")
    validation_id = await _form_value(request, "val_id")
    transaction = db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.transaction_id == transaction_id
        )
    )
    if transaction is None or not validation_id:
        return _redirect("error", transaction_id)
    if transaction.status == "Paid":
        return _redirect("success", transaction_id)
    if transaction.status != "Pending":
        return _redirect("error", transaction_id)

    validation = _validation_response(validation_id, transaction)
    order = _payment_order(db, transaction)
    if not validation or order is None:
        transaction.status = "Failed"
        if order is not None and order.payment_transaction_id == transaction_id:
            order.payment_status = "FAILED"
        db.commit()
        return _redirect("error", transaction_id)

    transaction.status = "Paid"
    transaction.validation_id = validation_id
    order.payment_status = "PAID"
    if transaction.order_type == "purchase":
        order.status = "Processing"
    db.commit()
    return _redirect("success", transaction_id)


async def _finish_unsuccessful_payment(
    request: Request,
    db: Session,
    terminal_status: str,
    query_status: str,
):
    transaction_id = await _form_value(request, "tran_id")
    transaction = db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.transaction_id == transaction_id
        )
    )
    if transaction and transaction.status == "Pending":
        transaction.status = terminal_status
        order = _payment_order(db, transaction)
        if order is not None and order.payment_transaction_id == transaction_id:
            order.payment_status = terminal_status.upper()
        db.commit()
    return _redirect(query_status, transaction_id)


@router.post("/fail")
async def payment_fail(request: Request, db: Session = Depends(get_db)):
    return await _finish_unsuccessful_payment(request, db, "Failed", "error")


@router.post("/cancel")
async def payment_cancel(request: Request, db: Session = Depends(get_db)):
    return await _finish_unsuccessful_payment(request, db, "Cancelled", "cancelled")
