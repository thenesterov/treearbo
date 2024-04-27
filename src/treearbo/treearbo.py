import re
from typing import Self, TypeAlias

from exceptions import SpanError, TreeError, StringToTreeError


class Span:
    def __init__(
        self,
        uri: str,
        source: str,
        row: int,
        col: int,
        length: int
    ):
        self.uri = uri
        self.source = source
        self.row = row
        self.col = col
        self.length = length

    @staticmethod
    def begin(uri: str, source: str = '') -> 'Span':
        return Span(uri, source, 1, 1, 0)

    @staticmethod
    def end(uri: str, source: str) -> 'Span':
        return Span(uri, source, 1, len(source) + 1, 0)

    @staticmethod
    def entire(uri: str, source: str) -> 'Span':
        return Span(uri, source, 1, 1, len(source))

    def to_string(self) -> str:
        return str(self)

    def to_dict(self) -> dict:
        return {
            'uri': self.uri,
            'row': self.row,
            'col': self.col,
            'length': self.length
        }

    def span(self, row: int, col: int, length: int) -> Self:
        return Span(self.uri, self.source, row, col, length)

    def after(self, length: int = 0) -> Self:
        return Span(self.uri, self.source, self.row, self.col + self.length, length)

    def slice(self, begin: int, end: int = -1) -> Self:
        if begin < 0:
            begin += self.length

        if end < 0:
            end += self.length

        if begin < 0 or begin > self.length:
            raise SpanError(f'Begin value {begin} out of range {self}')

        if end < 0 or end > self.length:
            raise SpanError(f'End value {end} out of range {self}')

        if end < begin:
            raise SpanError(f"End value {end} can't be less than begin value, {self}")

        return self.span(self.row, self.col + begin, end - begin)

    def __str__(self) -> str:
        return f'{self.uri}#{self.row}:{self.col}/{self.length}'

    @classmethod
    @property
    def unknown(cls) -> Self:
        return cls.begin('?')


TreePath: TypeAlias = str | int | None


class Tree:
    def __init__(
        self,
        type_: str,
        value: str,
        kids: list['Tree'],
        span: Span
    ):
        self.type_ = type_
        self.value = value
        self.kids = kids
        self.span = span

    def __str__(self):
        return self.type_ or '\\' + self.value

    def __repr__(self):
        return self.type_ or '\\' + self.value

    @staticmethod
    def list_(
        kids: list['Tree'],
        span: Span = Span.unknown
    ):
        return Tree('', '', kids, span)

    @staticmethod
    def data(
        value: str,
        kids: list['Tree'] = [],
        span: Span = Span.unknown
    ):
        chunks: list[str] = value.split('\n')

        if len(chunks) > 1:
            kid_span: Span = span.span(span.row, span.col, 0)

            data: list['Tree'] = list(map(
                lambda chunk: Tree('', chunk, [], kid_span.after(len(chunk))),
                chunks
            ))

            kids = [*data, *kids]

            value = ''

        return Tree('', value, kids, span)

    @staticmethod
    def struct(
        type_: str,
        kids: list['Tree'] = [],
        span: Span = Span.unknown
    ) -> 'Tree':
        if re.match(r'[ \n\t\\]', type_):
            raise TreeError(repr(f'Wrong type {type_}'))

        return Tree(type_, '', kids, span)

    def _struct(
        self,
        type_: str,
        kids: list['Tree']
    ) -> 'Tree':
        return Tree.struct(type_, kids, self.span)

    def clone(
        self,
        kids: list['Tree'],
        span: Span | None = None
    ):
        if span is None:
            span = self.span

        return Tree(self.type_, self.value, kids, span) 

    def text(self):
        values: list[str] = []

        for kid in self.kids:
            if kid.type_:
                continue

            values.append(kid.value)

        return self.value + '\n'.join(values)

    def insert(
        self,
        value: 'Tree',
        *path: TreePath
    ):
        try:
            if len(path) == 0:
                return value
        except TypeError:
            return None

        type_ = path[0]

        if isinstance(type_, str):
            replaced = False
            
            sub: list['Tree'] = []
                
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
        elif isinstance(type_, int):
            sub: list['Tree'] = self.kids[:]

            sub[type_] = (sub[type_] or self.list_([], self.span)).insert(value, *path[1:])

            return self.clone(list(filter(bool, sub)))
        else:
            kids = list(filter(bool, map(
                lambda item: item.insert(value, *path[1:]),
                [self.list_([])] if len(self.kids) == 0 else self.kids
            )))

            return self.clone(kids)

    def select(
        self,
        *path: TreePath
    ):
        next_: list['Tree'] = [self]

        for type_ in path:
            if not len(next_):
                break

            prev: list[Self] = next_
            next_ = []

            for item in prev:
                if isinstance(type_, str):
                    for child in item.kids:
                        if child.type_ == type_:
                            next_.append(child)

                    break
                elif isinstance(type_, int):
                    if type_ < len(item.kids):
                        next_.append(item.kids[type_])

                    break
                else:
                    next_.append(*item.kids)

        return Tree.list_(next_, self.span)

    def filter(
        self,
        path: list[str],
        value: str | None
    ):
        sub: list['Tree'] = []

        for item in self.kids:
            found = item.select(*path)

            if value is None:
                if len(found.kids):
                    sub.append(item)
            else:
                if any(map(lambda child: child.value == value, found.kids)):
                    sub.append(item)

        return self.clone(sub)


