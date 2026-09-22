# Approved batch task

{
  "id": "L05",
  "card": "Run the approved combined acceptance commands and write short USAGE.md covering design-only, explicit mock, status, verify and callable API; explain exit statuses, old/corrupt/unfinished records, local evidence, restricted geometry, mock-only game status and lack of mock-world persistence. Add missing acceptance cases only if needed in tests/test_cli.py, preserving existing assertions. Update STATE.md with actual results and blockers. Do not add or change application features; if a code defect needs files outside this task's write scope, report the blocker and stop.",
  "pointers": [
    "bridge_cli.py",
    "bridge_app.py",
    "tests/test_cli.py",
    "STATE.md"
  ],
  "write_files": [
    "USAGE.md",
    "tests/test_cli.py",
    "STATE.md"
  ],
  "acceptance": [
    [
      "python",
      "tools/quiet_checks.py",
      "--suite",
      "application",
      "--label",
      "batch_l05"
    ],
    [
      "python",
      "tools/quiet_checks.py",
      "--suite",
      "corridor",
      "--label",
      "batch_l05_corridor"
    ],
    [
      "python",
      "tools/task_runner.py",
      "--acceptance",
      "L05"
    ]
  ]
}
