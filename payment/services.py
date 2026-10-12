from django.conf import settings
from zarinpal import ZarinPal, Config


def get_zarinpal():
    config = Config(
        merchant_id=settings.ZARINPAL["merchant_id"],
        sandbox=settings.ZARINPAL["sandbox"],
    )
    return ZarinPal(config)


def request_payment(payment, callback_url):
    """
    ارسال درخواست پرداخت به زرین‌پال و دریافت Authority
    """
    zp = get_zarinpal()
    payment_data = {
        "amount": int(payment.amount),
        "description": f"پرداخت سفارش {payment.order.order_number}",
        "callback_url": callback_url,
    }
    
    result = zp.payments.create(payment_data)
    
    if result.get("data", {}).get("code") == 100:
        authority = result["data"]["authority"]
        payment.authority = authority
        payment.save(update_fields=["authority"])
        
        payment_url = zp.payments.generate_payment_url(authority)
        return True, payment_url
    
    return False, str(result)


def verify_payment(payment):
    """
    تایید نهایی تراکنش از طریق زرین‌پال
    """
    zp = get_zarinpal()
    verify_data = {
        "amount": int(payment.amount),
        "authority": payment.authority,
    }
    
    result = zp.verifications.verify(verify_data)
    code = result.get("data", {}).get("code")
    
    if code in [100, 101]:  # 100: موفق، 101: قبلاً تایید شده
        ref_id = result["data"]["ref_id"]
        return True, ref_id
    
    return False, None