install:
	./setup.py install
dev:
	./setup.py develop
test:
	pip install -r requirements.txt -q
	pip install -r dev-requirements.txt -q
	./run_tests.sh
