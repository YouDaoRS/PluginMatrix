"""Human-facing rendering of guided application responses, never a new verdict."""
from .terminal import print


def render(command, document):
    if command == "profiles":
        for profile in document["profiles"]:
            print(f"{profile['id']} (revision {profile['revision']})")
            print(f"  Startup: {profile['timeout']} s; stability: {profile['stability_window']} s; "
                  f"environments: {profile['minimum_environments']}..{profile['maximum_environments']}")
            print("  Registration suggestions: " + ("review before use" if profile["suggest_registrations"] else "none"))
            if profile["fixed_builds"]:
                print("  Requires fixed official builds and complete supported static analysis.")
        print("Profiles define concrete checks, not full compatibility guarantees.")
    elif command == "analyze":
        print("Static prerequisites: " + ("READY" if document["valid"] else "NEEDS ATTENTION"))
        metadata = document.get("plugin") or {}
        print(f"Plugin: {metadata.get('plugin_name', '?')} {metadata.get('plugin_version', '')}")
        print(f"API minimum: {metadata.get('api_version') or 'not declared'}")
        print(f"JAR SHA-256: {metadata.get('plugin_jar_sha256') or 'unavailable'}")
        graph = document["dependency_report"]
        for issue in [*document["errors"], *graph["errors"], *graph.get("warnings", [])]:
            print(f"  {issue.get('code', 'DIAGNOSTIC')}: {issue['reason']}")
        suggestions = document.get("suggestions") or {}
        checks = (suggestions.get("behavior") or {}).get("checks", [])
        print(f"Reviewable registration checks: {len(checks)}")
        for check in checks:
            print(f"  {check['id']}: {check['type']} {check.get('name', '')}")
        for item in suggestions.get("omitted", []):
            print(f"  Omitted: {item['reason']}")
        print("Static analysis is not runtime PASS or a safety guarantee. Dependencies must be supplied as local JARs.")
    elif command == "recommend":
        recommendation = document["recommendation"]
        selected = recommendation["selection"]
        print("Recommendation: " + ("READY FOR REVIEW" if recommendation["ready"] else "UNRESOLVED"))
        print(f"Target: {selected['provider']} / Minecraft {selected['minecraft'] or 'choose explicitly'}")
        print(f"Build: {selected['build'] or 'unresolved'}")
        print(f"Java: {selected['java'] or 'select a matching full JDK with javac'}")
        if selected.get("jdk_dir"):
            print(f"Managed store: {selected['jdk_dir']}")
        for reason in recommendation["reasons"]:
            print(f"  {reason['code']}: {reason['reason']} [source: {reason['source']}]")
        for issue in [*recommendation["conflicts"], *recommendation["unresolved"]]:
            print(f"  Action required: {issue}")
        print("A recommendation is not a compatibility verdict. api-version is not a supported version range.")
    else:
        records = document.get("jdks") if "jdks" in document else [document]
        if not records:
            print("No managed JDKs installed.")
        for record in records:
            package = record.get("package") or record
            print(f"JDK: {record.get('id') or package.get('id', '?')}")
            if record.get("deleted"):
                print("  Deleted. System Java and persistent lock files are unchanged.")
                continue
            print(f"  {package.get('release', '')} / {package.get('os', '?')} / {package.get('architecture', '?')}")
            print(f"  Integrity: {record.get('integrity', 'official metadata only; not installed')}")
            if package.get("size"):
                print(f"  Archive: {package['size']:,} bytes")
            if package.get("sha256"):
                print(f"  Official SHA-256: {package['sha256']}")
            if package.get("url"):
                print(f"  Source: {package['url']}")
            if record.get("path"):
                print(f"  Java: {record['path']}")
            if record.get("error"):
                print(f"  Error: {record['error']}")
        if "package" in document and not document.get("path"):
            print("Install only after review: pluginmatrix jdk install --major "
                  f"{document['package']['major']} --id {document['package']['id']}")
