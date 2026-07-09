# fastnest/core/tokens.py
"""
Injection tokens — support for NestJS-style @Inject() when a plain type
annotation can't express what to resolve (e.g. binding to a string token,
or overriding what would otherwise be inferred from the annotation).
"""


class Inject:
    """
    Marks a constructor parameter for resolution by token instead of by its
    type annotation. Used as a parameter default:

        @Injectable()
        class UsersService:
            def __init__(self, config: dict = Inject("CONFIG_TOKEN")):
                self.config = config

    `token` can be any hashable value used as a `provide` key — a class, a
    string, or any other symbol-like object.
    """
    __slots__ = ("token",)

    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f"Inject({self.token!r})"
