from django.db import models
from django.conf import settings

class QA(models.Model):
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qas'
    )

    def __str__(self):
        return f"Q: {self.question[:50]}"