def tree_to_string(tree: Tree) -> str:
    output: list[str] = []

    def dump(
        tree: Tree,
        prefix: str = ''
    ):
        if len(tree.type_):
            if not len(prefix):
                prefix = '\t'

            output.append(tree.type_)

            if len(tree.kids) == 1:
                output.append(' ')
                dump(tree.kids[0], prefix)
                return

            output.append('\n')
        elif len(tree.value) or len(prefix):
            output.append('\\' + tree.value + '\n')

        for kid in tree.kids:
            output.append(prefix)
            dump(kid, prefix + '\t')

    dump(tree)

    return ''.join(output)


def string_to_tree(
    string: str,
    uri: str = '?'
) -> Tree:
    span = Span.entire(uri, string)

    root = Tree.list_([], span)
    stack = [root]

    pos, row, min_indent = 0, 0, 0

    while len(string) > pos:
        indent = 0
        line_start = pos

        row += 1

        while len(string) > pos and string[pos] == '\t':
            indent += 1
            pos += 1

        if not len(root.kids):
            min_indent = indent

        indent -= min_indent

        if indent < 0 or indent >= len(stack):
            sp = span.span(row, 1, pos - line_start)

            while len(string) > pos and string[pos] != '\n':
                pos += 1

            if indent < 0:
                if len(string) > pos:
                    raise StringToTreeError(f'Too few tabs {string[line_start:pos]} {sp}')
            else:
                raise StringToTreeError(f'Too many tabs {string[line_start:pos]} {sp}')

        stack = stack[:indent+1]
        parent = stack[indent]

        while len(string) > pos and string[pos] != '\\' and string[pos] != '\n':
            error_start = pos
            
            while len(string) > pos and (string[pos] == ' ' or string[pos] == '\t'):
                pos += 1

            if pos > error_start:
                line_end = string.index('\n', pos)
            
                if line_end == -1:
                    line_end = len(string)

                sp = span.span(row, error_start - line_start + 1, pos - error_start)

                raise StringToTreeError(f'Wrong nodes separator {string[line_start:line_end]} {sp}')

            type_start = pos

            while len(string) > pos \
                    and string[pos] != '\\' \
                    and string[pos] != ' ' \
                    and string[pos] != '\t' \
                    and string[pos] != '\n':
                pos += 1

            if pos > type_start:
                next_ = Tree(
                    string[type_start:pos],
                    '',
                    [],
                    span.span(row, type_start - line_start + 1, pos - type_start)
                )

                parent_kids: list[Tree] = parent.kids

                parent_kids.append(next_)
                parent = next_

            if len(string) > pos and string[pos] == ' ':
                pos += 1

        if len(string) > pos and string[pos] == '\\':
            data_start = pos

            while len(string) > pos and string[pos] != '\n':
                pos += 1

            next_ = Tree(
                '',
                string[data_start+1:pos],
                [],
                span.span(row, data_start - line_start + 2, pos - data_start - 1)
            )

            parent_kids: list[Tree] = parent.kids

            parent_kids.append(next_)
            parent = next_

        if len(string) == pos and len(stack) > 0:
            sp = span.span(row, pos - line_start + 1, 1)

            raise StringToTreeError(f'Unexpected EOF, LF required {string[line_start:len(string)]} {sp}')

        stack.append(parent)
        pos += 1

    return root
