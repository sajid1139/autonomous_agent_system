from tortoise.models import Model
from tortoise import fields

class Task(Model):
    id = fields.UUIDField(pk=True)
    goal = fields.ForeignKeyField("models.Goal", related_name="tasks")
    name = fields.CharField(max_length=200)
    agent = fields.CharField(max_length=100)
    status = fields.CharField(max_length=50, default="pending")
    result = fields.TextField(null=True)
    order = fields.IntField(default=0)