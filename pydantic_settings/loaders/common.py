from attr import dataclass


@dataclass
class Location:
    line: int
    col: int
    end_line: int
    end_col: int
