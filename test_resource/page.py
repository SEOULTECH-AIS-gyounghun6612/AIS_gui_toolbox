from GUI_ex._widget import sector, contents, Param
from GUI_ex._base import GUI_base
from test_resource import custom_contens


class main_page():
    class main(GUI_base.page):
        def __init__(self, title: str):
            super().__init__(title)

        def get_layout(self):
            _layout = sector.layer.grid([12, 5])
            _layout.set_contents(main_page.schedule_display_sub_section(), [0, 0, 12, 4])
            _layout.set_contents(main_page.main_schedule_sub_section(), [0, 4, 4, 1])
            _layout.set_contents(main_page.plot_sub_section(), [4, 4, 8, 1])

            return _layout

    class schedule_display_sub_section(sector.group):
        def __init__(self, name: str = "", default_check: bool = None, is_flat: bool = True):
            super().__init__(name, default_check, is_flat)

        def get_layout(self):
            _layout = sector.layer.grid([1, 40])

            self.month = custom_contens.Month()
            # _left_btn = contents.button("<")
            # _right_btn = contents.button(">")

            _layout.set_contents(self.month, [0, 0, 1, 40])
            # _layout.set_contents(_left_btn, [0, 0])
            # _layout.set_contents(_right_btn, [0, 39])

            return _layout

    class main_schedule_sub_section(sector.group):
        def __init__(self, name: str = "Main Schedule", default_check: bool = None, is_flat: bool = True):
            super().__init__(name, default_check, is_flat)

        def get_layout(self):
            _layout = sector.layer.grid([10, 6])

            _file_edit = contents.value_edit("./")
            _btn_load = contents.button("Load")
            _componant = sector.contents_annotation(
                [1, 6],
                [[contents.label("file directory"), [0, 0]], ],
                [[_file_edit, [0, 1, 1, 4]], [_btn_load, [0, 5]]]
            )
            _layout.set_contents(_componant, [0, 0, 1, 6])

            _data_tree_display = contents.tree_module(["test", "test"])
            _layout.set_contents(_data_tree_display, [1, 0, 8, 6])

            _btn_del = contents.button("Del")
            _btn_clear = contents.button("Clear")

            _layout.set_contents(_btn_del, [9, 0, 1, 3])
            _layout.set_contents(_btn_clear, [9, 3, 1, 3])

            return _layout

    class plot_sub_section(sector.group):
        def __init__(self, name: str = "Plot", default_check: bool = None, is_flat: bool = True):
            super().__init__(name, default_check, is_flat)

        def get_layout(self):
            _layout = sector.layer.grid([8, 10])

            _layout.set_contents(contents.label("Plot setting"), [0, 0, 1, 3])
            _layout.set_contents(sector.line(Param.sector.direction.HORIZONTAL), [0, 3, 1, 7])

            _plot_type = contents.combobox(["test 1", "test 2"])
            _componant = sector.contents_annotation(
                [1, 6],
                [[contents.label("Type"), [0, 0]], ],
                [[_plot_type, [0, 1, 1, 5]], ]
            )
            _layout.set_contents(_componant, [1, 0, 1, 10])

            return _layout
