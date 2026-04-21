import orjson
from werkzeug.wrappers import Response


def surge_response(data: dict | list, status: int = 200) -> Response:
	"""Return an orjson-serialized HTTP response — 10x faster than stdlib json."""
	return Response(
		orjson.dumps(data, option=orjson.OPT_NON_STR_KEYS),
		status=status,
		mimetype="application/json",
	)


def dumps(data) -> bytes:
	return orjson.dumps(data)


def loads(data: bytes | str) -> dict | list:
	return orjson.loads(data)
