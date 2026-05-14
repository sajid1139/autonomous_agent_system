import os
from tortoise import Tortoise

async def init():
    await Tortoise.init(
        db_url=os.getenv("DB_URL"),
        modules={"models": ["models.goal", "models.task", "models.session", "models.report", "models.scraped"]}
    )
    await Tortoise.generate_schemas()

async def close():
    await Tortoise.close_connections()