from flask import Flask, jsonify, render_template, request

from enums.color import Color
from enums.comparison import Comparison
from enums.format import Format
from enums.rarity import Rarity
from enums.typeline import TypeLine
from error_receipt import build_http_error_receipt
from http_errors import HttpRequestError
from printer import build_hello_world_blocks, send_print_job, build_message
from fortune import fortune
from search_builder import SearchBuilder
from search_results import fetch_json
from card import Card
from download_card import fetch_card
import pack

app = Flask(__name__)


def _render_page(message: str) -> str:
    return render_template(
        "index.html",
        message=message,
        packs=pack.PACKS.values(),
        type_lines=TypeLine,
        colors=Color,
        rarities=Rarity,
        formats=Format,
        comparisons=Comparison,
    )


def _parse_optional_enum(enum_cls, raw: str, field_name: str):
    """Parse an optional enum form field; blank input means "no filter"."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return enum_cls(raw)
    except ValueError:
        valid = ", ".join(member.value for member in enum_cls)
        raise ValueError(f"Invalid {field_name}: {raw!r} (expected one of: {valid})") from None


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
    
    return _render_page(message)


@app.route("/momir", methods=["POST"])
def submit_momir():
    raw = request.form.get("mana_value", "").strip()
    try:
        mana_value = int(raw)
    except ValueError:
        message = f"Invalid mana value: {raw!r}" if raw else "No mana value provided."
        return _render_page(message), 400

    try:
        builder = SearchBuilder()
        builder.add_card_type("creature")
        builder.add_mana_value(mana_value)
        url = builder.build_url_single_card()
        json = fetch_json(url)
        card = Card.from_json(json)
        card.print()
        message = f"Printed {card.name}"
        return _render_page(message)
    except HttpRequestError as err:
        _print_http_error_receipt(err)
        if err.status_code == 503:
            message = "Card service is temporarily unavailable. Error receipt sent to printer."
        else:
            message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return _render_page(message), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return _render_page(message), 500


@app.route("/search", methods=["POST"])
def submit_search():
    card_name = request.form.get("card_name", "").strip()
    if not card_name:
        return _render_page("No card name provided."), 400

    try:
        card_json = fetch_card(card_name)
        card = Card.from_json(card_json)
        card.print()
        message = f"Printed {card.name}"
        return _render_page(message)
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or f"No card found matching {card_name!r}."
            return _render_page(message), 404
        _print_http_error_receipt(err)
        if err.status_code == 503:
            message = "Card service is temporarily unavailable. Error receipt sent to printer."
        else:
            message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return _render_page(message), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return _render_page(message), 500


@app.route("/filter", methods=["POST"])
def submit_filter():
    try:
        mana_value_comparison = _parse_optional_enum(
            Comparison, request.form.get("mana_value_comparison"), "mana value comparison"
        ) or Comparison.EQUAL
        rarity_comparison = _parse_optional_enum(
            Comparison, request.form.get("rarity_comparison"), "rarity comparison"
        ) or Comparison.EQUAL
        rarity = _parse_optional_enum(Rarity, request.form.get("rarity"), "rarity")
        format_value = _parse_optional_enum(Format, request.form.get("format"), "format")
        colors = [Color(value) for value in request.form.getlist("colors")]
    except ValueError as err:
        return _render_page(str(err)), 400

    mana_value_raw = request.form.get("mana_value", "").strip()
    mana_value = None
    if mana_value_raw:
        try:
            mana_value = int(mana_value_raw)
        except ValueError:
            return _render_page(f"Invalid mana value: {mana_value_raw!r}"), 400

    builder = SearchBuilder()

    card_type = request.form.get("card_type", "").strip()
    if card_type:
        builder.add_card_type(card_type)

    exclude_card_type = request.form.get("exclude_card_type", "").strip()
    if exclude_card_type:
        builder.add_exclude_card_type(exclude_card_type)

    if mana_value is not None:
        builder.add_mana_value(mana_value, mana_value_comparison)

    if colors:
        builder.add_color(colors)

    if rarity is not None:
        builder.add_rarity(rarity, rarity_comparison)

    if format_value is not None:
        builder.add_format(format_value)

    if request.form.get("exclude_lands") == "enabled":
        builder.add_exclude_lands()

    set_name = request.form.get("set_name", "").strip()
    if set_name:
        builder.add_set_name(set_name)

    try:
        card_json = fetch_json(builder.build_url_single_card())
        card = Card.from_json(card_json)
        card.print()
        message = f"Printed {card.name}"
        return _render_page(message)
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or "No cards found matching those filters."
            return _render_page(message), 404
        _print_http_error_receipt(err)
        if err.status_code == 503:
            message = "Card service is temporarily unavailable. Error receipt sent to printer."
        else:
            message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return _render_page(message), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return _render_page(message), 500


@app.route("/deck", methods=["POST"])
def submit_deck():
    uploaded_file = request.files.get("deck_file")
    if uploaded_file is None or not uploaded_file.filename:
        return _render_page("No deck file provided."), 400

    try:
        deck_text = uploaded_file.read().decode("utf-8")
    except UnicodeDecodeError:
        return _render_page("Deck file must be valid UTF-8 text."), 400

    card_names = [line.strip() for line in deck_text.splitlines() if line.strip()]
    if not card_names:
        return _render_page("Deck file did not contain any card names."), 400

    try:
        cards = [Card.from_json(fetch_card(card_name)) for card_name in card_names]
        for card in cards:
            card.print()
        message = f"Printed {len(cards)} cards."
        return _render_page(message)
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or "One or more cards in the deck could not be found."
            return _render_page(message), 404
        _print_http_error_receipt(err)
        if err.status_code == 503:
            message = "Card service is temporarily unavailable. Error receipt sent to printer."
        else:
            message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return _render_page(message), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return _render_page(message), 500


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
    return jsonify({"packs": [loaded_pack.to_dict() for loaded_pack in pack.PACKS.values()]})


@app.route("/packs/<pack_type>", methods=["POST"])
def open_pack(pack_type):
    selected_pack = pack.PACKS.get(pack_type)
    if selected_pack is None:
        return jsonify({
            "error": f"Unknown pack type: {pack_type!r}",
            "available_packs": sorted(pack.PACKS),
        }), 404

    body = request.get_json(silent=True) or {}
    set_code = (body.get("set") or request.form.get("set") or request.args.get("set") or "").strip() or None

    try:
        cards = selected_pack.open(set_code=set_code, print_cards=True)
        return jsonify({
            "pack_type": selected_pack.name,
            "display_name": selected_pack.display_name,
            "set": set_code,
            "printed_count": len(cards),
            "cards": cards,
        })
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or f"No cards found for pack type {pack_type!r}."
            return jsonify({"error": message}), 404
        _print_http_error_receipt(err)
        if err.status_code == 503:
            error_msg = "Card service is temporarily unavailable. Error receipt sent to printer."
        else:
            error_msg = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return jsonify({"error": error_msg}), 502
    except (RuntimeError, ValueError) as err:
        return jsonify({"error": f"Failed to open pack: {err}"}), 500


@app.route("/pack", methods=["POST"])
def submit_pack():
    pack_type = request.form.get("pack_type", "").strip()
    selected_pack = pack.PACKS.get(pack_type)
    if selected_pack is None:
        message = f"Unknown pack type: {pack_type!r}" if pack_type else "No pack type provided."
        return _render_page(message), 400

    set_code = request.form.get("set_code", "").strip() or None

    try:
        cards = selected_pack.open(set_code=set_code, print_cards=True)
        card_names = ", ".join(card["name"] for card in cards)
        message = f"Opened {selected_pack.display_name} and printed {len(cards)} cards: {card_names}"
        return _render_page(message)
    except HttpRequestError as err:
        if err.status_code == 404:
            message = err.details or f"No cards found for pack type {pack_type!r}."
            return _render_page(message), 404
        _print_http_error_receipt(err)
        if err.status_code == 503:
            message = "Card service is temporarily unavailable. Error receipt sent to printer."
        else:
            message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return _render_page(message), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return _render_page(message), 500


@app.route("/discord", methods=["POST"])
def submit_discord():
    include_illegal = 'enabled' in request.form.getlist('illegal_cards')

    builder = SearchBuilder()

    if not include_illegal:
        builder.add_commander_legality()
        
    builder.add_exclude_lands()
    url = builder.build_url_single_card()
    
    try:
        json = fetch_json(url)
        card = Card.from_json(json)
        card.print()
        message = f"Printed {card.name}"
        return _render_page(message)
    except HttpRequestError as err:
        _print_http_error_receipt(err)
        if err.status_code == 503:
            message = "Card service is temporarily unavailable. Error receipt sent to printer."
        else:
            message = f"Request failed with HTTP {err.status_code}. Error receipt sent to printer."
        return _render_page(message), 502
    except (RuntimeError, ValueError) as err:
        message = f"Print failed: {err}"
        return _render_page(message), 500

if __name__ == "__main__":
    app.run()
