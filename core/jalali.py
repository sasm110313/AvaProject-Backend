"""تبدیل و ابزارهای تاریخ شمسی (جلالی).

پیاده‌سازی بر پایه‌ی الگوریتم استاندارد jdf (مبتنی بر تعداد روز سپری‌شده
از سال ۱۹۰۰ میلادی) که برای بازه‌ی ۱۱۷۸ تا ۱۶۳۳ شمسی دقیق است.

تمام توابع خالص (pure) هستند و به تنظیمات جنگو وابسته نیستند.
"""

import re
import uuid
from datetime import date

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

_G_DAYS_IN_MONTH = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

_JALALI_MONTH_LENGTHS = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]

_JALALI_DATE_RE = re.compile(r"^\s*(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\s*$")

MIN_JALALI_YEAR = 1178
MAX_JALALI_YEAR = 1633


class JalaliError(ValueError):
    """تاریخ شمسی نامعتبر است."""


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ میلادی به شمسی و بازگرداندن (سال، ماه، روز)."""
    if not 1 <= gm <= 12:
        raise JalaliError("ماه میلادی باید بین ۱ تا ۱۲ باشد")
    if not 1 <= gd <= 31:
        raise JalaliError("روز میلادی باید بین ۱ تا ۳۱ باشد")

    g_d_m = _G_DAYS_IN_MONTH
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        + gd
        + g_d_m[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ شمسی به میلادی و بازگرداندن (سال، ماه، روز)."""
    _validate_jalali_parts(jy, jm, jd)

    g_d_m = _G_DAYS_IN_MONTH
    jy += 1595
    days = -355668 + (365 * jy) + (((jy // 33) * 8) + (((jy % 33) + 3) // 4)) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    gm = 0
    while gm < 13 and gd > g_d_m[gm]:
        gd -= g_d_m[gm]
        gm += 1
    return gy, gm, gd


def _validate_jalali_parts(jy: int, jm: int, jd: int) -> None:
    if not MIN_JALALI_YEAR <= jy <= MAX_JALALI_YEAR:
        raise JalaliError(f"سال شمسی باید بین {MIN_JALALI_YEAR} تا {MAX_JALALI_YEAR} باشد")
    if not 1 <= jm <= 12:
        raise JalaliError("ماه شمسی باید بین ۱ تا ۱۲ باشد")
    max_day = _JALALI_MONTH_LENGTHS[jm - 1]
    if jm == 12 and _is_jalali_leap(jy):
        max_day = 30
    if not 1 <= jd <= max_day:
        raise JalaliError(f"روز شمسی باید بین ۱ تا {max_day} باشد")


def _is_jalali_leap(jy: int) -> bool:
    """سال کبیسه شمسی بر اساس الگوریتم ۳۳ ساله."""
    remainder = (jy % 33) % 4
    return remainder == 1


def is_valid_jalali_date(jy: int, jm: int, jd: int) -> bool:
    try:
        _validate_jalali_parts(jy, jm, jd)
    except JalaliError:
        return False
    return True


def format_jalali(jy: int, jm: int, jd: int) -> str:
    """قالب‌بندی تاریخ شمسی به شکل `۱۴۰۴/۰۵/۲۰` (با ارقام لاتین)."""
    return f"{jy:04d}/{jm:02d}/{jd:02d}"


def parse_jalali_date(value: str) -> date:
    """تبدیل رشته‌ی تاریخ شمسی (۱۴۰۴/۰۵/۲۰) به `datetime.date` میلادی.

    رشته‌های میلادی (۲۰۲۵-۰۸-۱۱) هم پذیرفته می‌شوند.
    """
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise JalaliError("تاریخ باید رشته باشد")

    match = _JALALI_DATE_RE.match(value)
    if not match:
        # تلاش برای پذیرش تاریخ میلادی
        try:
            return date.fromisoformat(value.strip())
        except ValueError as exc:
            raise JalaliError("قالب تاریخ نامعتبر است. نمونه درست: ۱۴۰۴/۰۵/۲۰") from exc

    jy, jm, jd = (int(part) for part in match.groups())
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    return date(gy, gm, gd)


def to_jalali_string(value: date) -> str:
    """تبدیل `datetime.date` به رشته‌ی شمسی."""
    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    return format_jalali(jy, jm, jd)


def today_jalali() -> str:
    """تاریخ امروز به همراه منطقه‌ی زمانی تنظیمات، به شکل شمسی."""
    from django.utils import timezone

    return to_jalali_string(timezone.localdate())


def jalali_month_name(index: int) -> str:
    """نام فارسی ماه شمسی؛ در صورت نامعتبر بودن رشته‌ی خالی برمی‌گرداند."""
    return JALALI_MONTHS[index - 1] if 1 <= index <= 12 else ""


def random_name(prefix: str, original: str) -> str:
    """ساخت نام یکتا و امن برای فایل آپلودی."""
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else "bin"
    ext = "".join(ch for ch in ext if ch.isalnum())[:10] or "bin"
    return f"{prefix}/{uuid.uuid4().hex}.{ext}"