"""Run the OPA validator gRPC wrapper server."""

import asyncio
import os
import sys
import traceback

from apme_engine.daemon.opa_validator_server import serve


async def _run(listen: str) -> None:
    """Start the OPA validator server and wait for termination.

    Args:
        listen: Host:port address to bind (e.g. 0.0.0.0:50054).
    """
    server = await serve(listen)
    sys.stderr.write(f"OPA validator (gRPC wrapper) listening on {listen}\n")
    sys.stderr.flush()
    await server.wait_for_termination()


def main() -> None:
    """Entry point: run OPA validator gRPC server until interrupted.

    Uses APME_OPA_VALIDATOR_LISTEN for bind address. Exits with code 1 on failure.
    """
    from apme_engine.log_bridge import install_handler

    install_handler()

    listen = os.environ.get("APME_OPA_VALIDATOR_LISTEN", "0.0.0.0:50054")
    try:
        asyncio.run(_run(listen))
    except Exception as e:
        sys.stderr.write(f"OPA validator failed: {e}\n")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
