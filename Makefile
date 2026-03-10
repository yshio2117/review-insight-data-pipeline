IMAGE_NAME := review-pipeline

# used to generate a consistent reason_id for identical review texts across different pipeline runs.
TEST_UUID := 7f1736ae-e013-402b-85e2-36b72055058d

.PHONY: all build run clean
all: build run

# build the docker image
build:
	@echo "=> Building the Docker image for the review analysis pipeline..."
	docker build -t $(IMAGE_NAME) .

# run the pipeline in local mode
run:
	@echo "=> Running the pipeline in local mode..."
	@echo "   (using UUID: $(TEST_UUID))"
	docker run --rm \
		-e UUID_STRING="$(TEST_UUID)" \
		-v "$(PWD)/data/output:/app/data/output" \
		$(IMAGE_NAME)
	@echo "=> Pipeline execution completed. Check the output in ./data/output/ folder on your PC."

# clean the output directory
clean:
	@echo "=> Cleaning the output directory..."
	rm -f data/output/*.csv
	@echo "=> Cleaning completed."