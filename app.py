from flask import Flask, jsonify, request
from markupsafe import escape

from error_receipt import build_http_error_receipt
from http_errors import HttpRequestError
from printer import build_hello_world_blocks, send_print_job, build_message
from fortune import fortune
from search_builder import SearchBuilder
from search_results import fetch_json
from card import Card
from download_card import fetch_card
from pack import PACKS

app = Flask(__name__)

_PACK_OPTIONS = "\n".join(
    f'    <option value="{pack.name}">{pack.display_name} ({pack.size} cards)</option>'
    for pack in PACKS.values()
)

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
<form method="post" action="/pack">
  <label for="pack_type">Pack Type:</label>
  <select id="pack_type" name="pack_type" required>
__PACK_OPTIONS__
  </select>
  <label for="set_code">Set Code (optional):</label>
  <input id="set_code" name="set_code" type="text">
  <button type="submit">Open &amp; Print Pack</button>
</form>
<p>{message}</p>
""".replace("__PACK_OPTIONS__", _PACK_OPTIONS)


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

@app.route("/packs", methods=["GET"])
def list_packs():
    return jsonify({"packs": [pack.to_dict() for pack in PACKS.values()]})


@app.route("/packs/<pack_type>", methods=["POST"])
def open_pack(pack_type):
    pack = PACKS.get(pack_type)
    if pack is None:
        return jsonify({
            "error": f"Unknown pack type: {pack_type!r}",
            "available_packs": sorted(PACKS),
        }), 404

    body = request.get_json(silent=True) or {}
    set_code = (body.get("set") or request.form.get("set") or request.args.get("set") or "").strip() or None

    try:
        cards = pack.open(set_code=set_code, print_cards=True)
        return jsonify({
            "pack_type": pack.name,
            "display_name": pack.display_name,
            "set": set_code,
            "printed_count": len(cards),
            "cards": cards,
        })
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or f"No cards found for pack type {pack_type!r}."
            return jsonify({"error": message}), 404
        _print_http_error_receipt(err)
        return jsonify({
            "error": f"Request failed with HTTP {err.status_code}. Error receipt sent to printer.",
        }), 502
    except (RuntimeError, ValueError) as err:
        return jsonify({"error": f"Failed to open pack: {err}"}), 500


@app.route("/pack", methods=["POST"])
def submit_pack():
    pack_type = request.form.get("pack_type", "").strip()
    pack = PACKS.get(pack_type)
    if pack is None:
        message = f"Unknown pack type: {pack_type!r}" if pack_type else "No pack type provided."
        return PAGE.format(message=escape(message)), 400

    set_code = request.form.get("set_code", "").strip() or None

    try:
        cards = pack.open(set_code=set_code, print_cards=True)
        card_names = ", ".join(card["name"] for card in cards)
        message = f"Opened {pack.display_name} and printed {len(cards)} cards: {card_names}"
        return PAGE.format(message=escape(message))
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or f"No cards found for pack type {pack_type!r}."
            return PAGE.format(message=escape(message)), 404
        _print_http_error_receipt(err)
        message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return PAGE.format(message=escape(message)), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return PAGE.format(message=escape(message)), 500


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
