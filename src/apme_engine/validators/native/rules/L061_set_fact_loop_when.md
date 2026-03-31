---
rule_id: L061
validator: native
description: set_fact with loop and when is a scaling anti-pattern.
---

## set_fact + loop + when anti-pattern (L061)

Using `set_fact` inside a `loop` (or `with_*`) with a `when` conditional to
build a filtered subset of a data structure forces Ansible to evaluate the task
once per loop item — O(n) task invocations.  A single Jinja2 filter expression
(`selectattr`, `select`, `reject`, etc.) achieves the same result in one pass.

### Example: violation

```yaml
- name: Filter running services
  ansible.builtin.set_fact:
    running_services: "{{ running_services | default([]) + [item] }}"
  loop: "{{ all_services }}"
  when: item.state == 'running'
```

### Example: pass

```yaml
- name: Filter running services
  ansible.builtin.set_fact:
    running_services: "{{ all_services | selectattr('state', 'equalto', 'running') | list }}"
```
