### Commit naming
This is a common commit text template::
```
type(scope): subject

Full text of commit.
```

The commit **type** can be one of:
- _feature_ - new functionality
- _fix_ - bug fix
- _docs_ - documentation changes
- _style_ - correction of formatting, typos
- _refactor_ - commit as part of the refactoring process
- _test_ - writing and working with tests
- _chore_ - general code maintenance

**Scope** - is a certain file or directory that has been edited. If it's a common commit, then pass it empty.

**Subject** - is a common name of the commit for a quick understanding of the meaning. The whole line should be in lowercase.

**Full commit text** - is optional full text of commit with description of changes. It is formatted as plain text - with capital letters, abbreviations in CAPS, and so on

If the changes have a number in the GitHub Issues, they should be passed before the commit text, for example:
```
#203 fix(src/treearbo): use `tree_to_string` in `__repr__`

Make a convenient tree display.
```
