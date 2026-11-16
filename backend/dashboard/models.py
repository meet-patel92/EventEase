from django.db import models


class DashboardStat(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    date = models.DateField(auto_now_add=True)

    class Meta:
        db_table = "dashboard_stats"
        ordering = ("-date",)

    def __str__(self):
        return f"{self.name}: {self.value}"
