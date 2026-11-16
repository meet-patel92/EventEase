from django.db import models


class Review(models.Model):
    class Rating(models.IntegerChoices):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="reviews"
    )
    event = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.IntegerField(choices=Rating.choices)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        unique_together = ("user", "event")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Review {self.id} - {self.event.title}"
