#!/usr/bin/env python3
"""Validate portable skills and their behavioral evaluation specifications."""

import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
FRONTMATTER_KEYS = {
    "name", "description", "license", "compatibility", "metadata", "allowed-tools"
}
RESOURCE_PREFIXES = ("references/", "scripts/", "assets/")
MARKDOWN_LINK = re.compile(
    r"\]\(\s*(?:<([^>\n]+)>|((?:[^()\s\\]|\\.|\((?:[^()\\]|\\.)*\))+))"
)
REFERENCE_LINK = re.compile(
    r"^\s{0,3}\[[^\]\n]+\]:\s*(?:<([^>\n]+)>|(\S+))", re.MULTILINE
)
CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)


class Validator:
    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def problem(self, path, message, warning=False):
        if warning:
            self.warnings += 1
        else:
            self.errors += 1
        print(f"{'WARN' if warning else 'ERROR'} {path.relative_to(ROOT)}: {message}")

    def read_text(self, path):
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            self.problem(path, f"cannot read file: {error}")
            return None

    def resolve_inside(self, directory, path, report_path):
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(directory.resolve()):
                self.problem(report_path, f"path escapes {directory.relative_to(ROOT)}: {path.name}")
                return None
            return resolved
        except (OSError, RuntimeError, ValueError) as error:
            self.problem(report_path, f"cannot resolve path {path.name}: {error}")
            return None

    def check_symlinks(self, directory):
        def walk_error(error):
            self.problem(directory, f"cannot inspect skill files: {error}")

        for current, directories, files in os.walk(directory, followlinks=False, onerror=walk_error):
            for name in directories + files:
                path = Path(current) / name
                if path.is_symlink():
                    self.resolve_inside(directory, path, path)

    def check_resources(self, directory, text):
        references = set()
        for pattern in (MARKDOWN_LINK, REFERENCE_LINK):
            for match in pattern.finditer(text):
                target = match.group(1) or match.group(2)
                if target.startswith(RESOURCE_PREFIXES):
                    target = unquote(target.split("#", 1)[0].split("?", 1)[0])
                    target = re.sub(r"\\(.)", r"\1", target)
                    references.add(target)
        for match in CODE_SPAN.finditer(text):
            code = match.group(2).strip()
            if code.startswith(RESOURCE_PREFIXES):
                references.add(code if (directory / code).exists() else code.split()[0])
        for target in sorted(references):
            path = directory / target
            resolved = self.resolve_inside(directory, path, directory / "SKILL.md")
            if resolved is not None and not resolved.exists():
                self.problem(directory / "SKILL.md", f"referenced path does not exist: {target}")

    def skill(self, directory):
        self.check_symlinks(directory)
        path = directory / "SKILL.md"
        text = self.read_text(path)
        if text is None:
            return
        self.check_resources(directory, text)
        lines = text.splitlines()
        if not lines or lines[0] != "---":
            self.problem(path, "SKILL.md must start with YAML frontmatter delimited by ---")
            return
        try:
            end = lines.index("---", 1)
        except ValueError:
            self.problem(path, "YAML frontmatter is missing its closing --- delimiter")
            return
        if len(lines[end + 1:]) > 500:
            self.problem(path, f"body has {len(lines[end + 1:])} lines (recommended maximum: 500)", warning=True)
        try:
            frontmatter = yaml.safe_load("\n".join(lines[1:end]))
        except yaml.YAMLError as error:
            self.problem(path, f"invalid YAML frontmatter: {' '.join(str(error).splitlines())}")
            return
        if not isinstance(frontmatter, dict):
            self.problem(path, "frontmatter must be a mapping")
            return
        for key in frontmatter:
            if key not in FRONTMATTER_KEYS:
                self.problem(path, f"unknown frontmatter key: {key!r}")
        name = frontmatter.get("name")
        if not isinstance(name, str) or not 1 <= len(name) <= 64 or not NAME.fullmatch(name):
            self.problem(path, "name must be a 1–64 character lowercase alphanumeric, hyphen-separated string")
        if name != directory.name:
            self.problem(path, f"name must match directory name {directory.name!r}")
        description = frontmatter.get("description")
        if not isinstance(description, str) or not description.strip() or len(description) > 1024:
            self.problem(path, "description must be a non-empty string of at most 1024 characters")
        if "compatibility" in frontmatter:
            value = frontmatter["compatibility"]
            if not isinstance(value, str) or not value.strip() or len(value) > 500:
                self.problem(path, "compatibility must be a non-empty string of at most 500 characters")
        for key in ("license", "allowed-tools"):
            if key in frontmatter and not isinstance(frontmatter[key], str):
                self.problem(path, f"{key} must be a string")
        if "metadata" in frontmatter:
            value = frontmatter["metadata"]
            if not isinstance(value, dict) or any(
                not isinstance(key, str) or not isinstance(item, str)
                for key, item in value.items()
            ):
                self.problem(path, "metadata must be a mapping of strings to strings")

    def string_list(self, value, path, label):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            self.problem(path, f"{label} must be an array of strings")
            return False
        return True

    def eval_path(self, directory, value, report_path, label, file_only=False):
        if not isinstance(value, str) or not value.strip():
            self.problem(report_path, f"{label} must be a non-empty relative path string")
            return
        path = Path(value)
        if path.is_absolute():
            self.problem(report_path, f"{label} must be relative to its eval suite")
            return
        resolved = self.resolve_inside(directory, directory / path, report_path)
        if resolved is None:
            return
        if not resolved.exists():
            self.problem(report_path, f"{label} path does not exist: {value}")
        elif file_only and not resolved.is_file():
            self.problem(report_path, f"{label} must reference a file: {value}")

    def eval_suite(self, directory, skills):
        path = directory / "evals.json"
        if directory.name not in skills:
            self.problem(path, f"no matching skills/{directory.name} directory")
        text = self.read_text(path)
        if text is None:
            return
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as error:
            self.problem(path, f"invalid JSON: {error}")
            return
        if not isinstance(spec, dict):
            self.problem(path, "eval specification must be an object")
            return
        skill_name = spec.get("skill_name")
        if not isinstance(skill_name, str) or skill_name != directory.name:
            self.problem(path, f"skill_name must equal directory name {directory.name!r}")
        if "trigger" not in spec and "evals" not in spec:
            self.problem(path, "at least one of trigger or evals is required")
        if "trigger" in spec:
            trigger = spec["trigger"]
            if not isinstance(trigger, dict):
                self.problem(path, "trigger must be an object")
            else:
                for key in ("positive", "negative"):
                    if key in trigger:
                        self.string_list(trigger[key], path, f"trigger.{key}")
        if "evals" not in spec:
            return
        cases = spec["evals"]
        if not isinstance(cases, list):
            self.problem(path, "evals must be an array")
            return
        ids = set()
        for index, case in enumerate(cases):
            label = f"evals[{index}]"
            if not isinstance(case, dict):
                self.problem(path, f"{label} must be an object")
                continue
            case_id = case.get("id")
            if not isinstance(case_id, str) or not NAME.fullmatch(case_id):
                self.problem(path, f"{label}.id must be a lowercase alphanumeric, hyphen-separated string")
            elif case_id in ids:
                self.problem(path, f"duplicate eval id: {case_id}")
            else:
                ids.add(case_id)
            prompt = case.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                self.problem(path, f"{label}.prompt must be a non-empty string")
            if "expected_output" in case and not isinstance(case["expected_output"], str):
                self.problem(path, f"{label}.expected_output must be a string")
            if "files" in case and self.string_list(case["files"], path, f"{label}.files"):
                for value in case["files"]:
                    self.eval_path(directory, value, path, f"{label}.files")
            has_expectations = False
            if "expectations" in case:
                has_expectations = self.string_list(case["expectations"], path, f"{label}.expectations") and bool(case["expectations"])
            if "check" in case:
                self.eval_path(directory, case["check"], path, f"{label}.check", file_only=True)
            elif not has_expectations:
                self.problem(path, f"{label} requires a check or at least one expectation")


def directories(path):
    if not path.exists():
        return {}
    return {
        child.name: child
        for child in sorted(path.iterdir())
        if not child.name.startswith(".") and child.is_dir()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", metavar="SKILL", help="restrict validation to these skill names")
    args = parser.parse_args()
    validator = Validator()
    skills = directories(ROOT / "skills")
    suites = directories(ROOT / "evals")
    if args.skills:
        requested = set(args.skills)
        for name in sorted(requested):
            if not NAME.fullmatch(name) or len(name) > 64:
                validator.problem(ROOT / "skills", f"invalid requested skill name: {name!r}")
            elif name not in skills and name not in suites:
                validator.problem(ROOT / "skills" / name, "requested skill does not exist")
        skills = {name: path for name, path in skills.items() if name in requested}
        suites = {name: path for name, path in suites.items() if name in requested}
    for name, directory in skills.items():
        validator.skill(directory)
        if name not in suites:
            validator.problem(directory, "skill has no eval suite", warning=True)
    for directory in suites.values():
        validator.eval_suite(directory, skills)
    print(f"{len(skills)} skills, {len(suites)} eval suites: {validator.errors} errors, {validator.warnings} warnings")
    return 1 if validator.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
