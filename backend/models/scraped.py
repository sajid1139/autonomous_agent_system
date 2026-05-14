from tortoise.models import Model
from tortoise import fields

class ScrapedSite(Model):
    id = fields.UUIDField(pk=True)
    url = fields.TextField()
    domain = fields.CharField(max_length=255)
    content = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True)
