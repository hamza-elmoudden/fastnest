from fastnest.core.factory import create_app
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from example.app_module import AppModule

app = create_app(AppModule, debug=True, title="FastNest + PostgreSQL")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(x) for x in err["loc"] if x != "body")
        errors.append({"field": field, "message": err["msg"], "type": err["type"]})
    return JSONResponse(
        status_code=422,
        content={"statusCode": 422, "message": "Validation failed", "errors": errors},
    )