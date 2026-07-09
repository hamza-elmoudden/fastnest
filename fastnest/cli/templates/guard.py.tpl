from fastapi import Request
from fastnest.common.interfaces import CanActivate


class ${ClassName}Guard(CanActivate):
    def can_activate(self, request: Request) -> bool:
        # TODO: implement your authorization logic here
        return True
