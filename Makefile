command_prefix = poetry run


.PHONY: docs test readme

package:
	@poetry build

test:
	@$(command_prefix) py.test

docs:
	@$(command_prefix) sphinx-build docs docs/build

readme:
	@$(command_prefix) sphinx-build -M markdown docs docs/build
	@cp docs/build/markdown/README.md .

	@echo
	@echo Generated README.md copied to the project root
