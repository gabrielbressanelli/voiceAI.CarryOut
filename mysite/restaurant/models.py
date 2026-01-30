from django.db import models
from django.core.exceptions import ValidationError

class WeeklyHours(models.Model):
    """
    Base weekly schedule.
    day_of_the_week: 0=Mon ... 6=Sun (matches Python datetime.weekday()).
    """
    day_of_the_week = models.PositiveSmallIntegerField(unique=True)

    is_closed = models.BooleanField(default=False)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ["day_of_the_week"]

    def __str__(self):
        names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        d = names[self.day_of_the_week] if 0 <= self.day_of_the_week <= 6 else str(self.day_of_the_week)
        if self.is_closed:
            return f"{d} Closed"
        return f"{d}: {self.open_time} - {self.close_time}"
    
    def clean(self):
        # optional validation: ensure open and close are set if not closed
        if self.is_closed:
            return
        if not self.open_time or not self.close_time:
            raise ValidationError("open_time and close_time are required when is_closed is set to False.")
        if self.open_time >= self.close_time:
            raise ValidationError("open_time must be before close_time.")
        
class HoursOverride(models.Model):
    # Wins over weekly hours

    date = models.DateField(unique=True)

    is_closed = models.BooleanField(default=False)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)

    note = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        if self.is_closed:
            return f"{self.date}: Closed:({self.note or 'override'})"
        return f"{self.date}: {self.open_time} - {self.close_time} ({self.note or 'override'})"
    
    def clean(self):
        if self.is_closed:
            return
        if not self.open_time or not self.close_time:
            raise ValidationError("open_time or close_time required when is_closed is set to False.")
        if self.open_time >= self.close_time:
            raise ValidationError("open_time needs to be before closing time.")
        
class StoreSettings(models.Model):
    # Store Settings

    timezone = models.CharField(max_length=64, default='America/Detroit')

    is_temporarily_closed = models.BooleanField(default=False)
    temp_closed_note = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        verbose_name = 'Store Setting' 
        verbose_name_plural = 'Store Settings'

    def __str__(self):
        return 'Store Settings'

