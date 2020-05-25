command_prefix = poetry run


.PHONY: docs test readme

package:
	@poetry build

test:
	@$(command_prefix) py.test

docs:
	@$(command_prefix) sphinx-build docs docs/build

readme:
	@$(command_prefix) sphinx-build -M rst docs docs/build
	@cp docs/build/rst/README.rst .

	@echo
	@echo Generated README.rst has been copied to the project root
