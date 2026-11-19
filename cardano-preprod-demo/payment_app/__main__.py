from __future__ import annotations

import os

from payment_app.server import serve


def main() -> None:
    host = os.environ.get("PAYMENT_APP_HOST", "0.0.0.0")
    port = int(os.environ.get("PAYMENT_APP_PORT", "8787"))
    serve(host=host, port=port)


if __name__ == "__main__":
    main()
