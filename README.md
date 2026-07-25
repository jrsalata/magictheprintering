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