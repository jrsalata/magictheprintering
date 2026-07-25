from flask import Flask, request
from markupsafe import escape

from printer import build_hello_world_blocks, send_print_job, build_message
from fortune import fortune

app = Flask(__name__)

PAGE = """<!doctype html>
<title>Magic the Printering</title>
<h1>Magic the Printering</h1>
<form method="post" action="/">
  <button value="hello" name="action" type="submit">Print Hello World</button>
  <button value="fortune" name="action" type="submit">Print Fortune</button>
</form>
<p>{message}</p>
"""


@app.route("/", methods=["GET", "POST"])
def print_page():
    message = ""
    if request.method == "POST":
        try:
            action = request.form.get("action")
            sent = False
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


if __name__ == "__main__":
    app.run()
