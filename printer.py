"""Simple printer client for sending block-based print jobs.

Environment variables:
- PRINTER_URL
- PRINTER_USERNAME
- PRINTER_PASSWORD
"""

import base64
from io import BytesIO
import json
import os
from dotenv import load_dotenv
from PIL import Image
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _image_file_to_data_url(image_path: str) -> str:
	"""Read an image file with PIL and return a data URL payload string."""
	with Image.open(image_path) as image:
		return _image_to_data_url(image)


def _image_url_to_data_url(image_url: str, timeout: int = 30) -> str:
	"""Download an image from URL and convert it to a data URL payload string."""
	request = Request(
		image_url,
		headers={"User-Agent": "magictheprintering/1.0"},
	)
	with urlopen(request, timeout=timeout) as response:
		image_bytes = response.read()

	with Image.open(BytesIO(image_bytes)) as image:
		return _image_to_data_url(image)


def _image_to_data_url(image: Image.Image) -> str:
	"""Encode an in-memory PIL image to a base64 data URL string."""
	image_format = (image.format or "PNG").upper()
	if image_format == "JPG":
		image_format = "JPEG"
	buffer = BytesIO()
	image.save(buffer, format=image_format)

	encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
	return f"data:image/{image_format.lower()};base64,{encoded}"

def _printer_config() -> tuple[str, str, str]:
	"""Read and validate printer connection settings from the environment."""
	load_dotenv()
	
	url = os.getenv("PRINTER_URL", "").strip()
	username = os.getenv("PRINTER_USERNAME", "").strip()
	password = os.getenv("PRINTER_PASSWORD", "").strip()

	missing = [
		name
		for name, value in (
			("PRINTER_URL", url),
			("PRINTER_USERNAME", username),
			("PRINTER_PASSWORD", password),
		)
		if not value
	]
	if missing:
		raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

	return url.rstrip("/"), username, password


# Example of blocks
def build_hello_world_blocks(image_url: str | None = None) -> dict[str, Any]:
	"""Return a simple block payload with text and an image.

	If image_url is provided, the image is downloaded and embedded as a data URL.
	Otherwise, the local sample image file is used.
	"""
	sample_image_path = os.path.join(
		os.path.dirname(__file__),
		"sample_data",
		"tle-74-aang-airbending-master.jpg",
	)
	image_data_url = (
		_image_url_to_data_url(image_url)
		if image_url
		else _image_file_to_data_url(sample_image_path)
	)

	return {
		"blocks": [
			{"type": "text", "text": "Hello, World!"},
			{
				"type": "image",
				"image": image_data_url,
				"center": True,
			},
		]
	}

def build_message(message: str) -> dict[str, Any]:
	"""Return a block payload that prints the given message."""
	return {
		"blocks": [
			{"type": "text", "text": message},
		]
	}

def send_print_momir(payload: dict[str, Any], timeout: int = 100) -> dict[str, Any]:
	# TODO replace with actual logic
	send_print_job(payload, timeout)

def send_print_discord(payload: dict[str, Any], timeout: int = 100) -> dict[str, Any]:
	# TODO replace with actual logic
	send_print_job(payload, timeout)

def send_print_job(payload: dict[str, Any], timeout: int = 100) -> dict[str, Any]:
	"""POST a print payload to the printer's /builder endpoint."""
	base_url, username, password = _printer_config()
	endpoint = f"{base_url}/builder"

	credentials = f"{username}:{password}".encode("utf-8")
	auth_header = base64.b64encode(credentials).decode("ascii")

	request = Request(
		endpoint,
		data=json.dumps(payload).encode("utf-8"),
		method="POST",
		headers={
			"Content-Type": "application/json",
			"Authorization": f"Basic {auth_header}",
			"User-Agent": "magictheprintering/1.0"
		},
	)

	try:
		with urlopen(request, timeout=timeout) as response:
			status_code = response.getcode()
			content_type = (response.headers.get("Content-Type") or "").lower()
			raw = response.read().decode("utf-8")
			if not raw:
				return {"success": True}

			try:
				return json.loads(raw)
			except json.JSONDecodeError:
				# Some servers return HTML (login/error page) instead of JSON.
				if "html" in content_type or raw.lstrip().startswith("<"):
					raise RuntimeError(
						"Printer API returned HTML instead of JSON. "
						"Check PRINTER_URL points to the API base and verify credentials."
					)

				return {
					"success": 200 <= status_code < 300,
					"status_code": status_code,
					"content_type": content_type,
					"raw": raw,
				}
	except HTTPError as err:
		details = err.read().decode("utf-8", errors="replace")
		raise RuntimeError(f"Printer API HTTP {err.code}: {details}") from err
	except URLError as err:
		raise RuntimeError(f"Failed to connect to printer API: {err.reason}") from err

if __name__ == "__main__":
	# Example usage
	payload = build_hello_world_blocks("https://cards.scryfall.io/art_crop/front/d/e/de7a150b-1b0d-4928-a2cc-80a4b7412350.jpg?1783904837")
	response = send_print_job(payload)
	print("Print job response:", response)