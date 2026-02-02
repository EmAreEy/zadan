import requests
import json
import os

BASE_URL = "https://gamma-api.polymarket.com/events/slug/"
SLUG = "israel-strikes-iran-by-february-28-2026"
RETRIES = 3


def get_data_from_api(
    base_url: str = "https://gamma-api.polymarket.com/events/slug/",
    slug: str = "israel-strikes-iran-by-february-28-2026",
    retries: int = RETRIES,
) -> dict[str, float] | None:
    for _ in range(retries):
        try:
            response = requests.get(base_url + slug)
            response.raise_for_status()
            markets = response.json()["markets"]
            outcomePrices = markets[0]["outcomePrices"].split('"')
            yes = float(outcomePrices[1])
            no = float(outcomePrices[-2])
            volume: float = float(markets[0]["volume"])
            mizanan_data = {
                "mizanan": yes,
                "nemizanan": no,
                "hajm": volume,
            }
            return mizanan_data
        except requests.exceptions.HTTPError as e:
            print(f"an http error occurred : {e}")
        except requests.exceptions.Timeout as e:
            print(f"request timeout error : {e}")
        except requests.exceptions.SSLError as e:
            print(f"an ssl error occurred : {e}")
        except requests.exceptions.ConnectionError as e:
            print(f"connection error : {e}")
        except requests.exceptions.RequestException as e:
            print(f"request error : {e}")
        except ValueError as e:
            print(f"failed to parse json : {e}")
    print("failed to call api")
    return None


def initial_run():
    if data := get_data_from_api(base_url=BASE_URL, slug=SLUG):
        with open("mizanan_data.json", "w") as f:
            json.dump(data, f)
    else:
        raise RuntimeError("error in getting data.")


def evaluate_alert_conditions(
    pervious_data: dict[str, float], current_data: dict[str, float]
) -> str:
    p_new, v_new = current_data["mizanan"], current_data["hajm"]
    p_old, v_old = pervious_data["mizanan"], pervious_data["hajm"]
    message = "nazadan"

    price_delta = p_new - p_old
    volume_delta = v_new - v_old
    tension_score = price_delta * (volume_delta ** (1 / 2))

    if price_delta <= 0 or volume_delta <= 100:
        return message
    elif p_new >= 0.65:
        message = "oh shit"
    elif price_delta >= 0.12 or tension_score >= 7:
        message = "red"
    elif tension_score >= 3:
        message = "yellow"
    return message


def send_telegram_message(token: str, chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"error sending to telegram : {e}")


if __name__ == "__main__":
    token = os.getenv("TELEGRAM_TOKEN")
    chat = os.getenv("CHAT_ID")
    if not os.path.exists("mizanan_data.json"):
        initial_run()
        print("initial run...")
    else:
        print("loading...")
        with open("mizanan_data.json", "r") as f:
            old_data = json.load(f)
        new_data = get_data_from_api()
        if new_data:
            status = evaluate_alert_conditions(
                pervious_data=old_data, current_data=new_data
            )
            print(status)
            if not status == "nazadan":
                if status == "yellow":
                    message = "لوله گاز ترکید ؟"
                elif status == "red":
                    message = "زدن؟؟؟"
                else:
                    message = "زدننننننننننننننننن"
                send_telegram_message(token, chat, message=message)
            else:
                send_telegram_message(token, chat, message="nazadan")
        else:
            message = "error in api"
            send_telegram_message(token, chat, message=message)
            raise RuntimeError("no data")
        with open("mizanan_data.json", "w") as f:
            json.dump(new_data, f)
            print("data updated")
