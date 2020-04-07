import os
import json
import hashlib

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from questApp.models import Quest, PlayersQuest
from player.models import Player
from datetime import datetime
from .models import Payment

MERCHANT_IPS = ["185.162.128.38", "185.162.128.39", "185.162.128.88"]
MERCHANT_SECRET_KEY = os.getenv("MERCHANT_SECRET_KEY")


def check_signature(sign, merchant_id, amount, pay_id):
    sign_real = hashlib.md5(f"{merchant_id}:{amount}:{pay_id}:{MERCHANT_SECRET_KEY}").hexdigest()
    return sign_real == sign


@csrf_exempt
def anypay_webhook(request):
    ip = request.META.get('HTTP_X_REAL_IP', request.META.get("REMOTE_ADDR"))
    ip_status = ip in MERCHANT_IPS

    content = json.loads(request.body)
    merchant_id = content["merchant_id"]
    amount = content["amount"]
    pay_id = content["pay_id"]

    sign = content["sign"]
    sign_status = check_signature(sign, merchant_id, amount, pay_id)

    if sign_status and ip_status:
        profit = content["profit"]
        transaction_id = content["transaction_id"]
        date_pay = content["pay_date"]

        payment = Payment.objects.get(id=pay_id)
        payment.amount = amount
        payment.profit = profit
        payment.transaction_id = transaction_id
        payment.date_pay = date_pay
        payment.save()

        return HttpResponse(status=200)
    else:
        return HttpResponse(status=400)
