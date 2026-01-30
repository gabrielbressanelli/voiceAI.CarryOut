from django.contrib import admin
from .models import WeeklyHours, HoursOverride, StoreSettings

admin.site.register(WeeklyHours)
admin.site.register(HoursOverride)
admin.site.register(StoreSettings)

# Register your models here.
