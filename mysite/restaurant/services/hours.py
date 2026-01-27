from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple

from django.utils import timezone

from restaurant.models import HoursOverride, StoreSettings, WeeklyHours

@dataclass(frozen=True)
class HoursResult:
    is_closed: bool
    open_time: Optional[time]
    close_time: Optional[time]
    source: str # override | weekly | settings

def get_store_settings() -> StoreSettings:
    obj = StoreSettings.objects.first()
    if obj:
        return obj
    return StoreSettings.objects.create()

def local_now() -> datetime:
    return timezone.localtime(timezone.now())

def get_hours_for_date(d: date) -> HoursResult:
    """" 
    Returns Hours for a certain local Date considering: 
    1) temporary closed 
    2) date override
    3) weekly schedule
    """

    settings = get_store_settings()
    if settings.is_temporarily_closed:
        return HoursResult(is_closed=True, open_time=None, close_time=None, source='settings')
    
    override = HoursOverride.objects.filter(date=d).first()

    if override:
        if override.is_closed:
            return HoursResult(is_closed=True, open_time=None, close_time=None, source='override')
        return HoursResult(is_closed=False, open_time=override.open_time, close_time=override.close_time, source='oerride')
    
    week_hours = WeeklyHours.objects.filter(day_of_the_week=d.weekday()).first()

    if not week_hours or week_hours.is_closed:
        return HoursResult(is_closed=True, open_time=None, close_time=None, source='weekly')

def is_open_at(dt_local: datetime) -> bool:
    hrs = get_hours_for_date(dt_local.date())

    if hrs.is_closed or not hrs.open_time or not hrs.close_time:
        return False
    
    t = dt_local.time()

    return hrs.open_time <= t <= hrs.close_time

def next_open_datetime(dt_local:datetime, search_days: int = 14) -> Optional[datetime]:
    # Finds next time store opens, starting from dt_local. Returns a local timezone-aware datetime.
    
    # If before today's opening time and today is not closed -> set today open_time

    today_hrs = get_hours_for_date(dt_local.time())
    if not today_hrs.is_closed and today_hrs.open_time and today_hrs.close_time:
        today_open=dt_local.replace(
            hour=today_hrs.open_time.hour,
            minute=today_hrs.open_time.minute,
            second=0,
            microsecond=0,
        )

        if dt_local < today_open:
            return today_open
        
        if is_open_at(dt_local):
            return dt_local
        
    # Otherwise look day by day
    base = dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(1, search_days + 1):
        d = (base + timedelta(days=i)).date()
        hrs = get_hours_for_date(d)
        if hrs.is_closed or not hrs.open_time:
            continue
        return base.replace(
            year=d.year, month=d.month, day=d.day,
            hour=hrs.open_time.hour, minute=hrs.open_time.minute, second=0, microsecond=0,
        )
    
    return None

def compute_print_at(dt_local: Optional[datetime] = None) -> datetime:
    # Decides if an order should print now or later based on rules

    dt_local = dt_local or local_now()
    if is_open_at(dt_local):
        return timezone.now()
    
    nxt = next_open_datetime(dt_local)
    if not nxt:
        #Fallback print next day at the same time for now
        return timezone.now() + timedelta(days=1)
    
    return nxt.astimezone(timezone.utc)
