.PHONY: env install layers soft_link

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo ""
	@echo "Please use 'make <target>' where <target> is one of"
	@echo "  install     create virtual environment and install packages"
	@echo "  layers      prepare lambda layers for 'python'"
	@echo "  soft_link   create soft link lambda_layer python to venv"
	@echo "  clean       remove all temporary files"
	@echo ""
	@echo "Check the Makefile to know exactly what each target is doing."



VENV_NAME?=.venv
PYTHON_EXECUTABLE_VERSION=python3.8
PYTHON=${VENV_NAME}/bin/python

LAYER_FOLDER=lambda_layer
PYTHON_LAYER_FOLDER=${LAYER_FOLDER}/python

env: $(VENV_NAME)/bin/activate

$(VENV_NAME)/bin/activate: requirements.txt
	test -d $(VENV_NAME) || virtualenv -p ${PYTHON_EXECUTABLE_VERSION} $(VENV_NAME) || ${PYTHON_EXECUTABLE_VERSION} -m venv $(VENV_NAME)

install: env
	${PYTHON} -m pip install -U pip
	${PYTHON} -m pip install -r requirements.txt

layers: env
	${PYTHON} -m pip install -t $(PYTHON_LAYER_FOLDER)/lib/python3.8/site-packages -r $(PYTHON_LAYER_FOLDER)/requirements.txt

SHELL := /bin/bash
CWD := $(shell cd -P -- '$(shell dirname -- "$0")' && pwd -P)
SOURCE_DIR = ${CWD}/${PYTHON_LAYER_FOLDER}/*
DESTINATION_DIR = ${CWD}/${VENV_NAME}/lib/${PYTHON_EXECUTABLE_VERSION}/site-packages

cwd:
	# @echo ${CWD}
	# @echo ${SOURCE_DIR}
	# @echo ${DESTINATION_DIR}
	# @echo 'ln -s ${SOURCE_DIR} ${DESTINATION_DIR}'

soft_link: install
	ln -s ${SOURCE_DIR} ${DESTINATION_DIR}


clean:
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf ${VENV_NAME}
	rm -rf $(PYTHON_LAYER_FOLDER)/lib