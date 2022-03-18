import os
from multiprocessing import Queue
from typing import TypeAlias

DS: TypeAlias = list[dict[str, str]]
Q_T: TypeAlias = "Queue[tuple[DS, DS]]"

os.environ.setdefault("ESCDELAY", "10")
