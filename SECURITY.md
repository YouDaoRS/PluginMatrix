# Security Policy

PluginMatrix is early-stage software. Security fixes are made on the current `main` branch; older snapshots are not maintained as separate supported release lines.

Do not put exploit details, credentials, private server logs, proprietary plugin JARs, or other sensitive material in a public issue. GitHub Private Vulnerability Reporting is enabled for this repository; use the **Security** tab and **Report a vulnerability**. Include the affected PluginMatrix version, operating system, Python and Java versions, impact, reproduction steps, and the smallest redacted evidence needed to confirm the problem.

If the private form is unexpectedly unavailable, open a public issue containing only a request for a private reporting channel and no vulnerability details. This avoids inventing an unverified security email address.

Ordinary crashes, unsupported Paper versions, incorrect verdicts without a security impact, and feature requests belong in the normal issue templates.

## Local Web UI boundary

`pluginmatrix web` listens only on `127.0.0.1`. It is not a LAN or cloud service and does not transmit plugin JARs, configurations, reports, or logs to PluginMatrix infrastructure. Browser-selected JARs are streamed only to the local process and kept in a session-temporary directory.

State-changing requests require an exact local Origin, a SameSite/HttpOnly session cookie, and an unguessable CSRF header token. Host headers are restricted to the active loopback port. Request bodies, paths, file names, job history, events, environments, and concurrency are bounded. Artifact endpoints resolve opaque IDs from a completed-job allowlist and recheck the opened file identity; there is no arbitrary path download endpoint. Pages use restrictive CSP/no-sniff/no-referrer headers, and untrusted result text is inserted with DOM `textContent`.

These controls protect the local HTTP surface; they do not sandbox the tested Minecraft plugin. Run only plugins you trust with the current OS account's permissions.
