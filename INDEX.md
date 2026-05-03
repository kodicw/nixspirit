# JBot Dashboard

*Last Updated: 2026-05-03 00:46:19*

## 🎯 Strategic Vision
> Phase 2 (PAO): Technical Excellence, Architectural Purity, and Practical Verification (90% min coverage).

## 👥 Team Roster
| Agent | Role | Description |
|-------|------|-------------|
| architect | System Architect | High-level design and ADR maintenance. Translates complex requirements into actionable technical plans. |
| bifrost-architect | System Architect | Expert in Nix-to-Windows declarative state mapping. |
| bifrost-lead | Managerial Lead | Orchestrator for PowerShell stability and project roadmap. |
| bifrost-tester | QA Engineer | PowerShell testing expert using Pester and idempotency validation. |
| engineer | Implementation Engineer | Core developer. Executes code changes, refactoring, and feature implementation delegated by the Lead. |
| lead | Managerial Lead | Orchestrator and task delegator. Decomposes high-level goals into sub-tasks for specialized agents using the nb task board. |
| researcher | Research Specialist | Information gathering and documentation. Monitors the ecosystem and maintains the knowledge base. |
| security | Security Auditor | Compliance and security gatekeeper. Audits all code changes and sandbox constraints. |
| tester | QA Engineer | Test automation and verification. Ensures 100% pass rate and reports regressions. |

## 💡 Proposed Tasks
- [ ] **Test proposed task** [architect]

## 🚀 Active Tasks
- [ ] **Inject ADR header links across all python scripts** [engineer]
- [ ] **Add missing Mermaid diagrams for core scripts** [engineer]
- [ ] **Formalize 'adr/', 'research/', and 'benchmarks/' structure in nb** [architect]
- [ ] **Achieve 100% test coverage across all Python modules and Nix derivations** [tester]
- [ ] **Audit codebase for 'Self-Documenting Code' compliance** [architect]

## 📦 Backlog Highlights
- [ ] **Docker-based test runner for faster verification cycles** (Agent: tester)

## ✅ Recently Completed
- [x] **Implement automated versioning and release tagging via the CLI** (Agent: lead)
- [x] **Enforce single Linux user account constraint in jbot.nix and flake.nix** (Agent: lead)
- [x] **Enhance agent-to-agent message threading in dashboard** (Agent: architect)
- [x] **Document external isolation and multi-user NixOS patterns in README.md** (Agent: architect)
- [x] **Formalize 'adr/', 'research/', and 'benchmarks/' structure in nb** (Agent: architect)

## 📜 Recent ADRs
- [[nb:63]] ADR: Multi-User Isolation Patterns
- [[nb:62]] ADR: Message Threading Model
- [[nb:61]] ADR: Security Audit Report

## 💬 Recent Messages
- **[unknown]** none ([human.txt](.jbot/messages/human.txt))
- **[architect]** Threading Test ([[nb:64]])
- **[lead]** Re: Threading Test (Re: [[nb:64]]) ([[nb:65]])

## 📊 Architectural Diagrams
### Jbot Agent
```mermaid
graph TD
    A[Start Agent] --> B[Initialize Environment]
    B --> C[Assemble Context]
    C --> D[Execute AI CLI]
    D --> E[Verify Changes]
    E --> F[End Agent]

    subgraph "Context Assembly (nb-driven)"
        C1[Get System Prompt]
        C2[Get Directives & ADRs]
        C3[Get Task Board]
        C4[Get Git Status & Tree]
        C5[Get Shared Memory Logs]
        C6[Get Messages]
        C1 --> C_ALL[Combine into Jinja2 Template]
        C2 --> C_ALL
        C3 --> C_ALL
        C4 --> C_ALL
        C5 --> C_ALL
        C6 --> C_ALL
    end

    subgraph "Verification"
        E1[Run .githooks/pre-commit]
        E2[Check Exit Code]
    end
```

### Jbot Agent Interface
```mermaid
classDiagram
    class AiInterface {
        <<abstract>>
        +binary_path: str
        +model: str
        +get_command(prompt: str)* List[str]
        +run(prompt: str, agent_name: str) int
    }
    class GeminiInterface {
        +get_command(prompt: str) List[str]
    }
    class OpenCodeInterface {
        +get_command(prompt: str) List[str]
    }
    AiInterface <|-- GeminiInterface
    AiInterface <|-- OpenCodeInterface

    class Factory {
        +get_interface(name, binary_path) AiInterface
    }
    Factory ..> AiInterface : creates
```

