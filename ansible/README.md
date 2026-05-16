# Ansible automation

This folder provides playbooks to automate:
- Docker + Docker Compose setup
- Docker Swarm init/join + stack deploy
- Kubernetes via k3s (server/agent) + manifest deploy

## Quick start

```bash
cd ansible
ansible-playbook -i inventories/example/hosts.ini playbooks/docker-compose.yml
```

Tip (faster, recommended): set `repo_git_url` in `group_vars/all.yml` to your GitHub repo URL so the playbook deploys via `git clone` instead of copying the whole folder.

## Inventory groups

`inventories/example/hosts.ini` defines:
- `docker_hosts`: install Docker/Compose and run `docker compose up`
- `swarm_manager`, `swarm_workers`: Swarm cluster + `docker stack deploy`
- `k3s_server`, `k3s_agents`: k3s cluster + `kubectl apply -k`

Update IPs/users/SSH keys before running.
