---
rule_id: L075
validator: native
description: Templates should include ansible_managed comment.
scope: role
---

## Ansible managed (L075)

Templates should include `{{ ansible_managed | comment }}` at the top and use `.j2` extension.

### Example: violation

```yaml
- name: Deploy config
  ansible.builtin.template:
    src: app.conf
    dest: /etc/app.conf
```

### Example: pass

```yaml
- name: Deploy config
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/app.conf
```
