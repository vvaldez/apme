# ansible-core Deprecation Mining: 2.21–2.24 Horizon

**Status**: Complete
**Date**: 2026-03-17
**Source**: Static analysis of `ansible/lib/ansible/` on the `devel` branch (post-2.20 release)
**Commit**: [`80ee6b5d920d`](https://github.com/ansible/ansible/commit/80ee6b5d920d181fa46b6fdc5e40dca73a2166cc) (2026-03-16)

## Objective

Mine the ansible-core source code for all version-gated deprecation warnings to identify upcoming breaking changes before they ship. This enables APME to warn users **ahead of their upgrade**, not after things break.

The existing [ANSIBLE_CORE_MIGRATION.md](/docs/ANSIBLE_CORE_MIGRATION.md) covers 2.19 and 2.20 changes. This document extends coverage to 2.21–2.24 and 2.27 (long-horizon).

## Methodology

Three deprecation mechanisms exist in ansible-core:

| Mechanism | Count | Description |
|-----------|-------|-------------|
| `display.deprecated()` | 43 active | Runtime warning emitted when code path is hit |
| `# deprecated:` comments | 26 | Staged deprecations not yet active |
| `_tags.Deprecated()` | 4 | Tag-based deprecation system (new in 2.19+) |

All instances were extracted with `rg` across `ansible/lib/ansible/` and categorized by: (1) target removal version, (2) whether content authors or plugin developers are affected, and (3) whether APME can statically detect the pattern.

## Version distribution

| Version | Active | Staged (comments) | Total |
|---------|--------|--------------------|-------|
| 2.21 | 2 | 0 | 2 |
| 2.22 | 4 | 0 | 4 |
| 2.23 | 35 | 24 | 59 |
| 2.24 | 6 | 0 | 6 |
| 2.27 | 0 | 4 | 4 |
| No version | 1 | 0 | 1 |

---

## Content-facing deprecations (statically detectable)

These affect playbook authors, role developers, and inventory maintainers. APME can detect these patterns through static analysis of YAML content.

### 2.21

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 1 | `paramiko_ssh` connection plugin usage | `plugins/connection/paramiko_ssh.py` | Detect `connection: paramiko_ssh` or `ansible_connection: paramiko_ssh` in plays/host vars |

### 2.22

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 2 | `follow_redirects: yes` or `follow_redirects: no` (string) in `url` lookup | `plugins/lookup/url.py` | Detect `follow_redirects: yes\|no` in lookup args |
| 3 | `yum_repository` module parameter deprecations (2 params) | `modules/yum_repository.py` | Detect deprecated parameter names in `yum_repository` tasks |

### 2.23 — The Big Wave

#### YAML parsing

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 4 | `!!omap` YAML tag | `_internal/_yaml/_constructor.py` | Scan YAML content for `!!omap` tag |
| 5 | `!!pairs` YAML tag | `_internal/_yaml/_constructor.py` | Scan YAML content for `!!pairs` tag |
| 6 | `!vault-encrypted` tag → use `!vault` | `_internal/_yaml/_constructor.py` | Scan YAML content for `!vault-encrypted` tag |

#### Conditionals and templating

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 7 | Empty `when:` conditional evaluated as True | `_internal/_templating/_engine.py` | Detect `when: ""` or `when:` (empty/null) |
| 8 | `when: "{{ var }}"` — conditional as template | `_internal/_templating/_engine.py` | **Already covered by L015** (OPA) |
| 9 | Broken conditional expressions (various) | `_internal/_templating/_engine.py` | Detect conditionals that don't parse as Jinja2 expressions |
| 10 | Test plugin returning non-boolean result | `_internal/_templating/_jinja_plugins.py` | Not statically detectable (runtime behavior) |

#### Task parsing

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 11 | `action:` as a mapping (`action: {module: copy, src: a}`) | `parsing/mod_args.py` | Detect `action:` with dict value |
| 12 | Empty `args:` keyword on a task | `parsing/mod_args.py` | Detect `args:` with null value |
| 13 | Legacy `k=v` args merged with `args:` mapping | `parsing/mod_args.py` | Detect tasks with both inline `k=v` and `args:` |

#### Filters

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 14 | `bool` filter coercing invalid values | `plugins/filter/core.py` | Not statically detectable (runtime data) |
| 15 | `from_yaml` filter on non-string input | `plugins/filter/core.py` | Not statically detectable (runtime data) |
| 16 | `from_yaml_all` filter on non-string input | `plugins/filter/core.py` | Not statically detectable (runtime data) |

#### Plugins

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 17 | `tree` callback plugin removed | `plugins/callback/tree.py` | Detect `callback_plugins: tree` or `stdout_callback = tree` in ansible.cfg |
| 18 | `oneline` callback plugin removed | `plugins/callback/oneline.py` | Detect `stdout_callback = oneline` in ansible.cfg |
| 19 | Plugin auto-redirect (using old name instead of FQCN) | `plugins/loader.py` | **Already covered by M001** (dynamic) |
| 20 | v1 callback method overrides (`on_*` instead of `v2_on_*`) | `plugins/callback/__init__.py` | Detect in custom callback plugin Python files |
| 21 | `on_any` deprecated callback method | `plugins/callback/__init__.py` | Same as above |
| 22 | Third-party strategy plugin usage | `plugins/loader.py` | Detect `strategy:` not in `ansible.builtin.*` |

#### Inventory

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 23 | Inventory script missing `_meta.hostvars` | `plugins/inventory/script.py` | Analyze inventory script output format |
| 24 | Malformed inventory script group data (non-dict groups) | `plugins/inventory/script.py` | Same |
| 25 | Invalid inventory variable names | `inventory/host.py`, `inventory/group.py` | Validate variable names in host/group vars |

#### Lookups

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 26 | `first_found` lookup auto-splitting paths on delimiters | `plugins/lookup/first_found.py` | Detect `first_found` terms containing `,` or `:` |

#### Variables

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 27 | `play_hosts` magic variable → `ansible_play_batch` | `vars/manager.py` | Detect `play_hosts` in Jinja2 expressions |

#### Data loading

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 28 | Files with invalid encoding (surrogate escaping) | `parsing/dataloader.py` | Not statically detectable (file encoding issue) |

### 2.24

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 29 | **Top-level fact injection** — `ansible_hostname` → `ansible_facts["hostname"]` | `vars/manager.py` | Detect `ansible_*` fact variable usage in Jinja2 expressions (HUGE impact — virtually every playbook) |
| 30 | Internal `vars` dictionary deprecated → use `vars`/`varnames` lookups | `vars/manager.py` | Detect `vars` dict access patterns in templates |
| 31 | `include_vars` with `ignore_files` as string → use list | `plugins/action/include_vars.py` | Detect `ignore_files:` with string value in `include_vars` tasks |
| 32 | `hash_params` function deprecated | `playbook/role/__init__.py` | Affects role internals and custom plugins calling this function |
| 33 | `Shell.wrap_for_exec` method | `plugins/shell/__init__.py` | Affects custom shell plugins |
| 34 | `PowerShell._encode_script` method | `plugins/shell/powershell.py` | Affects `ansible.windows` reboot plugin |

### 2.27 (long-horizon, currently staged in comments only)

| # | Pattern | Source file | Detection approach |
|---|---------|-------------|-------------------|
| 35 | `ansible.parsing.ajson` module removal | `parsing/ajson.py` | Plugin imports |
| 36 | `ansible.parsing.yaml.objects` module removal | `parsing/yaml/objects.py` | Plugin imports |
| 37 | `listify_lookup_plugin_terms` function | `utils/listify.py` | Lookup plugin code |
| 38 | `collection_name` key in `deprecations` dict | `executor/task_executor.py` | Module return values |

---

## Plugin/collection developer-facing deprecations

These affect people writing Python plugins, modules, or collections — not playbook authors. APME could detect these in Python files within scanned collections.

### Templar API (2.23) — 11 deprecations

| Deprecated | Replacement | Source |
|------------|-------------|--------|
| `Templar._available_variables` | `Templar.available_variables` | `template/__init__.py` |
| `Templar._loader` | `copy_with_new_env` | `template/__init__.py` |
| `Templar.environment` | `copy_with_new_env` | `template/__init__.py` |
| `Templar.set_temporary_context()` | `copy_with_new_env` | `template/__init__.py` |
| `Templar.do_template()` | `Templar.template()` | `template/__init__.py` |
| `copy_with_new_env(environment_class=...)` | Removed argument | `template/__init__.py` |
| `copy_with_new_env(**overrides)` | Pass to `template()` | `template/__init__.py` |
| `template(convert_bare=...)` | `evaluate_expression()` | `template/__init__.py` |
| `template(fail_on_undefined=None)` | Pass explicit `True`/`False` | `template/__init__.py` |
| `template(convert_data=...)` | Removed argument | `template/__init__.py` |
| `template(disable_lookups=...)` | Removed argument | `template/__init__.py` |

### Module utilities (2.23)

| Deprecated | Replacement | Source |
|------------|-------------|--------|
| `AnsibleModule.jsonify()` | `json.dumps()` | `module_utils/basic.py` |
| Passing `warnings` to `exit_json`/`fail_json` | Use `module.warn()` | `module_utils/basic.py` |
| Passing `deprecations` to `exit_json`/`fail_json` | Use `module.deprecate()` | `module_utils/basic.py` |
| `ansible.parsing.utils.jsonify` | `json.dumps()` | `parsing/utils/jsonify.py` |

### Error handling (2.23)

| Deprecated | Replacement | Source |
|------------|-------------|--------|
| `suppress_extended_error` argument | `show_content=False` | `errors/__init__.py` |
| `AnsibleFilterTypeError` import | `AnsibleTypeError` | `errors/__init__.py` |
| `_AnsibleActionDone` import | Return directly | `errors/__init__.py` |

### Compatibility modules (2.23)

| Deprecated | Replacement | Source |
|------------|-------------|--------|
| `ansible.compat.importlib_resources` | `importlib.resources` | `compat/importlib_resources.py` |
| `ansible.plugins.cache.base` | `ansible.plugins.cache` | `plugins/cache/base.py` |
| Paramiko compat imports | Direct paramiko imports | `module_utils/compat/paramiko.py` (2.21) |

### Shell plugins (2.23–2.24)

| Deprecated | Replacement | Source |
|------------|-------------|--------|
| `ShellModule.checksum()` (sh) | `ActionBase._execute_remote_stat()` | `plugins/shell/sh.py` (2.23) |
| `ShellModule.checksum()` (PowerShell) | Same | `plugins/shell/powershell.py` (2.23) |
| `Shell.wrap_for_exec()` | Contact plugin author | `plugins/shell/__init__.py` (2.24) |
| `PowerShell._encode_script()` | Contact plugin author | `plugins/shell/powershell.py` (2.24) |

---

## Overlap with existing APME rules

| Deprecation | Existing rule | Notes |
|-------------|--------------|-------|
| `when: "{{ var }}"` (2.23) | **L015** (OPA) | Already implemented |
| Plugin auto-redirect (2.23) | **M001** (ansible) | Dynamic — fires when venv has the redirect |
| Module deprecation (2.23+) | **M002** (ansible) | Dynamic — fires when venv marks module deprecated |
| Module redirect (2.23+) | **M003** (ansible) | Dynamic |
| Module removed/tombstoned | **M004** (ansible) | Dynamic |

---

## Proposed new rules

Priority based on: (1) how many playbooks are affected, (2) severity of breakage, (3) feasibility of static detection.

### Priority 1 — High impact, statically detectable

| Rule | Version | Pattern | Validator |
|------|---------|---------|-----------|
| M014 | 2.24 | Top-level fact vars (`ansible_*`) → `ansible_facts["*"]` | Native |
| M015 | 2.23 | `play_hosts` magic variable → `ansible_play_batch` | Native or OPA |
| M016 | 2.23 | Empty `when:` conditional | OPA |
| M017 | 2.23 | `action:` as mapping → use string | OPA |
| M018 | 2.21 | `paramiko_ssh` connection plugin | OPA |

### Priority 2 — Medium impact

| Rule | Version | Pattern | Validator |
|------|---------|---------|-----------|
| M019 | 2.23 | `!!omap` / `!!pairs` YAML tags | Native (YAML scan) |
| M020 | 2.23 | `!vault-encrypted` tag → `!vault` | Native (YAML scan) |
| M021 | 2.23 | Empty `args:` keyword | OPA |
| M022 | 2.23 | `tree` / `oneline` callback plugins | Native (ansible.cfg scan) |
| M023 | 2.22 | `follow_redirects: yes/no` string values | OPA |
| M024 | 2.24 | `include_vars` `ignore_files` as string | OPA |
| M025 | 2.23 | Third-party strategy plugin usage | OPA |
| M026 | 2.23 | Invalid inventory variable names | Native |

### Priority 3 — Lower impact or harder to detect

| Rule | Version | Pattern | Validator |
|------|---------|---------|-----------|
| M027 | 2.23 | Legacy `k=v` merged with `args:` | Native (parser) |
| M028 | 2.23 | `first_found` auto-splitting paths | OPA |
| M029 | 2.23 | Inventory scripts missing `_meta.hostvars` | Native |
| M030 | 2.23 | Broken conditional expressions | Native (Jinja2 parse) |

### Not statically detectable (runtime only)

These cannot be detected without running the playbook:

- `bool` filter coercing invalid values (depends on runtime data)
- `from_yaml` / `from_yaml_all` on non-string input (depends on runtime data)
- Test plugin returning non-boolean (depends on plugin implementation)
- Files with invalid encoding (depends on file content)

---

## Implementation notes

### Version gating

All new rules should be **version-gated** like existing M-rules. Each rule fires only when the user's target `ansible_core_version` is >= the deprecation version. The version is available in `ValidateRequest` and `ScanContext`.

### M014 (top-level fact vars) — special considerations

This is the highest-impact rule. Virtually every Ansible playbook uses `ansible_hostname`, `ansible_os_family`, `ansible_distribution`, etc. as top-level variables. The detection needs to:

1. Build a list of known fact names from `ansible.module_utils.facts`
2. Scan all Jinja2 expressions in tasks, templates, and conditionals
3. Match `ansible_*` variable references against the known fact list
4. Exclude false positives: `ansible_play_batch`, `ansible_check_mode`, etc. (magic vars, not facts)

The fix is mechanical: `ansible_hostname` → `ansible_facts["hostname"]` (drop the `ansible_` prefix).

### Relationship to module_metadata.json

The [ANSIBLE_CORE_MIGRATION.md](/docs/ANSIBLE_CORE_MIGRATION.md) roadmap mentions `module_metadata.json` for data-driven M-rules. The deprecation patterns in this research should feed into that metadata file, enabling rules to be added by updating data rather than writing new code for each deprecation.

---

## Remediation analysis

Per ADR-009, validators are read-only — remediation is a separate engine. Each proposed rule is classified by fix tier:

- **Tier 1 (auto-fix)**: Mechanical text substitution; the remediation engine can apply the fix without human review.
- **Tier 2 (AI-assisted)**: Pattern is detectable but the fix requires context or judgment; LLM proposes a patch, human reviews.
- **Tier 3 (manual)**: Detection only; no automated fix is feasible.

### Priority 1

| Rule | Pattern | Fix tier | Remediation approach |
|------|---------|----------|---------------------|
| M014 | `ansible_hostname` → `ansible_facts["hostname"]` | **Tier 1** | Regex substitution: `ansible_FACTNAME` → `ansible_facts["FACTNAME"]` in Jinja2 expressions. Requires a known-facts allowlist to avoid false positives on magic vars (`ansible_check_mode`, `ansible_play_batch`, etc.). Highest ROI rule — every playbook benefits. |
| M015 | `play_hosts` → `ansible_play_batch` | **Tier 1** | Simple string replacement in Jinja2 expressions. No ambiguity. |
| M016 | Empty `when:` conditional | **Tier 1** | Remove the `when:` key entirely (empty conditional was always True). |
| M017 | `action: {module: copy, src: a}` → `action: copy src=a` | **Tier 2** | Mapping → string conversion requires understanding of freeform vs structured args per module. Safe for simple cases, AI review for complex ones. |
| M018 | `connection: paramiko_ssh` → `connection: ssh` | **Tier 1** | Direct substitution. May need user review if paramiko was chosen deliberately for compatibility. |

### Priority 2

| Rule | Pattern | Fix tier | Remediation approach |
|------|---------|----------|---------------------|
| M019 | `!!omap` / `!!pairs` tags | **Tier 1** | Remove the tag; standard YAML mappings preserve insertion order since Python 3.7+. |
| M020 | `!vault-encrypted` → `!vault` | **Tier 1** | Direct tag substitution. |
| M021 | Empty `args:` | **Tier 1** | Remove the empty `args:` key. |
| M022 | `stdout_callback = tree` or `oneline` | **Tier 3** | No drop-in replacement — user must choose an alternative callback. Detection + informational message only. |
| M023 | `follow_redirects: yes` → `true` | **Tier 1** | String → boolean substitution. |
| M024 | `ignore_files: "*.bak"` → `ignore_files: ["*.bak"]` | **Tier 1** | Wrap string value in a YAML list. |
| M025 | Third-party strategy plugin | **Tier 3** | No replacement exists — informational warning only. |
| M026 | Invalid inventory variable names | **Tier 2** | Rename is mechanical but may break references elsewhere. AI review for impact. |

### Priority 3

| Rule | Pattern | Fix tier | Remediation approach |
|------|---------|----------|---------------------|
| M027 | Legacy `k=v` merged with `args:` | **Tier 2** | Move k=v params into `args:` mapping. Requires understanding module parameter structure. |
| M028 | `first_found` auto-splitting | **Tier 1** | Split the string term into a YAML list on the delimiter. |
| M029 | Inventory script missing `_meta` | **Tier 3** | Requires modifying external scripts — outside APME's scope. Informational only. |
| M030 | Broken conditional expressions | **Tier 2** | Depends on the specific breakage — AI review needed to determine intent. |

### Summary

| Tier | Count | Percentage |
|------|-------|------------|
| Tier 1 (auto-fix) | 10 | 59% |
| Tier 2 (AI-assisted) | 4 | 24% |
| Tier 3 (manual/informational) | 3 | 17% |

**10 of 17 proposed rules have fully mechanical fixes** — the remediation engine can apply them without human review. M014 (top-level fact vars) alone would modernize virtually every playbook in existence.

---

## References

- [ANSIBLE_CORE_MIGRATION.md](/docs/ANSIBLE_CORE_MIGRATION.md) — existing 2.19/2.20 migration rules
- [ansible-core changelogs](https://github.com/ansible/ansible/tree/devel/changelogs) — porting guides and version-specific changes
- ansible-core source: `lib/ansible/` on `devel` branch
- ADR-008: Rule ID conventions (M = modernization)
