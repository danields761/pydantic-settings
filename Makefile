project_name = $(shell grep -Po '(?<=name = )"([\w-]+)"' pyproject.toml | tr -d '"')
poetry_cmd=poetry
CMD_PREFIX ?= ${poetry_cmd} run
build_artifact_name=dist/build.whl
lint_targets = $(shell echo $(project_name) | tr '-' '_') test
WHEEL_NAME_FILE ?= dist/wheel_name.txt

.PHONY: test docs

## Install dependencies
install-deps:
	@${poetry_cmd} install
	@echo Development dependencies installed

## Check code-style
lint:
	@${CMD_PREFIX} flake8 ${lint_targets}
	@${CMD_PREFIX} isort --check ${lint_targets}
	@${CMD_PREFIX} black --check ${lint_targets}

lint-readme:
	@{ \
  		${CMD_PREFIX} sphinx-build -M rst docs docs/build > /dev/null 2>&1; \
		if ! diff docs/build/rst/README.rst README.rst; then \
		  echo 'README.md is not up to date, invoke "make readme"'; exit 1; \
	  	fi; \
	}

## Coerce code-style
fmt:
	@${CMD_PREFIX} isort ${lint_targets}
	@${CMD_PREFIX} black ${lint_targets}

## Run unit-tests
test:
	@${CMD_PREFIX} pytest test

## Build project into wheel, place it under "dist" folder (may be altered via $DIST_DST).
## Wheel filename can be read from "dist/wheel_name.txt"
build: 
	@{ \
		set -e; \
		tmp_file=$$(mktemp); \
		${poetry_cmd} build -f wheel | tee $$tmp_file; \
		wheel_name=$$(cat $$tmp_file | grep -P -o '$(project_name)[-\d\w.]+'); \
		echo Wheel "$$wheel_name" succesfully built; \
		echo Writing wheel name into ${WHEEL_NAME_FILE}; \
		echo $$(pwd)/dist/$$wheel_name > ${WHEEL_NAME_FILE}; \
	}

## Build project docs
docs:
	@${CMD_PREFIX} sphinx-build docs docs/build

## Generate README
readme:
	@${CMD_PREFIX} sphinx-build -M rst docs docs/build
	@cp docs/build/rst/README.rst .

	@echo
	@echo Generated README.rst has been copied to the project root
