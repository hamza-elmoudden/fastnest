from fastnest.core.decorators import Module
from .${name}_controller import ${ClassName}Controller
from .${name}_service import ${ClassName}Service


@Module(controllers=[${ClassName}Controller], providers=[${ClassName}Service])
class ${ClassName}Module:
    pass
