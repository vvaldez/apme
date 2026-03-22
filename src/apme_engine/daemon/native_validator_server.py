"""Native validator daemon: async gRPC server that runs in-tree Python rules on deserialized scandata."""

import asyncio
import json
import logging
import os
import time
from typing import cast

import grpc
import grpc.aio
import jsonpickle

from apme.v1 import common_pb2, validate_pb2, validate_pb2_grpc
from apme.v1.common_pb2 import HealthResponse, RuleTiming, ValidatorDiagnostics
from apme.v1.validate_pb2 import ValidateResponse
from apme_engine.daemon.violation_convert import violation_dict_to_proto
from apme_engine.engine.models import ViolationDict, YAMLDict
from apme_engine.log_bridge import attach_collector
from apme_engine.validators.base import ScanContext
from apme_engine.validators.native import NativeRunResult, NativeValidator

logger = logging.getLogger("apme.native")

_MAX_CONCURRENT_RPCS = int(os.environ.get("APME_NATIVE_MAX_RPCS", "32"))


def _run_native(hierarchy_payload: dict[str, object], scandata: object) -> NativeRunResult:
    """Blocking function: create ScanContext and run NativeValidator with timing.

    Args:
        hierarchy_payload: Parsed hierarchy payload for context.
        scandata: Deserialized scandata object.

    Returns:
        NativeRunResult with violations and rule timings.
    """
    scan_context = ScanContext(
        hierarchy_payload=cast(YAMLDict, hierarchy_payload),
        scandata=scandata,
    )
    validator = NativeValidator()
    return validator.run_with_timing(scan_context)


class NativeValidatorServicer(validate_pb2_grpc.ValidatorServicer):
    """Async gRPC adapter: deserializes scandata, runs native rules in executor."""

    async def Validate(
        self,
        request: validate_pb2.ValidateRequest,
        context: grpc.aio.ServicerContext,  # type: ignore[type-arg]
    ) -> ValidateResponse:
        """Handle Validate RPC: deserialize scandata, run native rules in executor.

        Args:
            request: ValidateRequest with hierarchy_payload and scandata.
            context: gRPC servicer context.

        Returns:
            ValidateResponse with violations and diagnostics.
        """
        req_id = request.request_id or ""
        t0 = time.monotonic()
        with attach_collector() as sink:
            try:
                logger.info("Native: validate start (req=%s)", req_id)

                hierarchy_payload: dict[str, object] = {}
                if request.hierarchy_payload:
                    try:
                        hierarchy_payload = json.loads(request.hierarchy_payload)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        logger.warning("Native: failed to decode hierarchy_payload (req=%s)", req_id)

                scandata = None
                if request.scandata:
                    try:
                        from apme_engine.engine import jsonpickle_handlers as _jp  # noqa: F401
                        from apme_engine.engine import models as _models  # noqa: F401
                        from apme_engine.engine import scanner as _scanner  # noqa: F401

                        _jp.register_engine_handlers()
                        for name in ("SingleScan",):
                            getattr(_scanner, name, None)
                        for name in (
                            "AnsibleRunContext",
                            "RunTargetList",
                            "RunTarget",
                            "TaskCall",
                            "Object",
                        ):
                            getattr(_models, name, None)
                        scandata = jsonpickle.decode(request.scandata.decode("utf-8"))
                    except Exception as e:
                        logger.error("Native: failed to decode scandata: %s (req=%s)", e, req_id)
                        return ValidateResponse(violations=[], request_id=req_id, logs=sink.entries)

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    _run_native,
                    hierarchy_payload,
                    scandata,
                )
                total_ms = (time.monotonic() - t0) * 1000
                logger.info(
                    "Native: validate done (%.0fms, %d violations, req=%s)", total_ms, len(result.violations), req_id
                )

                rule_timings = [
                    RuleTiming(
                        rule_id=rt.rule_id,
                        elapsed_ms=rt.elapsed_ms,
                        violations=rt.violations,
                    )
                    for rt in result.rule_timings
                ]
                diag = ValidatorDiagnostics(
                    validator_name="native",
                    request_id=req_id,
                    total_ms=total_ms,
                    files_received=len(request.files),
                    violations_found=len(result.violations),
                    rule_timings=rule_timings,
                )

                return validate_pb2.ValidateResponse(
                    violations=[violation_dict_to_proto(cast(ViolationDict, v)) for v in result.violations],
                    request_id=req_id,
                    diagnostics=diag,
                    logs=sink.entries,
                )
            except Exception as e:
                logger.exception("Native: unhandled error (req=%s): %s", req_id, e)
                return ValidateResponse(violations=[], request_id=req_id, logs=sink.entries)

    async def Health(
        self,
        request: common_pb2.HealthRequest,
        context: grpc.aio.ServicerContext,  # type: ignore[type-arg]
    ) -> HealthResponse:
        """Handle Health RPC.

        Args:
            request: Health request (unused).
            context: gRPC servicer context.

        Returns:
            HealthResponse with status "ok".
        """
        return HealthResponse(status="ok")


async def serve(listen: str = "0.0.0.0:50055") -> grpc.aio.Server:
    """Create, bind, and start async gRPC server with Native servicer.

    Args:
        listen: Host:port to bind (e.g. 0.0.0.0:50055).

    Returns:
        Started gRPC server (caller must wait_for_termination).
    """
    server = grpc.aio.server(
        maximum_concurrent_rpcs=_MAX_CONCURRENT_RPCS,
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
        ],
    )
    validate_pb2_grpc.add_ValidatorServicer_to_server(NativeValidatorServicer(), server)  # type: ignore[no-untyped-call]
    if ":" in listen:
        _, _, port = listen.rpartition(":")
        server.add_insecure_port(f"[::]:{port}")
    else:
        server.add_insecure_port(listen)
    await server.start()
    return server
