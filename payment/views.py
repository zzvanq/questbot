import os
import hashlib
from datetime import datetime

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Payment

MERCHANT_IPS = ["185.162.128.38", "185.162.128.39", "185.162.128.88"]
MERCHANT_SECRET_KEY = os.getenv("MERCHANT_SECRET_KEY")


def check_signature(sign, merchant_id, amount, pay_id):
    sign_real = hashlib.md5(f"{merchant_id}:{amount}:{pay_id}:{MERCHANT_SECRET_KEY}".encode()).hexdigest()
    return sign_real == sign


@csrf_exempt
def anypay_webhook(request):
    ip = request.META.get('HTTP_X_REAL_IP', request.META.get("REMOTE_ADDR"))
    ip_status = ip in MERCHANT_IPS

    merchant_id = request.POST.get("merchant_id")
    amount = request.POST.get("amount")
    pay_id = request.POST.get("pay_id")

    sign = request.POST.get("sign")
    sign_status = check_signature(sign, merchant_id, amount, pay_id)
    if sign_status and ip_status:
        profit = request.POST.get("profit")
        transaction_id = request.POST.get("transaction_id")
        date_pay = request.POST.get("pay_date")

        payment = Payment.objects.get(id=pay_id)
        payment.amount = amount
        payment.profit = profit
        payment.transaction_id = transaction_id
        payment.date_pay = datetime.strptime(date_pay, "%d.%m.%Y %H:%M:%S")
        payment.save()

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=400)
