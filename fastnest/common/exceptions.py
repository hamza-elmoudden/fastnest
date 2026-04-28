# fastnest/common/exceptions.py
from fastapi import HTTPException


class HttpException(HTTPException):
    def __init__(self, message: str, status_code: int = 500, *, error: str = None):
        detail = {
            "statusCode": status_code,
            "message": message,
            "error": error or self.__class__.__name__,
        }
        super().__init__(status_code=status_code, detail=detail)


class BadRequestException(HttpException):
    def __init__(self, message: str = "Bad Request"):
        super().__init__(message, 400, error="Bad Request")


class UnauthorizedException(HttpException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401, error="Unauthorized")


class ForbiddenException(HttpException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403, error="Forbidden")


class NotFoundException(HttpException):
    def __init__(self, message: str = "Not Found"):
        super().__init__(message, 404, error="Not Found")


class ConflictException(HttpException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, 409, error="Conflict")


class UnprocessableEntityException(HttpException):
    def __init__(self, message: str = "Unprocessable Entity"):
        super().__init__(message, 422, error="Unprocessable Entity")


class InternalServerErrorException(HttpException):
    def __init__(self, message: str = "Internal Server Error"):
        super().__init__(message, 500, error="Internal Server Error")


class ServiceUnavailableException(HttpException):
    def __init__(self, message: str = "Service Unavailable"):
        super().__init__(message, 503, error="Service Unavailable")