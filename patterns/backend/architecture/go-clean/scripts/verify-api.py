"""起動済みの検証用APIに一意なユーザーを作り、HTTP応答を確認する。"""

import json
import os
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8080").rstrip("/")


def request(method, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = Request(BASE_URL + path, data=body, method=method,
                  headers={"Content-Type": "application/json"})
    try:
        response = urlopen(req, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def expect_error(method, path, data, status, code):
    actual, body = request(method, path, data)
    if actual != status or body.get("error", {}).get("code") != code:
        raise RuntimeError(f"{method} {path}: expected {status}/{code}, got {actual}/{body}")


def main():
    for attempt in range(60):
        try:
            if request("GET", "/healthz")[0] == 200:
                break
        except (URLError, TimeoutError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError("API did not become ready within 60 seconds")

    email = f"smoke-{uuid.uuid4()}@example.com"
    data = {"name": "  Taro  ", "email": email.upper()}
    status, created = request("POST", "/users", data)
    if status != 201 or created.get("name") != "Taro" or created.get("email") != email:
        raise RuntimeError(f"create: expected 201, trimmed name, lowercased email; got {status}/{created}")
    uuid.UUID(created["id"])
    if not created.get("created_at"):
        raise RuntimeError("create: missing created_at")
    status, found = request("GET", "/users/" + created["id"])
    if status != 200 or found != created:
        raise RuntimeError(f"get: expected the persisted user, got {status}/{found}")
    expect_error("POST", "/users", data, 409, "already_exists")
    expect_error("POST", "/users", {"name": " ", "email": email}, 400, "invalid_argument")
    expect_error("POST", "/users", {"name": "Taro", "email": "invalid"}, 400, "invalid_argument")
    expect_error("POST", "/users", {**data, "extra": True}, 400, "invalid_request")
    expect_error("GET", "/users/invalid", None, 400, "invalid_argument")
    expect_error("GET", "/users/" + str(uuid.uuid4()), None, 404, "not_found")
    print("API smoke: health, create, persisted get, normalization, duplicate, invalid input, unknown field, missing user passed")


if __name__ == "__main__":
    main()
