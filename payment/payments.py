import os
import requests
import json
import hashlib

from payment.models import Payment

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
MERCHANT_SECRET_KEY = os.getenv("MERCHANT_SECRET_KEY")
MERCHANT_ID = os.getenv("MERCHANT_ID")
VK_KEY = os.getenv("VK_ACCESS_TOKEN")
CURRENCY = os.getenv("CURRENCY")
MERCHANT_URL = "https://anypay.io/merchant"


def get_sign(price: int, payment_id: int) -> str:
    return hashlib.md5(f"{CURRENCY}:{price}:{MERCHANT_SECRET_KEY}:{MERCHANT_ID}:{payment_id}").hexdigest()


def shorten_url(url: str):
    vk_api_url = f"https://api.vk.com/method/utils.getShortLink?url={url}&access_token={VK_KEY}&v=5.100"
    response = requests.get(vk_api_url)

    if not response.ok:
        return None

    json_content = json.loads(response)
    return json_content["response"]["short_url"]


def make_payment(user_id: int, price: int, quest_id: int) -> str:
    # get token and create Payment objects
    sign = get_sign(price, quest_id)

    payment, _ = Payment.objects.get_or_create(player_id=user_id, quest_id=quest_id)

    url_long = f"{MERCHANT_URL}?merchant_id={MERCHANT_ID}&amount={price}&pay_id={payment.id}&sign={sign}"
    return shorten_url(url_long)
