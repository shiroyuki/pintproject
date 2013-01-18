package:
	python setup.py sdist

test: clean
	cd test && python test.py
	cd test && python3 test.py

clean:
	find . -name .DS_Store -exec rm {} \;
	find . -name ._* -exec rm {} \;
	find . -name *.pyc -exec rm {} \;
	find . -name __pycache__ -exec rm -Rf {} \;
