import json
from typing import Any, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import search_builder


def fetch_json(url: str, timeout: int = 10) -> Union[dict[str, Any], list[Any]]:
	"""Send a GET request to the given URL and return the parsed JSON body."""
	request = Request(
		url,
		method="GET",
		headers={
			"Accept": "application/json",
			"User-Agent": "magictheprintering/1.0",
		},
	)

	try:
		with urlopen(request, timeout=timeout) as response:
			raw = response.read().decode("utf-8")
			return json.loads(raw)
	except json.JSONDecodeError as err:
		raise RuntimeError("GET response was not valid JSON") from err
	except HTTPError as err:
		details = err.read().decode("utf-8", errors="replace")
		raise RuntimeError(f"GET request failed with HTTP {err.code}: {details}") from err
	except URLError as err:
		raise RuntimeError(f"Failed to connect to URL: {err.reason}") from err


if __name__ == "__main__":
    search_builder_instance = search_builder.SearchBuilder()
    search_builder_instance.add_color([search_builder.Color.Color.RED, search_builder.Color.Color.GREEN])
    search_builder_instance.add_card_type("creature")
    try:
        result = fetch_json(search_builder_instance.build_url_single_card())
        print(json.dumps(result, indent=2))
    except RuntimeError as err:
        print(f"Error fetching JSON: {err}")