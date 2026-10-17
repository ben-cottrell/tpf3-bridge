# Reusable offline geometry and test fixtures

These modules support the bridge's offline commands and regression tests. They are
working source, not stored execution history. Synthetic checks do not prove native
game construction. Profile constraints apply only to the brief selecting them.

Run tests without leaving reports, from this directory:

```sh
python -B -m unittest discover -s tests
```

The `*_fixtures` directories are reusable test inputs. The sibling `evidence/`
directory holds reference data imported by these modules. Generated demo results
are temporary and should be removed after use.
