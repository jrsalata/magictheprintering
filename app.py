from flask import Flask, request
from markupsafe import escape

from printer import build_hello_world_blocks, send_print_job, build_message
from fortune import fortune
from search_builder import SearchBuilder
from search_results import fetch_json
from card import Card

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

    builder = SearchBuilder()
    builder.add_card_type("creature")
    builder.add_mana_value(mana_value)
    url = builder.build_url_single_card()
    json = fetch_json(url)
    card = Card.from_json(json)
    response = card.print()
    message = f"Printed {card.name}"

    return PAGE.format(message=escape(message))

@app.route("/discord", methods=["POST"])
def submit_discord():
    include_illegal = 'enabled' in request.form.getlist('illegal_cards')

    builder = SearchBuilder()
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
