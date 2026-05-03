# Security Policy

## Supported Versions

We provide security updates for the following versions of our infrastructure templates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of our infrastructure-as-code and system configurations seriously. If you find a security vulnerability, please report it privately rather than opening a public issue.

### Scope

The following are within the scope of our security policy:
- Vulnerabilities in the Core NixOS module (`core.nix`).
- Insecure defaults or privilege escalation paths in the systemd service.
- Exposed secrets or insecure secret handling in the prompt injection script.
- Flaws in the `system_prompt.txt` that could lead to unintended command execution.

### Reporting Process

1.  **Email**: Send a detailed report to `[security@example.com]`.
2.  **Details**: Include a description of the vulnerability, steps to reproduce, and potential impact.
3.  **Acknowledgement**: You will receive an acknowledgement within 48 hours.
4.  **Fix**: We will work on a fix and coordinate a disclosure date with you.

Please do not disclose the vulnerability publicly until a fix has been released and we have reached a mutual agreement on the disclosure timeline.

## Infrastructure Security Standards

All templates in this repository aim to follow these security principles:
- **Principle of Least Privilege**: Services and containers should run with the minimum necessary permissions (e.g., non-root users, dropped capabilities).
- **Reproducibility**: All configurations should be reproducible to ensure auditability and consistent security posture.
- **Secret Management**: No hardcoded secrets. Use Vault, environment-specific secret stores, or encrypted inputs.
- **Sandboxing**: Utilize Systemd isolation, Docker namespaces, and other containerization security features.
