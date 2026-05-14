from tortoise.models import Model
from tortoise import fields

class Session(Model):
    id = fields.UUIDField(pk=True)
    goal = fields.ForeignKeyField("models.Goal", related_name="sessions")
    state = fields.JSONField(default={})
    created = fields.DatetimeField(auto_now_add=True)