### Jbot Cli
```mermaid
graph TD
    CLI[jbot_cli.py] --> INIT[init: jbot_init]
    CLI --> STATUS[status: infra.get_project_summary]
    CLI --> TASK[task: jbot_tasks]
    CLI --> LOGS[logs: infra.get_recent_logs]
    CLI --> MSG[messages: infra.get_recent_messages]
    CLI --> SEND[send-message: infra.send_message]
    CLI --> MAINT[maintenance: infra.run_maintenance]
    CLI --> PURGE[purge: jbot_rotation.purge_directives]
    CLI --> ROTATE[rotate: jbot_rotation]
    CLI --> DASH[dashboard: utils.generate_dashboard]
    CLI --> AGENT[agent: jbot_agent.run_agent]
    CLI --> HUMAN[human: jbot_tui]
    CLI --> SYSTEM[system: handle_system]
    CLI --> VERSION[version: handle_version]

    subgraph "Internal Logic"
        STATUS --> core[jbot_core]
        VERSION --> core
        SYSTEM --> jbot_agent
    end
```

### Jbot Core
```mermaid
graph TD
    subgraph Logging
        LOG[log: Standardized Logging]
    end

    subgraph "Paths & Files"
        FFU[find_file_upwards]
        GPR[get_project_root]
        LJ[load_json]
        SJ[save_json]
        RF[read_file]
        WF[write_file]
    end

    subgraph "Notebook Management"
        GNN[get_notebook_name]
    end

    subgraph "Security & Isolation"
        ESU[ensure_single_user: Constraint Enforcement]
    end

    subgraph Git
        IGC[is_git_clean]
        IG[init_git]
        STD[switch_to_develop]
        CA[commit_all]
    end

    subgraph Versioning
        GV[get_version]
        BV[bump_version]
        UC[update_changelog]
    end

    subgraph Metadata
        GGS[get_git_status]
        GNM[get_nix_metadata]
    end

    GPR --> FFU
    GNN --> GPR
    GNN --> RF
    BV --> GV
    BV --> WF
    UC --> RF
    UC --> WF
```

### Jbot Infra
```mermaid
graph TD
    A[Start Maintenance] --> B[Initialize Infrastructure]
    B --> C[Consolidate Messages]
    C --> D[Consolidate Memory]
    D --> E[Perform Rotations]
    E --> F[Generate Dashboard]
    F --> G[End Maintenance]

    subgraph Initialize
        B1[Create .jbot/queues]
        B2[Create .jbot/messages]
        B3[Create .jbot/directives]
        B4[Create .jbot/outbox]
    end

    subgraph Consolidate
        C1[Move outbox/*.txt to messages/]
        D1[Parse agent queues/*.json]
        D2[Push memory to nb knowledge base]
    end

    subgraph Rotate
        E1[Archive expired directives]
        E2[Rotate old messages]
        E3[Rotate nb notes by tag]
    end
```

### Jbot Infra Updates
```mermaid
graph TD
    START[generate_infra_pr] --> CLEAN{Git Clean?}
    CLEAN -- No --> ABORT[Abort]
    CLEAN -- Yes --> UPDATE[nix flake update]
    UPDATE --> LOCK{flake.lock changed?}
    LOCK -- No --> NO_UPD[Log: No updates]
    LOCK -- Yes --> BRANCH[Create infra/update-TIMESTAMP branch]
    BRANCH --> ADD[git add flake.lock]
    ADD --> COMMIT[git commit -m ...]
    COMMIT --> NOTIFY[infra.send_message: Notify CEO/Lead]
    NOTIFY --> BACK[git checkout -]
```

