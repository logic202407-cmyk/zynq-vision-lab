"""Read-only S01-S03 inputs: frozen sources, local dependency hashes and options.

No compiler, GUI, device access, network, dependency download or installation.
Optional dependency paths are private inputs; public output uses logical labels.
"""
import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "src/prototype/stm32_openmv_gimbal/stm32"
BASE = "04ba0db3e1a4f67cee7efa7b941d69ce281bffa2"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def archive_member(name):
    root = "STM32F10x_StdPeriph_Lib_V3.5.0/Libraries/"
    base = name.split("/")[-1]
    if name.startswith("Library/"):
        return root + "STM32F10x_StdPeriph_Driver/" + ("src/" if base.endswith(".c") else "inc/") + base
    if base in ("core_cm3.c", "core_cm3.h"):
        return root + "CMSIS/CM3/CoreSupport/" + base
    return root + "CMSIS/CM3/DeviceSupport/ST/STM32F10x/" + ("startup/arm/" if base.endswith(".s") else "") + base


def audit(deps=None, origin=None, archive=None):
    started = datetime.now(timezone.utc).isoformat()
    protected = sorted(p for p in FW.rglob("*") if p.is_file() and
                       p.name != "s01_s08_bridge.c")
    protected += [ROOT / "tests/test_stm32_p0.py", ROOT / "tools/build_stm32_p0.py"]
    source_rows = []
    for path in protected:
        name = path.relative_to(ROOT).as_posix()
        frozen = subprocess.check_output(["git", "show", BASE + ":" + name], cwd=ROOT)
        source_rows.append(dict(path=name, baseline_sha256=sha(frozen),
                                actual_sha256=sha(path.read_bytes()), equal=frozen == path.read_bytes()))
    cases = json.loads((FW / "tests/scenarios.json").read_text(encoding="utf-8"))
    dependency_rows = []
    manifest = json.loads((FW / "dependencies.sha256.json").read_text(encoding="utf-8"))
    package = None
    members = {}
    if archive:
        with zipfile.ZipFile(archive) as zipped:
            members = {name: zipped.read(archive_member(name)) for name in manifest}
            licenses = [name for name in zipped.namelist() if re.search(r"license|licence|eula", name, re.I)]
            package = dict(logical_path="<LOCAL_SPL350_ARCHIVE>", filename=archive.name,
                           sha256=sha(archive.read_bytes()), member_count=len(zipped.namelist()),
                           matching_manifest_files=sum(sha(members[name]) == expected for name, expected in manifest.items()),
                           official_download_origin_verified=False,
                           license_members=[dict(member=name, sha256=sha(zipped.read(name)), bytes=len(zipped.read(name))) for name in licenses])
    for name, expected in manifest.items():
        row = dict(path=name, expected_sha256=expected, original_package_verified=False,
                   full_license_verified=False)
        if name in members:
            matches = sha(members[name]) == expected
            row.update(local_archive_member=archive_member(name), local_archive_sha256=sha(members[name]),
                       local_archive_matches_manifest=matches,
                       original_package_verified=matches,
                       original_package_scope="byte identity in found local archive, not ST download authenticity")
        for label, folder in (("actual_copy", deps), ("candidate_local_origin", origin)):
            path = folder / name if folder else None
            if path and path.is_file():
                raw = path.read_bytes()
                header = raw[:6000].decode("latin-1")
                version = re.search(r"@version\s*([^\r\n]+)|Version:\s*([^\r\n]+)", header)
                row[label] = dict(logical_root="<" + label.upper() + ">", sha256=sha(raw),
                                  matches_manifest=sha(raw) == expected,
                                  header_version=(version.group(1) or version.group(2)).strip() if version else None,
                                  header_sha256=sha(raw[:6000]))
            else:
                row[label] = dict(present=False)
        dependency_rows.append(row)
    project = ET.parse(FW / "Project.uvprojx").getroot()
    def field(path):
        return project.findtext(".//" + path)
    old_build = json.loads((ROOT / "report/experiments/stm32-p0-2026-10-04/firmware.json").read_text(encoding="utf-8"))
    compiled = {}
    for record in old_build["commands"]:
        arguments = record["command"]
        inputs = [s for s in arguments if s.lower().endswith((".c", ".s"))]
        if inputs:
            name = inputs[0].replace("\\", "/").rsplit("/", 1)[-1]
            compiled[name] = dict(cpu=arguments[arguments.index("--cpu") + 1],
                                  defines=[s[2:] for s in arguments if s.startswith("-D")],
                                  includes=[s[2:] for s in arguments if s.startswith("-I")],
                                  optimization=[s for s in arguments if s.startswith("-O")],
                                  c99="--c99" in arguments, debug="-g" in arguments,
                                  split_sections="--split_sections" in arguments,
                                  interwork="--apcs=interwork" in arguments,
                                  exit_code=record["exit_code"])
    units = []
    for element in project.findall(".//File"):
        if element.findtext("FileType") not in ("1", "2"):
            continue
        name = element.findtext("FileName")
        units.append(dict(unit=name, project_path=element.findtext("FilePath"),
                          language="C" if name.endswith(".c") else "assembler",
                          file_override=element.find("FileOption") is not None,
                          recorded_cli=compiled.get(name),
                          gui_target_defines=field("Cads/VariousControls/Define") if name.endswith(".c") else field("Aads/VariousControls/Define"),
                          gui_target_includes=field("Cads/VariousControls/IncludePath") if name.endswith(".c") else field("Aads/VariousControls/IncludePath")))
    units_equal = {u["unit"] for u in units} == set(compiled)
    options = {name: field(path) for name, path in dict(
        compiler="pCCUsed", ac6="uAC6", cpu="ArmAdsMisc/AdsCpuType", c99="Cads/uC99",
        optimization_raw="Cads/Optim", one_elf_section="Cads/OneElfS",
        interwork="Cads/interw", enum_int="Cads/EnumInt", signed_char="Cads/PlainCh",
        warning_level_raw="Cads/wLevel", suppress_auto_includes="Cads/uSurpInc",
        micro_lib="ArmAdsMisc/useUlib", generated_scatter="LDads/umfTarg",
        use_scatter_file="LDads/useFile", scatter="LDads/ScatterFile",
        irom_start="OnChipMemories/IROM/StartAddress", irom_size="OnChipMemories/IROM/Size",
        iram_start="OnChipMemories/IRAM/StartAddress", iram_size="OnChipMemories/IRAM/Size").items()}
    hook_values = [node.text for section in ("BeforeCompile", "BeforeMake", "AfterMake")
                   for node in project.findall(".//" + section + "/RunUserProg1") + project.findall(".//" + section + "/RunUserProg2")]
    return dict(schema="stm32-s01-s08/audit-v1", baseline=BASE, utc_start=started,
                utc_end=datetime.now(timezone.utc).isoformat(),
                S01=dict(original_total=109, original_stm32=69, fixed_scenarios=len(cases),
                         queue_tests=3, scenario_ids=[c["id"] for c in cases], protected=source_rows,
                         all_protected_equal=all(r["equal"] for r in source_rows)),
                S02=dict(execution="blocked", reason="local archive byte provenance established when present; full ST SPL licence and official download provenance remain unverified",
                         package=package, dependency_rows=dependency_rows, official_product="https://www.st.com/en/embedded-software/stsw-stm32054.html"),
                S03=dict(execution="implemented", review="static audit; GUI not_run",
                         options=options, units=units, source_sets_equal=units_equal,
                         cli_build_rerun_this_stage=False, enabled_user_hooks=any(x != "0" for x in hook_values),
                         cli_scatter_sha256=sha((FW / "firmware.sct").read_bytes()),
                         evidence_build_sha256=sha((ROOT / "report/experiments/stm32-p0-2026-10-04/firmware.json").read_bytes())))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deps", type=Path)
    parser.add_argument("--candidate-origin", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = audit(args.deps, args.candidate_origin, args.archive)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(protected_equal=data["S01"]["all_protected_equal"],
                          dependency_matches=sum(r["actual_copy"].get("matches_manifest", False) for r in data["S02"]["dependency_rows"]),
                          units=len(data["S03"]["units"]), source_sets_equal=data["S03"]["source_sets_equal"])))
    if not data["S01"]["all_protected_equal"] or not data["S03"]["source_sets_equal"]:
        raise SystemExit(1)
