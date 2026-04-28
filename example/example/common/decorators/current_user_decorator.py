from fastnest.common.decorators import createParamDecorator

CurrentUser = createParamDecorator(
    lambda data, request: getattr(request.state, "user", None)
)