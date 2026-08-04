ANSIBLE_PLAYBOOK = ansible-playbook

.PHONY: help
help: ## Display help message
	@grep -E '^[0-9a-zA-Z_-]+\.*[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## Generate EOS intended configurations and documentation
	$(ANSIBLE_PLAYBOOK) playbooks/dc1-fabric-deploy-cvp.yml --tags build

.PHONY: provision
provision: ## Push configlets and containers to CVP (no task execution)
	$(ANSIBLE_PLAYBOOK) playbooks/dc1-fabric-deploy-cvp.yml --tags provision

.PHONY: deploy
deploy: ## Full deploy: build + provision + execute tasks on CVP
	$(ANSIBLE_PLAYBOOK) playbooks/dc1-fabric-deploy-cvp.yml --extra-vars "execute_tasks=true" --tags "build,provision,apply"

.PHONY: validate
validate: ## Run ANTA fabric validation via AVD
	$(ANSIBLE_PLAYBOOK) playbooks/dc1-validate-state.yml

.PHONY: reset
reset: ## Reset fabric on CVP (remove configlets/containers)
	$(ANSIBLE_PLAYBOOK) playbooks/dc1-fabric-reset-cvp.yml
