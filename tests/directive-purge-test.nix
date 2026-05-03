{
  pkgs,
  core-cli-py,
  ...
}:
pkgs.runCommand "core-directive-purge-test"
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

        mkdir -p .system/directives
        
        # 1. Active directive (no date)
        echo "Active directive content" > .system/directives/001_active.txt
        
        # 2. Expired directive (filename date in the past)
        echo "Expired filename directive content" > .system/directives/002_2020-01-01_expired.md
        
        # 3. Future directive (filename date in the future)
        echo "Future filename directive content" > .system/directives/003_2099-01-01_future.md
        
        # 4. Expired directive (content expiration in the past)
        cat <<EOF > .system/directives/004_expired_content.md
    # Directive 004
    Expiration: 2020-01-01
    Expired content directive content
    EOF

        # 5. Future directive (content expiration in the future)
        cat <<EOF > .system/directives/005_future_content.md
    # Directive 005
    Expiration: 2099-01-01
    Future content directive content
    EOF

        # Run purge via CLI
        export PYTHONPATH=$PYTHONPATH:${dirOf core-cli-py}
        python3 ${core-cli-py} purge

        # Verifications
        echo "Verifying purged directives..."
        
        if [ ! -f .system/directives/001_active.txt ]; then
          echo "Error: Active directive was purged"
          exit 1
        fi

        if [ -f .system/directives/002_2020-01-01_expired.md ]; then
          echo "Error: Expired filename directive was NOT purged"
          exit 1
        fi

        if [ ! -f .system/directives/archive/002_2020-01-01_expired.md ]; then
          echo "Error: Expired filename directive was not found in archive"
          exit 1
        fi

        if [ ! -f .system/directives/003_2099-01-01_future.md ]; then
          echo "Error: Future filename directive was purged"
          exit 1
        fi

        if [ -f .system/directives/004_expired_content.md ]; then
          echo "Error: Expired content directive was NOT purged"
          exit 1
        fi

        if [ ! -f .system/directives/archive/004_expired_content.md ]; then
          echo "Error: Expired content directive was not found in archive"
          exit 1
        fi

        if [ ! -f .system/directives/005_future_content.md ]; then
          echo "Error: Future content directive was purged"
          exit 1
        fi

        echo "All directive purge checks passed!"
        touch $out
  ''
