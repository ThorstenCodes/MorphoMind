init:
	@direnv allow .
	@echo "direnv is now allowed for this directory"
	@pip install -e .
	@echo "Python package is now installed"
