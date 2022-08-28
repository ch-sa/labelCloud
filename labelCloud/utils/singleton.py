from abc import ABCMeta
from typing import Dict, Type


class SingletonABCMeta(ABCMeta):
    _instances: Dict[Type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonABCMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
