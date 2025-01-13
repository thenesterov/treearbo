from treearbo import Span, Tree
from treearbo.exceptions import StringToTreeError


def tree_to_string(tree: Tree) -> str:
    output: list[str] = []

    def dump(tree_: Tree, prefix: str = ""):
        if len(tree_.type_):
            if not len(prefix):
                prefix = "\t"

            output.append(tree_.type_)

            if len(tree_.kids) == 1:
                output.append(" ")
                dump(tree_.kids[0], prefix)
                return

            output.append("\n")
        elif len(tree_.value) or len(prefix):
            output.append("\\" + tree_.value + "\n")

        for kid in tree_.kids:
            output.append(prefix)
            dump(kid, prefix + "\t")

    dump(tree)

    return "".join(output)


def string_to_tree(string: str, uri: str = "?") -> Tree:
    span = Span.entire(uri, string)

    root = Tree.wrap([], span)
    stack = [root]

    pos, row, min_indent = 0, 0, 0

    while len(string) > pos:
        indent = 0
        line_start = pos

        row += 1

        while len(string) > pos and string[pos] == "\t":
            indent += 1
            pos += 1

        if not len(root.kids):
            min_indent = indent

        indent -= min_indent

        if indent < 0 or indent >= len(stack):
            sp = span.span(row, 1, pos - line_start)

            while len(string) > pos and string[pos] != "\n":
                pos += 1

            if indent < 0:
                if len(string) > pos:
                    raise StringToTreeError(
                        f"Too few tabs {string[line_start:pos]} {sp}",
                    )
            else:
                raise StringToTreeError(f"Too many tabs {string[line_start:pos]} {sp}")

        stack = stack[: indent + 1]
        parent = stack[indent]

        parent_kids: list[Tree] = []

        while len(string) > pos and string[pos] != "\\" and string[pos] != "\n":
            error_start = pos

            while len(string) > pos and (string[pos] == " " or string[pos] == "\t"):
                pos += 1

            if pos > error_start:
                line_end = string.index("\n", pos)

                if line_end == -1:
                    line_end = len(string)

                sp = span.span(row, error_start - line_start + 1, pos - error_start)

                raise StringToTreeError(
                    f"Wrong nodes separator {string[line_start:line_end]} {sp}",
                )

            type_start = pos

            while (
                len(string) > pos
                and string[pos] != "\\"
                and string[pos] != " "
                and string[pos] != "\t"
                and string[pos] != "\n"
            ):
                pos += 1

            if pos > type_start:
                next_ = Tree(
                    string[type_start:pos],
                    "",
                    [],
                    span.span(row, type_start - line_start + 1, pos - type_start),
                )

                parent_kids = parent.kids

                parent_kids.append(next_)
                parent = next_

            if len(string) > pos and string[pos] == " ":
                pos += 1

        if len(string) > pos and string[pos] == "\\":
            data_start = pos

            while len(string) > pos and string[pos] != "\n":
                pos += 1

            next_ = Tree(
                "",
                string[data_start + 1 : pos],
                [],
                span.span(row, data_start - line_start + 2, pos - data_start - 1),
            )

            parent_kids = parent.kids

            parent_kids.append(next_)
            parent = next_

        if len(string) == pos and len(stack) > 0:
            sp = span.span(row, pos - line_start + 1, 1)

            raise StringToTreeError(
                f"Unexpected EOF, LF required {string[line_start : len(string)]} {sp}",
            )

        stack.append(parent)
        pos += 1

    return root
