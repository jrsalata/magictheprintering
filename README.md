# magictheprintering

A Flask web application for printing Magic cards.

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

The app will be available at http://localhost:5000.

The UI supports:

- printing hello world and fortunes
- searching for and printing a single card by name
- uploading a UTF-8 plain text deck list file where each non-empty line is a card name

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

## Running as a Service (Linux / systemd)

A `magictheprintering.service` unit file is included in the project root.

Before installing, ensure a `.env` file exists in the deployment directory with the required environment variables:

```text
PRINTER_URL=<your printer URL>
PRINTER_USERNAME=<your printer username>
PRINTER_PASSWORD=<your printer password>
SEARCH_URL=<your card search API URL>
```

The port defaults to `5000`. To change it, edit `FLASK_RUN_PORT` in `magictheprintering.service` before installing, or override it after install:

```bash
sudo systemctl edit magictheprintering
# Add under [Service]:
# Environment=FLASK_RUN_PORT=8080
```

Then install and enable the service:

```bash
sudo cp magictheprintering.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now magictheprintering
```

Check that it started successfully:

```bash
sudo systemctl status magictheprintering
```

The app will be available at `http://<host-ip>:5000`.
