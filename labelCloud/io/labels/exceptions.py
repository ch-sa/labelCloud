class ZeroLabelException(Exception):
    pass


class LabelIdsNotUniqueException(Exception):
    pass


class DefaultIdMismatchException(Exception):
    pass


class LabelClassNameEmpty(Exception):
    pass


class UnknownLabelFormat(Exception):
    def __init__(self, label_format: str) -> None:
        super().__init__(f"Unknown label format '{label_format}'.")
