{
  pkgs,
  home-manager,
  jbot-module,
  ...
}:
let
  mockGemini = pkgs.writeShellScriptBin "gemini" ''
    # Find the prompt argument
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -p)
          # Store the prompt for verification
          # The agent name is now part of the prompt
          AGENT_NAME=$(echo "$2" | grep -oP 'You are \K[^,]*')
          echo "$2" > ".test_prompt_$AGENT_NAME"
          shift 2
          ;;
        *)
          shift
          ;;
      esac
    done
    # Simulate agent writing to its specific memory queue
    # The agent name should be known by the environment variable
    # In the real loop, we set MEMORY_OUTPUT
    echo '{"scope": "local", "status": "success", "summary": "Mock agent ran", "next_step": "Verification"}' > "$MEMORY_OUTPUT"
  '';
in
pkgs.testers.nixosTest {
  name = "jbot-test";
  nodes.machine = _: {
    imports = [ home-manager.nixosModules.home-manager ];

    users.users.testuser = {
      isNormalUser = true;
      home = "/home/testuser";
    };

    home-manager = {
      useGlobalPkgs = true;
      useUserPackages = true;
      users.testuser =
        { ... }:
        {
          imports = [ jbot-module ];
          programs.jbot = {
            enable = true;
            agents = {
              ceo = {
                enable = true;
                role = "CEO";
                description = "Oversee project goals and coordinate other agents.";
                projectDir = "/home/testuser/project";
                interval = "*-*-* *:*:*";
                geminiPackage = mockGemini;
              };
              dev = {
                enable = true;
                role = "Lead Developer";
                description = "Implement core features.";
                projectDir = "/home/testuser/project";
                interval = "*-*-* *:*:*";
                geminiPackage = mockGemini;
                dependsOn = [ "ceo" ];
              };
              qa = {
                enable = true;
                role = "QA Engineer";
                description = "Test everything and report bugs.";
                projectDir = "/home/testuser/project";
                interval = "*-*-* *:*:*";
                geminiPackage = mockGemini;
                dependsOn = [ "dev" ];
              };
            };
          };
          home.stateVersion = "23.11";
        };
    };
  };

  testScript = ''
    machine.wait_for_unit("home-manager-testuser.service")
    machine.wait_until_succeeds("systemctl --user -M testuser status jbot-agent-ceo.timer")
    machine.wait_until_succeeds("systemctl --user -M testuser status jbot-agent-dev.timer")
    machine.wait_until_succeeds("systemctl --user -M testuser status jbot-agent-qa.timer")

    # Check if the service file contains the expected sandboxing
    machine.succeed("systemctl --user -M testuser cat jbot-agent-dev.service | grep ProtectSystem=strict")
    machine.succeed("systemctl --user -M testuser cat jbot-agent-dev.service | grep PrivateTmp=true")
    machine.succeed("systemctl --user -M testuser cat jbot-agent-dev.service | grep PrivateDevices=true")
    machine.succeed("systemctl --user -M testuser cat jbot-maintenance.service | grep ProtectSystem=strict")
    machine.succeed("systemctl --user -M testuser cat jbot-knowledge-base.service | grep ProtectSystem=strict")

    # Initial setup
    machine.succeed("mkdir -p /home/testuser/project")
    machine.succeed("echo 'Test Goal' > /home/testuser/project/.project_goal")
    machine.succeed("cp ${../jbot_prompt.txt} /home/testuser/project/jbot_prompt.txt")
    machine.succeed("echo '# Task Board' > /home/testuser/project/TASKS.md")
    machine.succeed("chown -R testuser:users /home/testuser/project")

    # Start the CEO agent
    machine.succeed("systemctl --user -M testuser start jbot-agent-ceo.service")
    machine.wait_until_succeeds("test -f /home/testuser/project/.test_prompt_ceo")
    machine.succeed("grep 'You are ceo, acting as CEO' /home/testuser/project/.test_prompt_ceo")

    # Start the Dev agent
    machine.succeed("systemctl --user -M testuser start jbot-agent-dev.service")
    machine.wait_until_succeeds("test -f /home/testuser/project/.test_prompt_dev")

    # Verify Dev agent prompt contains its name and role
    machine.succeed("grep 'You are dev, acting as Lead Developer' /home/testuser/project/.test_prompt_dev")
    machine.succeed("grep '# Task Board' /home/testuser/project/.test_prompt_dev")

    # Wait for Dev to finish. It should NOT create memory.log directly ()
    machine.wait_until_succeeds("! systemctl --user -M testuser is-active jbot-agent-dev.service")
    machine.fail("test -f /home/testuser/project/.jbot/memory.log")
    machine.succeed("test -f /home/testuser/project/.jbot/queues/dev.json")

    # Now run maintenance to consolidate memory
    machine.succeed("systemctl --user -M testuser start jbot-maintenance.service")
    machine.wait_until_succeeds("! systemctl --user -M testuser is-active jbot-maintenance.service")

    # Verify memory consolidation happened
    machine.succeed("test -f /home/testuser/project/.jbot/memory.log")
    machine.succeed("grep '\"agent\": \"dev\"' /home/testuser/project/.jbot/memory.log")
    machine.fail("test -f /home/testuser/project/.jbot/queues/dev.json")

    # Start the QA agent
    machine.succeed("systemctl --user -M testuser start jbot-agent-qa.service")
    machine.wait_until_succeeds("test -f /home/testuser/project/.test_prompt_qa")

    # Verify QA agent prompt contains dev memory in Shared History
    machine.succeed("grep '\[dev\] Mock agent ran' /home/testuser/project/.test_prompt_qa")

    # Verify jbot CLI
    machine.wait_until_succeeds("sudo -u testuser jbot status -d /home/testuser/project | grep 'JBot Organization Status'")
    machine.wait_until_succeeds("sudo -u testuser jbot tasks -d /home/testuser/project | grep 'JBot Task Board'")
    machine.wait_until_succeeds("sudo -u testuser jbot messages -d /home/testuser/project")
  '';
}
