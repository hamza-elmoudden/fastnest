from fastnest.core.decorators import Module
from .posts_controller import PostsController
from .posts_service import PostsService

@Module(controllers=[PostsController], providers=[PostsService])
class PostsModule:
    pass