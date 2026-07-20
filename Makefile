IMAGE ?= your-registry.example.com/visionone-bank-demo
TAG ?= 1.0.0
RELEASE ?= visionone-bank-demo
NAMESPACE ?= visionone-demo

.PHONY: inventory preflight run build push install upgrade uninstall lint test package
inventory:
	./scripts/cluster-inventory.sh
preflight:
	./scripts/preflight-check.sh
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
build:
	docker build -t $(IMAGE):$(TAG) .
push:
	docker push $(IMAGE):$(TAG)
install:
	helm upgrade --install $(RELEASE) ./helm/visionone-bank-demo -n $(NAMESPACE) --create-namespace --set image.repository=$(IMAGE) --set image.tag=$(TAG)
upgrade: install
uninstall:
	helm uninstall $(RELEASE) -n $(NAMESPACE)
lint:
	ruff check app tests
	test -f helm/visionone-bank-demo/Chart.yaml
	test -f helm/visionone-bank-demo/values.yaml
test:
	python -m pytest -q
package:
	cd .. && zip -r visionone-bank-demo.zip visionone-bank-demo -x '*/__pycache__/*' '*.pyc' '*.zip'
