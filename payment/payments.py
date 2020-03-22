import os
import requests
import json

from requests.auth import HTTPBasicAuth

MERCHANT_ID = os.getenv("MERCHANT_ID")
MERCHANT_API_KEY = os.getenv("MERCHANT_API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def register_user(user_id, **kwargs):
    # Request Xsolla project to register new user
    reg_url = "https://api.xsolla.com/merchant/v2/projects/39756/users"
    data = {"user_id": str(user_id)}

    return requests.post(
        reg_url,
        data=json.dumps(data),
        headers=HEADERS,
        auth=HTTPBasicAuth(MERCHANT_ID, MERCHANT_API_KEY),
    )


def get_token(user_id, price, game_id, **kwargs):
    # Get purchase token
    token_url = "https://api.xsolla.com/merchant/v2/merchants/74390/token"

    data = {
        "user": {"id": {"value": str(user_id)}},
        "settings": {
            "project_id": PROJECT_ID,
            "external_id": game_id,
            "mode": "sandbox",
        },
        "purchase": {"checkout": {"amount": float(price), "currency": "RUB"}},
    }
    response = requests.post(
        token_url,
        data=json.dumps(data),
        headers=HEADERS,
        auth=HTTPBasicAuth(MERCHANT_ID, MERCHANT_API_KEY),
    )

    token = response.json()
    return token.get("token", None)


def make_payment(user_id, price, game_id):
    # Register user, get token and create Payment objects
    user = register_user(user_id)
    token = get_token(user_id, price, game_id)

    if token:
        url_long = "https://secure.xsolla.com/paystation3/?access_token=" + token
        # r = requests.post("https://api.rebrandly.com/v1/links",
        #                   data = json.dumps({
        #                       "destination": url_long,
        #                       "domain": {"fullName": "rebrand.ly"}
        #                   }),
        #                   headers = {
        #                       "Content-type": "application/json",
        #                       "apikey": "8ba8ebd726174ed385dc3bac7d6a38d2"
        #                   })

        # if (r.status_code == requests.codes.ok):
        #     link = r.json()
        #     url = link["shortUrl"]
        # else:
        url = url_long
        return url
