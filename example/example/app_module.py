from fastnest.core.decorators import Module
from example.config.config_module import ConfigModule
from example.database.database_module import DatabaseModule
from example.auth.auth_module import AuthModule
from example.users.users_module import UsersModule
from example.posts.posts_module import PostsModule

@Module(
    imports=[
        ConfigModule.for_root(),
        DatabaseModule,
        AuthModule,
        UsersModule,
        PostsModule,
    ],
)
class AppModule:
    pass