### Jbot Init
```mermaid
graph TD
    INIT[init_project] --> INFRA[infra.initialize_infrastructure]
    INIT --> GIT[core.init_git]
    INIT --> BRANCH[core.switch_to_develop]
    INIT --> NB_DIR[Create .nb/]
    INIT --> NB_ADD[nb notebooks add]
    INIT --> CFG[Write .jbot/notebook]
    INIT --> GOAL[Write .project_goal]
    INIT --> AGENTS[Write .jbot/agents.json]
    INIT --> VER[Write VERSION & CHANGELOG.md]
    INIT --> IGNORE[Write .gitignore]
    INIT --> FLAKE[Write flake.nix template]
    INIT --> PROMPT[Write jbot_prompt.txt template]
    INIT --> PUSH[Push Initial Notes to nb]
    INIT --> DASH[utils.generate_dashboard]
    INIT --> COMMIT[core.commit_all]

    subgraph "Knowledge Base (nb)"
        PUSH --> GOAL_NOTE[Vision: Goal Note]
        PUSH --> TEAM_NOTE[Team Registry Note]
        PUSH --> TASK_NOTE[Initial Task Note]
    end
```

### Jbot Launcher
```mermaid
graph TD
    Start[Start Launcher] --> EnvCheck[Check Environment Variables]
    EnvCheck --> GitCheck[Ensure Develop Branch]
    GitCheck --> PrepDirs[Prepare .jbot/ Queues & Outbox]
    PrepDirs --> PrepRegistry[Copy Agent Registry]
    PrepRegistry --> FakePasswd[Create Fake /etc/passwd]
    FakePasswd --> Sandbox[Execute Bubblewrap Sandbox]
    
    subgraph "Sandbox (bwrap)"
        Sandbox --> Mounts[Mount /nix/store, /etc, /dev, /proc]
        Mounts --> Binds[Bind Project Dir & Memory]
        Binds --> Unshare[Unshare All Namespaces]
        Unshare --> Execute[Run jbot-cli agent]
    end
    
    Execute --> End[End Launcher]
```

### Jbot Memory Interface
```mermaid
classDiagram
    class MemoryNote {
        +id: str
        +title: str
        +tags: List[str]
        +content: str
        +filename: str
    }
    class MemoryInterface {
        <<abstract>>
        +add(title, content, tags, overwrite)* str
        +show(note_id)* str
        +query(query)* List[MemoryNote]
        +edit(note_id, content, title, tags, overwrite)* bool
        +ls(tags, limit)* List[MemoryNote]
        +delete(note_id)* bool
    }

    class Factory {
        +get_memory_client(backend, **kwargs) MemoryInterface
    }

    Factory ..> MemoryInterface : creates
    MemoryInterface ..> MemoryNote : uses
```

### Jbot Rotation
```mermaid
graph TD
    A[Start Rotation Loop] --> B[Purge Directives]
    B --> C[Rotate Messages]
    C --> D[Rotate nb Notes]
    D --> E[End Rotation]

    subgraph "Purge Directives"
        B1[Check Expiration Date]
        B2{Expired?}
        B2 -->|Yes| B3[Move to archive/]
        B2 -->|No| B4[Keep in directives/]
    end

    subgraph "Rotate Messages"
        C1[List .jbot/messages]
        C2{Count > Limit?}
        C2 -->|Yes| C3[Move oldest to archive/]
    end

    subgraph "Rotate NB (Knowledge Base)"
        D1[Filter by Tag]
        D2[Sort by Stable ID Desc]
        D3{Count > Tag Limit?}
        D3 -->|Yes| D4[Delete Oldest Notes]
        D1 --> D1_ADR[ADR Limit: 50]
        D1 --> D1_MEM[Memory Limit: 50]
    end
```

### Jbot Tasks
```mermaid
graph TD
    A[Task Operation] --> B{Fetch Task Data}
    B --> B1[Fetch Strategic Vision]
    B --> B2[Fetch Granular Tasks]
    B2 -->|nb ls tags:type:task| C[Process Each Task Note]
    C --> D{Action Type}
    
    D -->|add_task| E[Create New Task Note]
    D -->|update_task| F[Update Task Note]
    D -->|complete_task| G[Mark Note Completed]
    
    E -->|nb add| H[Update Technical Memory]
    F -->|nb edit| H
    G -->|nb edit status| H
    
    subgraph "Granular Per-Task Model"
        C1[Check status:active/backlog/completed]
        C2[Extract Agent Assignments]
        C1 --> C
        C2 --> C
    end
    
    subgraph "Strategic Alignment"
        B1 -->|nb show type:vision| S1[Parse Vision Section]
    end
```

