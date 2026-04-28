import time
from fastapi import Request
from fastnest.common.interfaces import NestInterceptor
from fastnest.common.logger import Logger

class LoggingInterceptor(NestInterceptor):
    def __init__(self):
        self.logger = Logger("HTTP")

    def intercept_before(self, request: Request):
        request.state.t0 = time.time()

    def intercept_after(self, request: Request, response):
        ms = (time.time() - request.state.t0) * 1000
        self.logger.info(f"{request.method} {request.url.path} {ms:.1f}ms")
        return response