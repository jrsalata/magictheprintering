# magictheprintering

A hello world Flask web application.

## Setup

We will be using Python Virtual Environments to make installing packages safer

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
flask run
```

The app will be available at http://localhost:5000 and returns `Hello, World!`.

## Test

```bash
pytest
```

## Image URL Support

The sample block builder in [printer.py](printer.py) can use either:

- A local sample image file (`sample_data/tle-74-aang-airbending-master.jpg`)
- An image URL that will be downloaded and embedded as a base64 data URL

Example:

```python
from printer import build_hello_world_blocks

payload = build_hello_world_blocks(
	"https://cards.scryfall.io/art_crop/front/d/e/de7a150b-1b0d-4928-a2cc-80a4b7412350.jpg?1783904837"
)
```

## HTTP Error Receipts

When an HTTP error is raised inside app routes, the app now attempts to print
an error receipt using JSON templates.

Templates live under:

- `error_templates/http/404.json`
- `error_templates/http/4xx.json`
- `error_templates/http/5xx.json`
- `error_templates/http/default.json`
- `error_templates/default.json`

Template placeholders include:

- `{{source}}`
- `{{status}}`
- `{{details}}`
- `{{url}}`
- `{{timestamp}}`

Template resolution order is:

1. exact status code (example: `404.json`)
2. status family (example: `4xx.json`)
3. `http/default.json`
4. `default.json`