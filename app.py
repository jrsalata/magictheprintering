from flask import Flask, request
from markupsafe import escape

from error_receipt import build_http_error_receipt
from http_errors import HttpRequestError
from printer import build_hello_world_blocks, send_print_job, build_message
from fortune import fortune
from search_builder import SearchBuilder
from search_results import fetch_json
from card import Card
from download_card import fetch_card

app = Flask(__name__)

PAGE = """<!doctype html>
<title>Magic the Printering</title>
<h1>Magic the Printering</h1>
<form method="post" action="/">
  <button value="hello" name="action" type="submit">Print Hello World</button>
  <button value="fortune" name="action" type="submit">Print Fortune</button>
</form>
<form method="post" action="/momir">
  <label for="mana_value">Mana Value for Momir:</label>
  <input id="mana_value" name="mana_value" type="number" step="any" required>
  <button type="submit">I'm Feeling Lucky</button>
</form>
<form method="post" action="/discord">
  <label>
    <input type="checkbox" name="illegal_cards" value="enabled" checked>
    Include illegal cards
  </label>
  <input type="submit" value="My little discord">
</form>
<form method="post" action="/search">
  <label for="card_name">Card Name:</label>
  <input id="card_name" name="card_name" type="text" required>
  <button type="submit">Search &amp; Print</button>
</form>
<p>{message}</p>
"""


@app.route("/", methods=["GET", "POST"])
def print_page():
    message = ""
    sent = False
    if request.method == "POST":
        try:
            action = request.form.get("action")
            if action == "hello":
                send_print_job(build_hello_world_blocks())
                sent = True
            if action == "fortune":
                send_print_job(build_message(fortune()))
                sent = True
            if sent:
                message = "Print job sent!"
        except HttpRequestError as err:
            _print_http_error_receipt(err)
            message = f"Print failed with HTTP {err.status_code}. Error receipt sent to printer."
        except (RuntimeError, ValueError) as err:
            message = f"Print failed: {err}"
    
    return PAGE.format(message=escape(message))


@app.route("/momir", methods=["POST"])
def submit_momir():
    raw = request.form.get("mana_value", "").strip()
    try:
        mana_value = int(raw)
    except ValueError:
        message = f"Invalid mana value: {raw!r}" if raw else "No mana value provided."
        return PAGE.format(message=escape(message)), 400

    try:
        builder = SearchBuilder()
        builder.add_card_type("creature")
        builder.add_mana_value(mana_value)
        url = builder.build_url_single_card()
        json = fetch_json(url)
        card = Card.from_json(json)
        card.print()
        message = f"Printed {card.name}"
        return PAGE.format(message=escape(message))
    except HttpRequestError as err:
        _print_http_error_receipt(err)
        message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return PAGE.format(message=escape(message)), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return PAGE.format(message=escape(message)), 500


@app.route("/search", methods=["POST"])
def submit_search():
    card_name = request.form.get("card_name", "").strip()
    if not card_name:
        return PAGE.format(message=escape("No card name provided.")), 400

    try:
        card_json = fetch_card(card_name)
        card = Card.from_json(card_json)
        card.print()
        message = f"Printed {card.name}"
        return PAGE.format(message=escape(message))
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or f"No card found matching {card_name!r}."
            return PAGE.format(message=escape(message)), 404
        _print_http_error_receipt(err)
        message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return PAGE.format(message=escape(message)), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return PAGE.format(message=escape(message)), 500


def _print_http_error_receipt(err: HttpRequestError) -> None:
    """Best-effort HTTP error receipt printing with recursion guard."""
    try:
        payload = build_http_error_receipt(err)
        send_print_job(payload)
    except RuntimeError:
        # If printer call fails while printing the error receipt, avoid recursion.
        return

@app.route("/discord", methods=["POST"])
def submit_discord():
    include_illegal = 'enabled' in request.form.getlist('illegal_cards')

    builder = SearchBuilder()

    if not include_illegal:
        builder.add_commander_legality()
        
    builder.add_exclude_lands()
    url = builder.build_url_single_card()
    json = fetch_json(url)
    card = Card.from_json(json)
    response = card.print()
    message = f"Printed {card.name}"

    return PAGE.format(message=escape(message))

if __name__ == "__main__":
    app.run()
