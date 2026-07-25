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