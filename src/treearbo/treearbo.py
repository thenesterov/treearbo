import re
import typing as t

from treearbo.exceptions import SpanError, TreeError


class Span:
    def __init__(self, uri: str, source: str, row: int, col: int, length: int):
        self.uri = uri
        self.source = source
        self.row = row
        self.col = col
        self.length = length

    @staticmethod
    def begin(uri: str, source: str = "") -> "Span":
        return Span(uri, source, 1, 1, 0)

    @staticmethod
    def end(uri: str, source: str) -> "Span":
        return Span(uri, source, 1, len(source) + 1, 0)

    @staticmethod
    def entire(uri: str, source: str) -> "Span":
        return Span(uri, source, 1, 1, len(source))

    def __dict__(self):
        return {
            "uri": self.uri,
            "row": self.row,
            "col": self.col,
            "length": self.length,
        }

    def span(self, row: int, col: int, length: int) -> "Span":
        return Span(self.uri, self.source, row, col, length)

    def after(self, length: int = 0) -> "Span":
        return Span(self.uri, self.source, self.row, self.col + self.length, length)

    def slice(self, begin: int, end: int = -1) -> "Span":
        if begin < 0:
            begin += self.length

        if end < 0:
            end += self.length

        if begin < 0 or begin > self.length:
            raise SpanError(f"Begin value {begin} out of range {self}")

        if end < 0 or end > self.length:
            raise SpanError(f"End value {end} out of range {self}")

        if end < begin:
            raise SpanError(f"End value {end} can't be less than begin value, {self}")

        return self.span(self.row, self.col + begin, end - begin)

    def __repr__(self) -> str:
        return f"{self.uri}#{self.row}:{self.col}/{self.length}"

    @classmethod
    def unknown(cls) -> "Span":
        return cls.begin("?")


TreePath = t.Union[str, int, None]
Context = dict[str, t.Any]
Belt = dict[str, "Hack"]


class Hack(t.Protocol):
    def __call__(self, input_: "Tree", belt: Belt, context: Context) -> list["Tree"]: ...


class Tree:
    def __init__(self, type_: str, value: str, kids: list["Tree"], span: Span):
        self.type_ = type_
        self.value = value
        self.kids = kids
        self.span = span

    def __repr__(self):
        from treearbo.converters import tree_to_string

        return tree_to_string(self)

    @staticmethod
    def wrap(kids: list["Tree"], span: Span = Span.unknown()):
        return Tree("", "", kids, span)

    @staticmethod
    def data(value: str, kids: t.Optional[list["Tree"]] = None, span: Span = Span.unknown()):
        if not kids:
            kids = []

        chunks: list[str] = value.split("\n")

        if len(chunks) > 1:
            kid_span: Span = span.span(span.row, span.col, 0)

            data: list[Tree] = list(
                map(
                    lambda chunk: Tree("", chunk, [], kid_span.after(len(chunk))),
                    chunks,
                ),
            )

            kids = [*data, *kids]

            value = ""

        return Tree("", value, kids, span)

    @staticmethod
    def struct(
        type_: str,
        kids: t.Optional[list["Tree"]] = None,
        span: Span = Span.unknown(),
    ) -> "Tree":
        if not kids:
            kids = []

        if re.match(r"[ \n\t\\]", type_):
            raise TreeError(repr(f"Wrong type {type_}"))

        return Tree(type_, "", kids, span)

    def _struct(self, type_: str, kids: list["Tree"]) -> "Tree":
        return Tree.struct(type_, kids, self.span)

    def clone(self, kids: list["Tree"], span: t.Optional[Span] = None):
        if span is None:
            span = self.span

        return Tree(self.type_, self.value, kids, span)

    def text(self) -> str:
        values: list[str] = []

        for kid in self.kids:
            if kid.type_:
                continue

            values.append(kid.value)

        return self.value + "\n".join(values)

    def insert(self, value: t.Optional["Tree"], *path: TreePath):
        try:
            if len(path) == 0:
                return value
        except TypeError:
            return None

        type_ = path[0]

        if isinstance(type_, str):
            replaced = False

            sub: list[Tree] = []

            for item in self.kids:
                if item.type_ != type_:
                    sub.append(item)

                replaced = True

                elem = item.insert(value, *path[1:])

                if elem is not None:
                    sub.append(elem)

            sub = list(filter(bool, sub))

            if not replaced and value:
                elem = self._struct(type_, []).insert(value, *path[1:])

                if elem is not None:
                    sub.append(elem)

            return self.clone(sub)
        if isinstance(type_, int):
            sub = self.kids[:]

            sub[type_] = (sub[type_] or self.wrap([], self.span)).insert(
                value,
                *path[1:],
            )

            return self.clone(list(filter(bool, sub)))
        kids = list(
            filter(
                bool,
                map(
                    lambda kid: kid.insert(value, *path[1:]),
                    [self.wrap([])] if len(self.kids) == 0 else self.kids,
                ),
            ),
        )

        return self.clone(kids)

    def select(self, *path: TreePath):
        next_: list[Tree] = [self]

        for type_ in path:
            if not len(next_):
                break

            prev: list[Tree] = next_
            next_ = []

            for item in prev:
                if isinstance(type_, str):
                    for child in item.kids:
                        if child.type_ == type_:
                            next_.append(child)

                    break
                if isinstance(type_, int):
                    if type_ < len(item.kids):
                        next_.append(item.kids[type_])

                    break
                next_.append(*item.kids)

        return Tree.wrap(next_, self.span)

    def filter(self, path: list[str], value: t.Optional[str]):
        sub: list[Tree] = []

        for item in self.kids:
            found = item.select(*path)

            if value is None:
                if len(found.kids):
                    sub.append(item)
            elif any(map(lambda child: child.value == value, found.kids)):
                sub.append(item)

        return self.clone(sub)

    def hack_self(self, belt: Belt, context: t.Optional[Context] = None):
        if not context:
            context = {}

        handle: t.Optional[Hack] = belt.get(self.type_) or belt.get("")

        if not handle:
            handle = lambda input_, belt_, context_: [  # noqa
                input_.clone(input_.hack(belt_, context_), context_.get("span")),
            ]

        return handle(self, belt, context)

    def hack(self, belt: Belt, context: t.Optional[Context] = None):
        if not context:
            context = {}

        return [item for kid in self.kids for item in kid.hack_self(belt, context)]

    def __getitem__(self, item: t.Union[str, int]):
        return self.select(item).kids[0]
