from __future__ import annotations
from typing import (
    Type, TypeVar, Generic
)

from dataclasses import dataclass
from python_ex.system import Path, File, String


@dataclass
class Numbered_Data():
    id_num: int

    def Convert_from_string(self, **kwarg: str) -> int:
        try:
            for _key in ["id_num"]:
                _data = String.Convert_from_str(kwarg[_key])
                assert isinstance(_data, type(self.__dict__[_key]))
                self.__dict__[_key] = _data
            return 0
        except AssertionError:
            return 1

    def Convert_to_string(
        self,
        additional: dict[str, str] | None = None,
        slot_length: dict[str, int] | None = None
    ) -> dict[str, str]:
        _data: dict[str, str] = {}

        if slot_length is None or "id_num" not in slot_length:
            _key = "id_num"
            _value = str(self.id_num)
        else:
            _key, _value = String.Str_adjust_with_key(
                "id_num",
                str(self.id_num),
                slot_length["id_num"]
            )
        _data.update({_key: _value})

        if additional is not None:
            _data.update(additional)

        return _data

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            _t_dict = self.__dict__
            _o_dict = other.__dict__
            if len(_t_dict) != len(_o_dict):
                # option for "other come from child class"
                # when is okay, change to "pass" or "..."
                return False

            _t_hash = sum([
                hash(_v) for _k, _v in _t_dict.items() if _k != "id_num"
            ])
            _o_hash = sum([
                hash(_v) for _k, _v in _o_dict.items() if _k != "id_num"
            ])

            return _t_hash == _o_hash
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


@dataclass
class Numbered_String_Data():
    _id_num: str

    def Convert_to_string(
        self,
        additional: dict[str, str] | None = None,
        slot_length: dict[str, int] | None = None
    ) -> dict[str, str]:
        _data: dict[str, str] = {}

        if slot_length is None or "_id_num" not in slot_length:
            _key = "_id_num"
            _value = self._id_num
        else:
            _key, _value = String.Str_adjust_with_key(
                "_id_num",
                self._id_num,
                slot_length["_id_num"]
            )
        _data.update({_key: _value})

        if additional is not None:
            _data.update(additional)

        return _data

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            _t_dict = self.__dict__
            _o_dict = other.__dict__
            if len(_t_dict) != len(_o_dict):
                # option for "other come from child class"
                # when is okay, change to "pass" or "..."
                return False

            _t_hash = sum([
                hash(_v) for _k, _v in _t_dict.items() if _k != "_id_num"
            ])
            _o_hash = sum([
                hash(_v) for _k, _v in _o_dict.items() if _k != "_id_num"
            ])

            return _t_hash == _o_hash
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def id_num(self):
        return int(self._id_num)

    @id_num.setter
    def id_num(self, id_num: int):
        self._id_num = str(id_num)


NUMED_DATA = TypeVar(
    "NUMED_DATA",
    bound=Numbered_Data
)

NUMED_STRING_DATA = TypeVar(
    "NUMED_STRING_DATA",
    bound=Numbered_String_Data
)


class Block_Of_Numbered_Data(Generic[NUMED_DATA]):
    def __init__(
        self,
        data_type: Type[NUMED_DATA],
        file_name: str = "data",
        file_dir: str = Path.WORK_SPACE
    ) -> None:
        pass


class Block_Of_Numbered_String_Data(Generic[NUMED_STRING_DATA]):
    def __init__(
        self,
        data_type: Type[NUMED_STRING_DATA],
        file_name: str = "data",
        file_dir: str = Path.WORK_SPACE,
    ) -> None:
        _file_path = Path.Join(file_name, file_dir)

        self.data_type = data_type

        self.data_dict: dict[int, data_type] = {}
        self.last_id = 0

        if Path.Exist_check(_file_path):
            self.Read_from_csv(file_name, file_dir)

        self.last_id = max(self.data_dict) if len(self.data_dict) else -1

    def Read_from_csv(
        self,
        file_name: str,
        file_dir: str
    ):
        _data_type = self.data_type
        _data_holder = self.data_dict

        for _data in File.CSV.Read_from_file(file_name, file_dir):
            _comp: NUMED_STRING_DATA = _data_type(**_data)
            _data_holder[int(_data["id_num"])] = _comp

    def Write_to_csv(
        self,
        file_name: str,
        file_dir: str,
        data_socket_size: dict[str, int] | None = None
    ):
        _data_dict = self.data_dict

        if not _data_dict:
            return False

        return File.CSV.Write_to_file(
            file_name,
            file_dir,
            [
                _data.Convert_to_string(
                    slot_length=data_socket_size
                ) for _data in _data_dict.values()
            ],
            list(self.data_type.__annotations__.__dict__)
        )

    def Update_data(
        self,
        new_data: NUMED_STRING_DATA,
        is_override: bool = False
    ) -> bool:
        if isinstance(new_data, self.data_type):
            _data_id = new_data.id_num
            if is_override:
                self.data_dict[int(_data_id)] = new_data
                return True
            elif new_data not in self.data_dict.values():  # add
                _this_id = self.last_id + 1
                new_data.id_num = _this_id
                self.data_dict[_this_id] = new_data
                self.last_id += 1
                return True
            else:
                raise ValueError(
                    f"This is already in {self.__class__.__name__} block")
        return False

    def Get_data_from(self, id_num: int, is_pop: bool = False):
        if id_num in self.data_dict:
            if is_pop:
                return True, self.data_dict.pop(id_num)
            return True, self.data_dict[id_num]
        return False, None

    def Clear_data(self):
        self.data_dict = {}
        self.last_id = 0
