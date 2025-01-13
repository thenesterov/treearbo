import unittest

from treearbo import Span, Tree
from treearbo.converters import string_to_tree, tree_to_string


class TestSpan(unittest.TestCase):
    def test_span_for_same_uri(self):
        span = Span("test.py", "", 1, 3, 4)
        child = span.span(4, 5, 8)

        self.assertEqual(child.uri, "test.py")
        self.assertEqual(child.row, 4)
        self.assertEqual(child.col, 5)
        self.assertEqual(child.length, 8)

    def test_after_of_given_position(self):
        span = Span("test.py", "", 1, 3, 4)
        child = span.after(11)

        self.assertEqual(child.uri, "test.py")
        self.assertEqual(child.row, 1)
        self.assertEqual(child.col, 7)
        self.assertEqual(child.length, 11)

    def test_slice_span_regular(self):
        span = Span("test.py", "", 1, 3, 5)
        child_1 = span.slice(1, 4)

        self.assertEqual(child_1.row, 1)
        self.assertEqual(child_1.col, 4)
        self.assertEqual(child_1.length, 3)

        child_2 = span.slice(2, 2)

        self.assertEqual(child_2.col, 5)
        self.assertEqual(child_2.length, 0)

    def test_slice_span_negative(self):
        span = Span("test.py", "", 1, 3, 5)
        child = span.slice(-3, -1)

        self.assertEqual(child.row, 1)
        self.assertEqual(child.col, 5)
        self.assertEqual(child.length, 2)

    def test_slice_out_of_range(self):
        span = Span("test.py", "", 1, 3, 5)

        self.assertRaises(Exception, span.slice, -1, 3)
        self.assertRaises(Exception, span.slice, 1, 6)
        self.assertRaises(Exception, span.slice, 1, 10)


class TestTree(unittest.TestCase):
    def _test_inserting(self):
        self.assertEqual(
            tree_to_string(
                string_to_tree("a b c d\n").insert(Tree.struct("x"), "a", "b", "c"),
            ),
            "a b x\n",
        )

        self.assertEqual(
            tree_to_string(
                string_to_tree("a b\n").insert(Tree.struct("x"), "a", "b", "c", "d"),
            ),
            "a b c x\n",
        )

        self.assertEqual(
            tree_to_string(
                string_to_tree("a b c d\n").insert(Tree.struct("x"), 0, 0, 0),
            ),
            "a b x\n",
        )

        self.assertEqual(
            tree_to_string(
                string_to_tree("a b c d\n").insert(Tree.struct("x"), None, None, None),
            ),
            "a b x\n",
        )

        self.assertEqual(
            tree_to_string(
                string_to_tree("a b\n").insert(Tree.struct("x"), 0, 0, 0, 0),
            ),
            "a b \\\n\tx\n",
        )

        self.assertEqual(
            tree_to_string(
                string_to_tree("a b\n").insert(Tree.struct("x"), None, None, None, None),
            ),
            "a b \\\n\tx\n",
        )

    def test_deleting(self):
        self.assertEqual(
            tree_to_string(string_to_tree("a b c d\n").insert(None, "a", "b", "c")),
            "a b\n",
        )

        self.assertEqual(
            tree_to_string(string_to_tree("a b c d\n").insert(None, 0, 0, 0)),
            "a b\n",
        )

    def test_hacking(self):
        config = string_to_tree("password @password\n")

        self.assertEqual(
            tree_to_string(
                config.wrap(
                    config.hack(
                        {
                            "@password": lambda i, b, c: [i.data("qwerty")],
                        },
                    ),
                ),
            ),
            "password \\qwerty\n",
        )

        sample = string_to_tree("spam egg xxx xxx\n")

        self.assertEqual(
            tree_to_string(
                sample.wrap(
                    sample.hack(
                        {
                            "xxx": lambda i, b, c: [i.struct("777", i.hack(b))],
                        },
                    ),
                ),
            ),
            "spam egg 777 777\n",
        )

        caster = string_to_tree("all numbers is string: 35 171\n")

        self.assertEqual(
            tree_to_string(
                caster.wrap(
                    caster.hack(
                        {
                            "": lambda i, b, c: [i.data(i.type_, i.hack(b))]
                            if i.type_.isdigit()
                            else [i.clone(i.hack(b))],
                        },
                    ),
                ),
            ),
            "all numbers is string: \\35\n\t\\171\n",
        )


if __name__ == "__main__":
    unittest.main()
