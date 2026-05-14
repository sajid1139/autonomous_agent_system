from tortoise.models import Model
from tortoise import fields

class Report(Model):
    id = fields.UUIDField(pk=True)
    goal = fields.ForeignKeyField("models.Goal", related_name="reports")
    content = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True)