"""Gateway scan client — translates uploaded files into a Primary.ScanStream call.

The gateway acts as a "CLI without a terminal" (ADR-029): it writes uploaded
files to a temp directory, constructs ``ScanChunk`` messages via the shared
chunked_fs module, streams them to Primary, and yields SSE-formatted progress
events back to the HTTP caller.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import grpc
import grpc.aio

from apme.v1 import primary_pb2_grpc
from apme_engine.daemon.chunked_fs import yield_scan_chunks

logger = logging.getLogger(__name__)


@dataclass
class UploadedFile:
    """A file received from the browser upload.

    Attributes:
        relative_path: Relative path preserving directory structure.
        content: Raw file bytes.
    """

    relative_path: str
    content: bytes


def _sanitize_path(relative_path: str) -> str:
    """Sanitize a user-provided relative path to prevent directory traversal.

    Strips leading slashes, rejects ``..`` components, and normalises to
    a POSIX-style relative path safe for joining with a temp directory.

    Args:
        relative_path: Raw path from the upload filename.

    Returns:
        Sanitized relative path string.

    Raises:
        ValueError: If the path contains traversal components.
    """
    cleaned = PurePosixPath(relative_path.replace("\\", "/"))
    parts = [p for p in cleaned.parts if p != "/"]
    if ".." in parts:
        raise ValueError(f"Path traversal detected: {relative_path!r}")
    if cleaned.is_absolute():
        parts = parts[1:]
    return str(PurePosixPath(*parts)) if parts else "unnamed"


def _sse(event: str, data: dict[str, object]) -> str:
    """Format a single SSE message.

    Args:
        event: SSE event type (progress, result, error).
        data: JSON-serializable payload.

    Returns:
        SSE-formatted string with trailing blank line.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def run_scan_stream(
    files: list[UploadedFile],
    primary_address: str,
    *,
    ansible_version: str = "",
    collections: list[str] | None = None,
    timeout: int = 300,
) -> AsyncIterator[str]:
    """Stream a scan through Primary and yield SSE events.

    Writes uploaded files to a temp directory, constructs ``ScanChunk``
    messages, calls ``Primary.ScanStream``, and yields SSE-formatted
    strings for each ``ScanEvent``.

    Args:
        files: Uploaded files from the browser.
        primary_address: gRPC address of the Primary orchestrator.
        ansible_version: Optional Ansible core version constraint.
        collections: Optional collection specifiers.
        timeout: gRPC call timeout in seconds.

    Yields:
        str: SSE-formatted event strings.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="apme-gw-scan-"))
    try:
        for f in files:
            safe_path = _sanitize_path(f.relative_path)
            dest = temp_dir / safe_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(f.content)

        chunks = yield_scan_chunks(
            temp_dir,
            project_root_name="upload",
            ansible_core_version=ansible_version or None,
            collection_specs=collections,
        )

        channel = grpc.aio.insecure_channel(primary_address)
        try:
            stub = primary_pb2_grpc.PrimaryStub(channel)  # type: ignore[no-untyped-call]
            response_stream = stub.ScanStream(chunks, timeout=timeout)

            scan_id: str | None = None
            async for event in response_stream:
                oneof = event.WhichOneof("event")
                if oneof == "progress":
                    p = event.progress
                    yield _sse(
                        "progress",
                        {"phase": p.phase, "message": p.message, "level": p.level},
                    )
                    await asyncio.sleep(0)
                elif oneof == "result":
                    resp = event.result
                    scan_id = resp.scan_id
                    yield _sse(
                        "result",
                        {
                            "scan_id": resp.scan_id,
                            "total_violations": resp.diagnostics.total_violations
                            if resp.HasField("diagnostics")
                            else len(resp.violations),
                            "session_id": resp.session_id,
                        },
                    )
            if scan_id is None:
                yield _sse("error", {"message": "No scan result received from engine"})
        except grpc.aio.AioRpcError as e:
            yield _sse("error", {"message": f"Engine error: {e.details()}"})
        finally:
            await channel.close(grace=None)
    except Exception as exc:
        logger.exception("Scan stream failed: %s", exc)
        yield _sse("error", {"message": "Scan failed — check gateway logs for details"})
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
