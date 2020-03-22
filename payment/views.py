import json
import hashlib

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from questApp.models import Quest, PlayersQuest
from player.models import Player
from datetime import datetime
from .models import Payment

PROJECT_SECRET_KEY = "saVhFLGhpP6f8HIX"


def _check_signature(body, auth):
    jsondata = str(body)
    jsondata = jsondata.replace(" ", "").replace("'", '"')
    hash_val = jsondata + PROJECT_SECRET_KEY
    access = hashlib.sha1(hash_val.encode())
    sign_in = auth.split(" ")[1]
    sign_out = access.hexdigest()

    return sign_in == sign_out


@csrf_exempt
def xsollaWebhook(request):
    jsondata = json.loads(request.body)
    if _check_signature(jsondata, request.META.get("HTTP_AUTHORIZATION", None)):
        notif_type = jsondata["notification_type"]
        if notif_type == "payment":
            # Successed payment
            payment = jsondata["payment_details"]
            value = payment["payout"]["amount"]
            value_wo = payment["payment"]["amount"]
            user = jsondata["user"]["id"]
            transaction = jsondata["transaction"]
            game_id = transaction["external_id"]
            method = transaction["payment_method"]
            agreement = transaction["agreement"]
            payment_id = transaction["id"]
            date_created = transaction["payment_date"]
            date_created = datetime.strptime(date_created, "%Y-%m-%dT%H:%M:%S+03:00")
            quest_pk, quest_name, attempts_num = game_id.split(":")

            player = Player.objects.get(user_login=user)
            quest = Quest.objects.get(pk=quest_pk)

            player_quest = PlayersQuest.objects.get(player=player, quest=quest)
            player_quest.attempts_num += attempts_num
            player_quest.save()
            payment, created = Payment.objects.get_or_create(
                player=player,
                quest=quest,
                value=value,
                value_wo=value_wo,
                method=method,
                agreement=agreement,
                payment_id=payment_id,
                date_created=date_created,
                is_in_awarding_time=quest.is_awarding,
            )
            if created:
                payment.save()
            return HttpResponse(status=200)
        elif notif_type == "refund" or notif_type == "afs_reject":
            # Payment refund
            user = jsondata["user"]["id"]
            game_id = jsondata["transaction"]["external_id"]

            player = Player.objects.get(user_login=user)
            quest = Quest.objects.get(pk=game_id)
            payment = Payment.objects.get(player=player, quest=quest)
            payment.remove()
            player_quest = PlayersQuest.objects.get(player=player, quest=quest)
            player_quest.attempts_num = 0
            player_quest.save()
        elif notif_type == "user_validation":
            user = jsondata["user"]["id"]
            player = Player.objects.filter(user_login=user).exists()
            if player:
                return HttpResponse(status=200)
            else:
                response = JsonResponse(
                    status=401, data={"error": {"code": "INVALID_USER"}}
                )
                return response
        elif notif_type == "user_search":
            user = jsondata["user"]["public_id"]
            player = Player.objects.filter(user_login=user).exists()
            if player:
                return JsonResponse(
                    status=200, data={"user": {"id": jsondata["user"]["public_id"]}}
                )
            else:
                response = JsonResponse(
                    status=404, data={"error": {"code": "INVALID_USER"}}
                )
                return response
    else:
        response = JsonResponse(
            status=403, data={"error": {"code": "INVALID_SIGNATURE"}}
        )
        return response
