import inspect
from fastapi import (
    Request,
    Body as FBody,
    Query as FQuery,
    Path as FPath,
    Header as FHeader,
)
from fastnest.core.params import _ParamMarker, ParamType
from fastnest.core.signature_cache import get_cached_signature


_RESERVED_REQUEST_KEY = "__nest_request__"


def _marker_to_fastapi_default(marker: _ParamMarker):
    default = marker.default if marker.default is not ... else ...

    if marker.type == ParamType.BODY:
        if marker.key:
            return FBody(default, alias=marker.key, embed=True)
        return FBody(default)

    if marker.type == ParamType.QUERY:
        return FQuery(default, alias=marker.key) if marker.key else FQuery(default)

    if marker.type == ParamType.PARAM:
        return FPath(default, alias=marker.key) if marker.key else FPath(default)

    if marker.type == ParamType.HEADERS:
        return FHeader(default, alias=marker.key) if marker.key else FHeader(default)

    return default


def rewrite_handler_signature(handler):
    
    original = get_cached_signature(handler)
    new_params = []
    handler_params = set()
    user_request_name = None

    for name, param in original.parameters.items():
        if name == "self":
            continue
        default = param.default

        if isinstance(default, _ParamMarker):
            marker = default

            # Custom param decorator (createParamDecorator)
            if marker._custom_extractor is not None:
                # Bug fix 2: do NOT add to handler_params — value comes from extractor, not kwargs
                func = getattr(handler, "__func__", handler)
                func._custom_extractors = getattr(func, "_custom_extractors", {})
                func._custom_extractors[name] = (marker._custom_extractor, marker._custom_data)
                # ensure request param is in signature so FastAPI injects it
                if user_request_name is None:
                    user_request_name = name
                    new_params.append(param.replace(
                        annotation=Request,
                        default=inspect.Parameter.empty,
                    ))
                # skip — not added to handler_params, not added to new_params
                continue

            # Standard marker (Body, Query, Param, Headers, Req)
            if marker.type == ParamType.REQ:
                user_request_name = name
                new_params.append(param.replace(
                    annotation=Request,
                    default=inspect.Parameter.empty,
                ))
                continue

            new_default = _marker_to_fastapi_default(marker)
            new_params.append(param.replace(default=new_default))
        else:
            if param.annotation is Request:
                user_request_name = name
            new_params.append(param)

        handler_params.add(name)  # Bug fix 2: only params that reach here are in the signature

    request_alias = user_request_name or _RESERVED_REQUEST_KEY
    if user_request_name is None:
        new_params.append(inspect.Parameter(
            _RESERVED_REQUEST_KEY,
            kind=inspect.Parameter.KEYWORD_ONLY,
            annotation=Request,
        ))

    # ── Fix: sort params so non-default never follows default ──────────────
    # Rules (Python + FastAPI):
    #   1. POSITIONAL_OR_KEYWORD without default  → first
    #   2. POSITIONAL_OR_KEYWORD with default     → second
    #   3. KEYWORD_ONLY (FastAPI Body/Query/Path) → any order, FastAPI handles them
    #   4. Request param must be KEYWORD_ONLY with no default to avoid the error
    #
    # Strategy: convert the request param to KEYWORD_ONLY so it never conflicts.

    final_params = []
    request_param = None

    for p in new_params:
        if p.annotation is Request:
            # Force to KEYWORD_ONLY — FastAPI accepts this fine
            request_param = p.replace(kind=inspect.Parameter.KEYWORD_ONLY)
        else:
            final_params.append(p)

    # non-default positional first, default positional second, then kw-only
    no_default = [p for p in final_params
                  if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
                  and p.default is inspect.Parameter.empty]
    with_default = [p for p in final_params
                    if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
                    and p.default is not inspect.Parameter.empty]
    kw_only = [p for p in final_params
               if p.kind == inspect.Parameter.KEYWORD_ONLY]

    ordered = no_default + with_default + kw_only
    if request_param is not None:
        ordered.append(request_param)

    new_signature = inspect.Signature(parameters=ordered)
    return new_signature, handler_params, request_alias