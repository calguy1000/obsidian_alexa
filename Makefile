NCONTAINERS := $(shell docker ps | grep alexa-skill-dev | wc -l)

shell: run
	docker exec -it --user worker alexa-skill-dev bash --login

root: run
	docker exec run -it alexa-skill-dev bash --login

build:
	docker compose build

run:
ifeq ($(NCONTAINERS), 0)
	docker compose up -d
endif

deploy:
	docker compose exec -it --user worker alexa-skill-dev ask deploy

dialog: run
	docker compose exec -it --user worker alexa-skill-dev ask dialog --locale en-US

down stop:
	docker compose down

clean: stop
	docker compose down
	_list=`docker ps -a | grep alexa-skill-dev | grep Exited | cut -d ' ' -f1`
	if [ "$$_list" != "" ]; then docker rm $_list; fi

rebuild: clean build

help:
    @echo "shell: Run a shell in the container"
    @echo "root: Run a root shell in the container"
    @echo "build: Build the container" 
    @echo "rebuild: Clean up the container and rebuild it"
    @echo "run: Run the skill locally, for debugging"
    @echo "deploy: Deploy the skill"
    @echo "stop: Stop the container"
    @echo "dialog: Test the skill using the interactive dialog tool"
    @echo "clean: Clean up the container"
    @echo "help: Show this help message"


