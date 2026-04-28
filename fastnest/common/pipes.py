from typing import Type, Optional, Any, get_type_hints
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException
from fastnest.common.interfaces import PipeTransform
from fastnest.common.base import SchemaAwarePipe


class ValidationPipe(SchemaAwarePipe, PipeTransform):

    def __init__(
        self,
        schema: Optional[Type[BaseModel]] = None,
        *,
        whitelist: bool = False,
        forbid_non_whitelisted: bool = False,
        transform: bool = True,
    ):
        self.schema = schema
        self.whitelist = whitelist
        self.forbid_non_whitelisted = forbid_non_whitelisted
        self.transform_output = transform   # ← renamed: لا يطغى على method

    def __call__(self, *args, **kwargs):
        return self

    def _resolve_schema(self, value: Any) -> Optional[Type[BaseModel]]:
        if self.schema is not None:
            return self.schema
        if isinstance(value, BaseModel):
            return type(value)
        return None

    def transform_value(self, value: Any) -> Any:
        schema = self._resolve_schema(value)

        if schema is None:
            return value

        if isinstance(value, schema):
            return self._apply_whitelist(value, schema)

        try:
            if isinstance(value, dict):
                dto = schema(**value)
            else:
                dto = schema.model_validate(value)
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "statusCode": 400,
                    "message": "Validation failed",
                    "errors": [
                        {
                            "field": ".".join(str(x) for x in err["loc"]),
                            "message": err["msg"],
                            "type": err["type"],
                        }
                        for err in e.errors()
                    ],
                },
            )

        return self._apply_whitelist(dto, schema)

    def _apply_whitelist(self, dto: BaseModel, schema: Type[BaseModel]):
        if not (self.whitelist or self.forbid_non_whitelisted):
            return dto

        allowed_fields = set(schema.model_fields.keys())
        raw = dto.model_dump()
        extra = set(raw.keys()) - allowed_fields

        if self.forbid_non_whitelisted and extra:
            raise HTTPException(
                status_code=400,
                detail={
                    "statusCode": 400,
                    "message": "Validation failed",
                    "errors": [
                        {"field": f, "message": "property should not exist"}
                        for f in extra
                    ],
                },
            )

        if self.whitelist and extra:
            cleaned = {k: v for k, v in raw.items() if k in allowed_fields}
            return schema(**cleaned)

        return dto

    def transform(self, value: Any) -> Any:
        """Entry point called by the framework pipeline."""
        if not self.transform_output:
            return value
        return self.transform_value(value)


class ParseIntPipe(PipeTransform):
    def transform(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail={
                    "statusCode": 400,
                    "message": "Validation failed (numeric string is expected)",
                },
            )


class ParseBoolPipe(PipeTransform):
    TRUTHY = {"true", "1", "yes", "on"}
    FALSY  = {"false", "0", "no", "off"}

    def transform(self, value):
        if isinstance(value, bool):
            return value
        v = str(value).strip().lower()
        if v in self.TRUTHY:
            return True
        if v in self.FALSY:
            return False
        raise HTTPException(
            status_code=400,
            detail={
                "statusCode": 400,
                "message": "Validation failed (boolean string is expected)",
            },
        )


class DefaultValuePipe(PipeTransform):
    def __init__(self, default):
        self.default = default

    def transform(self, value):
        return self.default if value is None else value