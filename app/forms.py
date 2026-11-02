"""自定义表单校验（非 WTForms，纯校验逻辑）。"""

from datetime import date, time


def parse_date(value):
    """'YYYY-MM-DD' -> datetime.date，非法返回 None。"""
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, AttributeError, TypeError):
        return None


def parse_time(value):
    """'HH:MM' -> datetime.time，非法返回 None。"""
    try:
        parts = str(value).strip().split(":")
        if len(parts) != 2:
            return None
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, AttributeError, TypeError):
        return None


class ReservationForm:
    """预约表单：负责类型与格式层面的基础校验。"""

    def __init__(self, room_id=None, date_str=None, start_str=None,
                 end_str=None, purpose="", attendees=None):
        self.room_id = int(room_id) if str(room_id).strip().isdigit() else None
        self.date = parse_date(date_str)
        self.start_time = parse_time(start_str)
        self.end_time = parse_time(end_str)
        self.purpose = (purpose or "").strip()
        self.attendees = attendees
        self.errors = []

    def validate_basic(self):
        """基础校验：房间/日期/时间格式、时间先后、人数为正整数。"""
        if self.room_id is None:
            self.errors.append("请选择房间")
        if self.date is None:
            self.errors.append("日期格式不正确")
        if self.start_time is None or self.end_time is None:
            self.errors.append("时间格式不正确")
        elif self.start_time >= self.end_time:
            self.errors.append("开始时间必须早于结束时间")

        raw = self.attendees
        if raw is None or str(raw).strip() == "":
            self.attendees = None
        else:
            try:
                self.attendees = int(raw)
                if self.attendees < 1:
                    self.errors.append("人数必须为正整数")
            except (ValueError, TypeError):
                self.errors.append("人数必须为正整数")

        return not self.errors
