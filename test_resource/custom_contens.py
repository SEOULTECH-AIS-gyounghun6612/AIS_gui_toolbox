from datetime import datetime, timedelta, date

from GUI_ex._widget import Param, sector, contents


class Month(contents.custom):
    def __init__(self, center_Date: datetime = None, is_relative: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.center_Date = datetime.now() if center_Date is None else center_Date

        self.is_relative = is_relative
        self.display_max_week = 6
        self.display_max_day_slot = 5
        self.display_future_week = 6

        self.draw_layout()
        self.refresh()

    def get_layout(self):
        _h = self.display_max_week * self.display_max_day_slot + 1  # day label line(1 line) + 6 weak (each 5 line)
        _w = 21  # 7 day (each 3 line)

        _layout = sector.layer.grid([_h, _w])

        # set day label
        for _ct, _day_label in enumerate(["Sun", "Mon", "The", "Wed", "Thu", "Fri", "Sat"]):
            _label = contents.label(_day_label)
            _label.setAlignment(Param.align.CENTER.value)
            _layout.set_contents(_label, [0, _ct * 3, 0, 3])

        return _layout

    def refresh(self):
        if self.is_relative:
            _start_day = date(self.center_Date.year, self.center_Date.month, self.center_Date.day)
        else:
            _start_day = date(self.center_Date.year, self.center_Date.month, 1)

        _start_day -= timedelta(days=_start_day.isocalendar()[-1])

        for _week_ct in range(self.display_max_week):
            _line_num = _week_ct * 5 + 1

            for _day_ct in range(7):
                _day = _start_day + timedelta(days=_week_ct * 7 + _day_ct)

                self.layout().set_contents(contents.label(), [_line_num, _day_ct * 3, self.display_max_day_slot, 3])

                # _date_label = contents.label(f"{_day.day}") if _day_ct else ...
                _date_label = contents.label(f"{_day.day}")
                self.layout().set_contents(_date_label, [_line_num, _day_ct * 3])
