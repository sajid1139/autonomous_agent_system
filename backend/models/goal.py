from tortoise.models import Model
from tortoise import fields

class Goal(Model):
    id = fields.UUIDField(pk=True)
    text = fields.TextField()
    status = fields.CharField(max_length=50, default="pending")
    created = fields.DatetimeField(auto_now_add=True)