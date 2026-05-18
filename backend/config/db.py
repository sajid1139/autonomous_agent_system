from dotenv import load_dotenv
load_dotenv()

import os
from tortoise import Tortoise

TORTOISE_ORM = {
    "connections": {"default": os.getenv("DB_URL")},
    "apps": {
        "models": {
            "models": ["models.goal", "models.task", "models.session", "models.report", "models.scraped", "models.message"],
            "default_connection": "default",
        }
    },
}

async def init():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)

async def close():
    await Tortoise.close_connections()