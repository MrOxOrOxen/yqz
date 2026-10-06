from lunar_python import Lunar, LunarYear
from datetime import datetime

def is_birthday_today(birthday_str, is_moon, only_leap):
    now = datetime.now()

    if not is_moon:
        return now.strftime("%m%d") == birthday_str

    now_lunar = Lunar.fromDate(now)
    lunar_month = now_lunar.getMonth()
    lunar_day = now_lunar.getDay()
    is_today_leap = lunar_month < 0
    today_mmdd = f"{abs(lunar_month):02d}{lunar_day:02d}"
    
    target_mmdd = birthday_str.lstrip("-")
    is_leap_birthday = birthday_str.startswith("-")
    # is_today_leap = now_lunar.isLeap()

    if not is_leap_birthday:
        return (not is_today_leap) and (today_mmdd == target_mmdd)

    if is_today_leap:
        return today_mmdd == target_mmdd

    if only_leap:
        return False

    current_year_leap_month = LunarYear.fromYear(now_lunar.getYear()).getLeapMonth()
    target_month = int(target_mmdd[:2])
    has_leap_this_year = (current_year_leap_month == target_month)
    
    return (today_mmdd == target_mmdd) and (not has_leap_this_year)