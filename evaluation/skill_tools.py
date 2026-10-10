"""Native repository checks and byte-compatible deterministic skill packaging.

No network, package installation, archive extraction or research-data publication.
Node counterparts remain independently exercised compatibility checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import sys
import zlib

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "ai-research-mentor"
PACKAGE = REPO / "dist" / "ai-research-mentor.zip"
LICENSE = REPO / "LICENSE"
sys.path.insert(0, str(SKILL / "runtime"))
LIMIT = 128 * 1024 * 1024
PREFIX = "ai-research-mentor"


def no_links(path, *, allow_missing=False):
    path = Path(path).absolute()
    for current in [*reversed(path.parents), path]:
        try:
            info = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                continue
            raise
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Linked path is forbidden: {current}")
    return path


def safe_name(name):
    name = name.replace("\\", "/")
    parts = (name[:-1] if name.endswith("/") else name).split("/")
    if not name or "\0" in name or any(not part or part in (".", "..") or ":" in part for part in parts) or parts[0] != PREFIX or (len(parts) < 2 and not name.endswith("/")):
        raise ValueError(f"Unsafe package entry: {name}")
    return name


def source_files(root=SKILL, *, license_path=None):
    root = no_links(root)
    if not root.is_dir():
        raise ValueError("Skill source is not a directory")
    files = {}
    total = 0
    def add(name, path):
        nonlocal total
        if name in files:
            raise ValueError(f"Duplicate source package entry: {name}")
        if path.stat().st_size > LIMIT - total:
            raise ValueError("Skill source exceeds package size limit")
        content = path.read_bytes()
        total += len(content)
        if total > LIMIT:
            raise ValueError("Skill source exceeds package size limit")
        files[name] = content
    def walk(directory):
        for path in sorted(directory.iterdir(), key=lambda p: p.name.encode("utf-16-be", "surrogatepass")):
            if path.name == "__pycache__" or re.search(r"\.py[co]$", path.name):
                continue
            no_links(path)
            if "\\" in path.name:
                raise ValueError(f"Unsupported source filename: {path.name}")
            if path.is_dir():
                walk(path)
            elif path.is_file():
                add(safe_name(f"{PREFIX}/{path.relative_to(root).as_posix()}"), path)
            else:
                raise ValueError(f"Unsupported source entry: {path}")
    walk(root)
    if f"{PREFIX}/SKILL.md" not in files:
        raise ValueError("Skill source lacks SKILL.md")
    if license_path:
        path = no_links(license_path)
        add(f"{PREFIX}/LICENSE", path)
        files = {f"{PREFIX}/LICENSE": files[f"{PREFIX}/LICENSE"], **files}
    if len(files) > 65534:
        raise ValueError("ZIP64 archives are not supported")
    return files


def build_package(root=SKILL, *, license_path=None):
    """Stored ZIP, UTF-8 names, fixed 1980 timestamp; byte-for-byte Node format."""
    files = source_files(root, license_path=license_path)
    locals_, central = [], []
    offset = 0
    for name, content in files.items():
        encoded = name.encode("utf-8")
        if len(encoded) > 65535:
            raise ValueError("ZIP entry name is too long")
        crc = zlib.crc32(content)
        header = struct.pack("<I5H3I2H", 0x04034B50, 20, 0x0800, 0, 0, 0x21, crc, len(content), len(content), len(encoded), 0)
        central_header = struct.pack("<I6H3I5H2I", 0x02014B50, 20, 20, 0x0800, 0, 0, 0x21, crc, len(content), len(content), len(encoded), 0, 0, 0, 0, 0, offset)
        locals_.extend((header, encoded, content))
        central.extend((central_header, encoded))
        offset += len(header) + len(encoded) + len(content)
    directory = b"".join(central)
    end = struct.pack("<I4H2IH", 0x06054B50, 0, 0, len(files), len(files), len(directory), offset, 0)
    return b"".join(locals_) + directory + end


def read_package(content):
    if len(content) < 22 or len(content) > LIMIT * 2:
        raise ValueError("Invalid ZIP size")
    end = -1
    for index in range(len(content) - 22, max(-1, len(content) - 65558), -1):
        if content[index:index + 4] == b"PK\x05\x06" and index + 22 + struct.unpack_from("<H", content, index + 20)[0] == len(content):
            end = index
            break
    if end < 0:
        raise ValueError("Missing ZIP end record")
    _, disk, directory_disk, local_count, count, directory_size, directory_offset, _ = struct.unpack_from("<I4H2IH", content, end)
    if disk or directory_disk or local_count != count or count == 65535 or directory_offset + directory_size != end:
        raise ValueError("Unsupported or invalid ZIP directory")
    files, names, regions, total, cursor = {}, set(), [], 0, directory_offset
    for _ in range(count):
        if cursor + 46 > end or content[cursor:cursor + 4] != b"PK\x01\x02":
            raise ValueError("Invalid ZIP central entry")
        fields = struct.unpack_from("<I6H3I5H2I", content, cursor)
        _, _, _, flags, method, _, _, crc, compressed, size, name_length, extra_length, comment_length, start_disk, _, attributes, local_offset = fields
        next_cursor = cursor + 46 + name_length + extra_length + comment_length
        if next_cursor > end or flags & ~0x0808 or method not in (0, 8) or start_disk or stat.S_ISLNK(attributes >> 16):
            raise ValueError("Unsupported or linked ZIP entry")
        encoded = content[cursor + 46:cursor + 46 + name_length]
        name = safe_name(encoded.decode("utf-8", errors="strict"))
        if name in names:
            raise ValueError(f"Duplicate ZIP entry: {name}")
        names.add(name)
        if local_offset + 30 > directory_offset or content[local_offset:local_offset + 4] != b"PK\x03\x04":
            raise ValueError("Invalid ZIP local entry")
        local = struct.unpack_from("<I5H3I2H", content, local_offset)
        if local[2] != flags or local[3] != method:
            raise ValueError("Invalid ZIP local entry")
        local_name_length, local_extra_length = local[9:11]
        data_offset = local_offset + 30 + local_name_length + local_extra_length
        if data_offset + compressed > directory_offset or content[local_offset + 30:local_offset + 30 + local_name_length] != encoded:
            raise ValueError("ZIP local name or length mismatch")
        if not flags & 8 and local[6:9] != (crc, compressed, size):
            raise ValueError("ZIP local checksum or size mismatch")
        regions.append((local_offset, data_offset + compressed))
        total += size
        if total > LIMIT or method == 0 and compressed != size:
            raise ValueError("ZIP uncompressed size is invalid")
        payload = content[data_offset:data_offset + compressed]
        if method == 0:
            data = payload
        else:
            decoder = zlib.decompressobj(-15)
            data = decoder.decompress(payload, max(1, size + 1))
            if not decoder.eof or decoder.unconsumed_tail:
                raise ValueError("ZIP decompression exceeds size or is incomplete")
        if len(data) != size or zlib.crc32(data) != crc:
            raise ValueError(f"ZIP checksum mismatch: {name}")
        if name.endswith("/"):
            if size:
                raise ValueError("ZIP directory has content")
        else:
            files[name] = data
        cursor = next_cursor
    if cursor != end:
        raise ValueError("ZIP directory length mismatch")
    regions.sort()
    if any(region[0] < previous[1] for previous, region in zip(regions, regions[1:])):
        raise ValueError("Overlapping ZIP entries")
    if f"{PREFIX}/SKILL.md" not in files:
        raise ValueError("ZIP lacks SKILL.md")
    return files


def verify_package(root, content, *, license_path=None):
    expected = source_files(root, license_path=license_path)
    actual = read_package(content)
    difference = {"missing": [name for name in expected if name not in actual],
                  "extra": [name for name in actual if name not in expected],
                  "changed": [name for name, data in expected.items() if name in actual and data != actual[name]]}
    if any(difference.values()):
        raise ValueError("Package differs from skill source: " + json.dumps(difference))
    return {"valid": True, "files": len(actual), "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def check_skill(root=SKILL):
    root = Path(root).absolute()
    errors, links = [], 0
    required = ["SKILL.md", "agents/openai.yaml", "references/python-core.md"]
    required += [f"scripts/{name}.{ext}" for name in ("research_audit", "research_sources", "research_outputs", "evolution_guard") for ext in ("py", "mjs")]
    required += ["scripts/research_mentor.py", "runtime/research_mentor/tool_cli.py"]
    required += [f"runtime/research_mentor/{name}.py" for name in ("core", "judgment", "audit", "sources", "outputs", "evolution")]
    required += [f"references/{name}.md" for name in ("data-contract", "literature", "ideation", "evaluation", "feedback", "design-basis", "self-improvement", "retrieval-adapters", "fulltext", "research-outputs", "source-tools")]
    required += [f"schemas/{name}.schema.json" for name in ("notes", "dossier", "ledger-event")]
    required += [f"tests/{name}.test.mjs" for name in ("research_audit", "research_sources", "research_outputs", "evolution_guard")]
    required += [f"tests/python/test_{name}.py" for name in ("audit", "sources", "outputs", "evolution")]
    for name in required:
        if not (root / name).is_file():
            errors.append(f"Missing {name}")
    if errors:
        return {"valid": False, "errors": errors, "local_links_checked": 0}
    source = (root / "SKILL.md").read_text(encoding="utf-8")
    front = re.match(r"---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)", source)
    if not front:
        errors.append("Missing YAML frontmatter")
    else:
        fields = {}
        for line in front[1].splitlines():
            field = re.fullmatch(r"(name|description): (.+)", line)
            if not field:
                errors.append("Unexpected or unsupported frontmatter syntax")
            else:
                fields[field[1]] = field[2]
        name, description = fields.get("name", ""), fields.get("description", "")
        if name != root.name or len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append("Invalid skill name")
        if not description or len(description.encode("utf-16-le")) // 2 > 1024 or re.search(r"[<>]", description):
            errors.append("Invalid description")
        if any(re.search(r":\s|^[\[\]{}!&*#>|%@`]", value) for value in fields.values()):
            errors.append("Frontmatter requires unsupported YAML syntax")
    if re.search(r"^\s*\[TODO:[^\n]*\]\s*$", source, re.MULTILINE):
        errors.append("Unfinished scaffold")
    metadata = (root / "agents/openai.yaml").read_text(encoding="utf-8")
    ui = {key: json.loads(value) for key, value in re.findall(r'^  (display_name|short_description|default_prompt): ("[^"\r\n]*")$', metadata, re.MULTILINE)}
    if any(not ui.get(key) for key in ("display_name", "short_description", "default_prompt")):
        errors.append("Missing quoted UI strings")
    if ui.get("short_description") and not 25 <= len(ui["short_description"]) <= 64:
        errors.append("UI description length outside 25–64")
    if "$ai-research-mentor" not in ui.get("default_prompt", ""):
        errors.append("Default prompt misses skill invocation")
    if not re.search(r"^  allow_implicit_invocation: true$", metadata, re.MULTILINE):
        errors.append("Implicit invocation is not enabled")
    for name in [name for name in required if name.endswith(".md")]:
        for destination in re.findall(r"\[[^\]]*\]\(([^)]+)\)", (root / name).read_text(encoding="utf-8")):
            if re.match(r"(?:[a-z]+:|#)", destination, re.IGNORECASE):
                continue
            target = (root / name).parent.joinpath(destination.split("#")[0]).resolve()
            if not target.is_relative_to(root.resolve()):
                errors.append(f"Reference escapes skill: {destination}")
            elif not target.exists():
                errors.append(f"Broken reference in {name}: {destination}")
            else:
                links += 1
    for name in [name for name in required if name.endswith(".schema.json")]:
        schema = json.loads((root / name).read_text(encoding="utf-8"))
        def inspect(value):
            if isinstance(value, dict):
                ref = value.get("$ref")
                if isinstance(ref, str):
                    try:
                        if not ref.startswith("#/"):
                            raise KeyError(ref)
                        current = schema
                        for part in ref[2:].split("/"):
                            part = part.replace("~1", "/").replace("~0", "~")
                            if isinstance(current, list):
                                if not re.fullmatch(r"0|[1-9][0-9]*", part):
                                    raise KeyError(part)
                                current = current[int(part)]
                            else:
                                current = current[part]
                    except (KeyError, TypeError, IndexError):
                        errors.append(f"Broken or external schema reference in {name}: {ref}")
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
        inspect(schema)
    return {"valid": not errors, "errors": errors, "local_links_checked": links, "skill_lines": len(source.split("\n")), "note": "Local metadata/reference checks; does not prove research quality."}


def check_examples():
    from research_mentor.audit import validate_dossier, rank_dossier
    results = []
    for kind in ("empirical", "theoretical", "measurement"):
        directory = REPO / "examples" / f"{kind}-example"
        if "SYNTHETIC EXAMPLE — NOT A REAL SCIENTIFIC CLAIM" not in (directory / "README.md").read_text(encoding="utf-8"):
            raise ValueError(f"Example lacks clear synthetic provenance: {kind}")
        dossier = json.loads((directory / "dossier.json").read_text(encoding="utf-8"))
        checked = validate_dossier(dossier)
        if not checked["valid"]:
            raise ValueError(f"{kind}: {checked['errors']}")
        ranked = rank_dossier(dossier)
        expected = ranked["held" if kind == "measurement" else "ranked"]
        if len(expected) != 1 or ranked["killed"]:
            raise ValueError(f"Example review or intended next step is stale: {kind}")
        results.append({"type": kind, "valid": True, "decision": expected[0]["decision"], "synthetic": True})
    return {"examples": results, "note": "Synthetic schema examples, not scientific findings."}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check-skill", "check-examples", "package", "check-package"))
    args = parser.parse_args(argv)
    try:
        if args.command == "check-skill":
            result = check_skill()
        elif args.command == "check-examples":
            result = check_examples()
        elif args.command == "check-package":
            no_links(PACKAGE)
            result = verify_package(SKILL, PACKAGE.read_bytes(), license_path=LICENSE)
        else:
            content = build_package(SKILL, license_path=LICENSE)
            no_links(PACKAGE, allow_missing=True)
            if PACKAGE.exists():
                if not PACKAGE.is_file():
                    raise ValueError("Package target is not a regular file")
                read_package(PACKAGE.read_bytes())
            PACKAGE.parent.mkdir(exist_ok=True)
            PACKAGE.write_bytes(content)
            result = {"package": str(PACKAGE), **verify_package(SKILL, content, license_path=LICENSE)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("valid", True) else 1
    except (OSError, ValueError, struct.error, zlib.error) as error:
        print(json.dumps({"valid": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
