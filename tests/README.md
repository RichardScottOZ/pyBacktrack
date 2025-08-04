# PyBacktrack Testing

The tests can be run with:

```
  pytest
```

...provided `pytest` has been installed.

This will test the *installed* `pybacktrack` package (ie, the package installed with `pip`), not the package in the `pybacktrack/` sub-directory of the root source directory.

> __Note:__ `pytest` can be installed with `pip install pytest`. And developers can install `pytest` as an optional development dependency (`dev`) with `pip install -e .[dev]` (from the root source code directory).

You can also run `pytest` in the root source directory (parent of this directory).

> __Note:__ Running `pytest` in the root source directory (unlike running `python -m pytest`) will **only** test the *installed* package (not the package in the `pybacktrack/` sub-directory of the root source directory).
This is because our tests are *standalone* test modules (see [here](https://docs.pytest.org/en/stable/explanation/pythonpath.html#standalone-test-modules-conftest-py-files)). That means this `tests/` sub-directory will get added to `sys.path` (when testing) instead of the root source directory. And so the local `pybacktrack/` package (sub-directory of root source directory) will not get found when testing - resulting in only the *installed* `pybacktrack` getting found.
