from flask import Flask, request
from markupsafe import escape

from printer import build_hello_world_blocks, send_print_job, build_message, send_print_momir, send_print_discord
from fortune import fortune

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
  <input id="mana_value" name="mana_value" type="mana_value" step="any" required>
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
    sent = False
    try:
        mana_value = int(raw)
    except ValueError:
        message = f"Invalid mana value: {raw!r}" if raw else "No mana value provided."
        return PAGE.format(message=escape(message)), 400
    if mana_value.is_integer():
        send_print_momir(build_message(f"TODO: print random creature with mana value {mana_value} for momir"))
        sent = True
    if sent:
        message = f"Printing random creature with mana value {mana_value}"
    return PAGE.format(message=escape(message))

@app.route("/discord", methods=["POST"])
def submit_discord():
    include_illegal = 'enabled' in request.form.getlist('illegal_cards')
    if include_illegal:
        send_print_discord(build_message(f"TODO: print random non-land including illegal cards for discord"))
        message = "Printing random non-land including illegal cards for discord"
    else:
        send_print_discord(build_message(f"TODO: print random non-land excluding illegal cards for discord"))
        message = "Printing random non-land excluding illegal cards for discord"
    return PAGE.format(message=escape(message))

if __name__ == "__main__":
    app.run()
