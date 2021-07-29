.PHONY: clean
build:
	python3 setup.py sdist bdist_wheel

.PHONY: clean
clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

publish: clean build
	twine upload dist/*