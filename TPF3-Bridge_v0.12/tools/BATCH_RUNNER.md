# Development batch runner

`task_runner.py` is retained as reusable development code, with fake-worker tests.
There is no active project queue or supported ready-to-run historical batch. Old
queue files, completed task cards and worker journals have been removed. Do not
recreate or launch earlier milestone batches. The current workflow uses scoped
assignments in the existing implementation chat.

A future explicitly authorised batch needs its own current task definitions and
reviewed scope. Its diagnostics and reconciliation state are temporary; remove them
when finished. No history retention or automatic restart is implied.
