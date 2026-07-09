import uvicorn

from fastnest.core.factory import create_app
from src.app_module import AppModule

app = create_app(AppModule)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
