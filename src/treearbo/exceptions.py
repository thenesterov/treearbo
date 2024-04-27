class SpanError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class TreeError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class StringToTreeError(Exception):
    def __init__(self, *args):
        super().__init__(*args)
