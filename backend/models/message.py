from tortoise import fields, models

class Message(models.Model):
    id = fields.UUIDField(pk=True)
    goal = fields.ForeignKeyField("models.Goal", related_name="messages", on_delete=fields.CASCADE)
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "messages"
