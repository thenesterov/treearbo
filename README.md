![](./docs/banner.png)
<div align="center">
    <h1>treearbo</h1>
    <p>is a python implementation of a parser for the tree format</p>
</div>

This is the WIP (work in progress) to provide python support for the [tree format](https://github.com/hyoo-ru/mam_mol/tree/master/tree2) of the [$mol frontend framework](https://github.com/hyoo-ru). Use it like this:

```python
from treearbo import string_to_tree, tree_to_string

tree_string = r"""user
	name \Jin
	age 35
	hobby
		\kendo
		\dance
		\role play
"""

tree = string_to_tree(tree_string)

assert tree_string == tree_to_string(tree)
```
