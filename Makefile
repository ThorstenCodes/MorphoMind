build:
	@docker build -t $(IMAGE_NAME) demo/

run:
	@docker run -v "$(pwd)":/app -p 8080:8080 -e PORT=8080 test
