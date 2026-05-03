{
  pkgs,
  core-cli-py,
  ...
}:
pkgs.runCommand "core-task-rotation-test"
  {
    nativeBuildInputs = [
      pkgs.python3
      pkgs.coreutils
    ];
  }
  ''
        export PROJECT_DIR=$TMPDIR/project
        mkdir -p $PROJECT_DIR
        cd $PROJECT_DIR

        # Need .project_goal to identify project root
        echo "Goal" > .project_goal

        # Create a task board with many completed tasks
        cat <<EOF > TASKS.md
    ## Strategic Vision
    Goal

    ## Active Tasks
    - [ ] Active 1

    ## Backlog
    - [ ] Backlog 1

    ## Completed Tasks
    EOF

        for i in {1..20}; do
          echo "- [x] Done $i" >> TASKS.md
        done

        # Run rotation via CLI with limit 5
        export PYTHONPATH=$PYTHONPATH:${dirOf core-cli-py}
        python3 ${core-cli-py} rotate tasks --limit 5

        # Verifications
        echo "Verifying task rotation..."
        
        if [ ! -f TASKS.archive.md ]; then
          echo "Error: Archive file not created"
          exit 1
        fi

        DONE_LINES=$(grep "- \[x\]" TASKS.md | wc -l)
        if [ "$DONE_LINES" -ne 5 ]; then
          echo "Error: TASKS.md should have 5 completed tasks, but has $DONE_LINES"
          exit 1
        fi

        ARCHIVE_LINES=$(grep "- \[x\]" TASKS.archive.md | wc -l)
        if [ "$ARCHIVE_LINES" -ne 15 ]; then
          echo "Error: Archive should have 15 completed tasks, but has $ARCHIVE_LINES"
          exit 1
        fi

        echo "Task rotation checks passed!"
        touch $out
  ''
