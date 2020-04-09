import os
import requests
import json
import hashlib
import urllib.parse

from payment.models import Payment
from decimal import Decimal

MERCHANT_SECRET_KEY = os.getenv("MERCHANT_SECRET_KEY")
MERCHANT_ID = os.getenv("MERCHANT_ID")
MERCHANT_URL = "https://anypay.io/merchant"
VK_KEY = os.getenv("VK_ACCESS_TOKEN")
CURRENCY = os.getenv("CURRENCY")


def get_sign(price: Decimal, payment_id: int) -> str:
    return hashlib.md5(
        f"{CURRENCY}:{price}:{MERCHANT_SECRET_KEY}:{MERCHANT_ID}:{payment_id}".encode()
    ).hexdigest()


def shorten_url(url: str):
    vk_api_url = f"https://api.vk.com/method/utils.getShortLink?url={url}&access_token={VK_KEY}&v=5.100"
    response = requests.get(vk_api_url)

    if not response.ok:
        return None

    json_content = json.loads(response.content)
    return json_content["response"]["short_url"]


def make_payment(user_id: int, quest_id: int, price: Decimal) -> str:
    """
    Makes payment-object and returns url to process payment

    :param user_id: Id of user that want to buy
    :param quest_id: Id of quest that player wants to buy
    :param price: Price of the quest
    :return: URL to process payment, 'None' if something goes wrong
    """

    payment, _ = Payment.objects.get_or_create(
        player_id=user_id, quest_id=quest_id, defaults={"amount": price}
    )

    sign = get_sign(price, quest_id)
    url_params = urllib.parse.quote(
        f"merchant_id={MERCHANT_ID}&amount={price}&pay_id={payment.id}&sign={sign}",
        safe="=",
    )
    url_long = f"{MERCHANT_URL}?{url_params}"
    url_short = shorten_url(url_long)
    return url_short
