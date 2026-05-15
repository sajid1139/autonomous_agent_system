from tortoise import fields, models

class Message(models.Model):
    id = fields.UUIDField(pk=True)
    goal_id = fields.UUIDField()
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "messages"