### Jbot Tui
```mermaid
graph TD
    START[main] --> CHOICE{Select Action}
    CHOICE --> IDEA[💡 New Idea]
    CHOICE --> FEED[💬 Feedback]
    CHOICE --> PROMPT[🔧 Update Prompt]
    CHOICE --> EXIT[❌ Exit]

    IDEA --> DRAFT[Draft content via gum write]
    FEED --> DRAFT
    PROMPT --> DRAFT

    DRAFT --> REFINE[AI Refinement via Gemini]
    REFINE --> CONFIRM{Confirm Refinement}

    CONFIRM --> ACCEPT[✅ Accept & Push]
    CONFIRM --> EDIT[✏️ Edit Manually]
    CONFIRM --> RETRY[🔄 Retry AI]
    CONFIRM --> DISCARD[❌ Discard]

    ACCEPT --> PUSH[Push to nb knowledge base]
    EDIT --> DRAFT
    RETRY --> REFINE
```

### Jbot Utils
```mermaid
graph TD
    UTILS[jbot_utils.py] --> UNS[update_note_stably]
    UTILS --> ADR[get_recent_adrs]
    UTILS --> EXP[Expiration Logic]
    UTILS --> DASH[generate_dashboard]

    subgraph "Expiration Logic"
        GDE[get_directive_expiration]
        IDE[is_directive_expired]
        IDE --> GDE
    end

    subgraph "Dashboard Generation"
        DASH --> infra[jbot_infra: get_project_summary]
        DASH --> MER[Embed Mermaid Diagrams]
        DASH --> TASK[Format Task Board]
        DASH --> MSG[Format Messages]
    end

    UNS --> mem[jbot_memory_interface]
    ADR --> mem
```

### Nb Client
```mermaid
graph TD
    NbClient[NbClient] --> ResolvePath[_resolve_notebook_path]
    NbClient --> LoadCache[_load_persistent_cache]

    NbClient --> Add[add: nb add]
    NbClient --> Show[show: Hybrid Retrieval]
    NbClient --> Batch[show_batch: Parallel Retrieval]
    NbClient --> Search[search/ls: nb search/ls]
    NbClient --> Edit[edit: nb edit]
    NbClient --> Delete[delete: nb delete]

    subgraph "Hybrid Retrieval (show)"
        Show --> CacheCheck{In-memory Cache?}
        CacheCheck -- No --> FSRead{Direct FS Read?}
        FSRead -- No --> NBShow[nb show --print]
        CacheCheck -- Yes --> Return[Return Content]
        FSRead -- Yes --> Return
        NBShow --> Return
    end

    subgraph "Caching Mechanism"
        LoadCache --> FileCache[.jbot/nb_cache.json]
        FileCache --> IDMap[ID-to-Filename Mapping]
        FileCache --> ContentMap[Partial Content Cache]
    end

    Batch --> ThreadPool[ThreadPoolExecutor]
    ThreadPool --> Show
```

## 📈 Status & Progress
- **Tasks Completed:** 6
- **Milestones Achieved:** 5

### 📊 Technical ROI (Engineering Metrics)
- **Engineering Velocity:** 0.33 tasks/milestone
- **Architectural Density:** 0.17 ADRs/milestone
- **Knowledge Base Growth:** 69 records
- **Total Token Usage:** 1234 tokens
- **Completion Ratio:** 46.2%

## ✅ Recent Milestones
- **Architectural Evaluation of Flat Scaling:** Validated the efficiency of the flat organization model and single-user sandbox for long-term technical purity (ADR-210).
- **Flat Organization Scaling Efficiency (ADR-210):** Implemented granular per-task note model and increased ADR retention to 50 for long-term stability.
- **NB Client Robustness:** Fixed pagination issues in `NbClient.ls` by ensuring the `-a` flag is used for tag-based listings.
- **Infrastructure CLI Integration:** Integrated `maintenance`, `purge`, `rotate`, `dashboard`, and `send-message` as subcommands in the `jbot` CLI.
- **Modularized Infrastructure Logic:** Moved core logic for purging, rotation, and dashboard generation into `scripts/jbot_utils.py` for architectural purity.

