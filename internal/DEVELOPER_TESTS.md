# Developer Note: Running Tests

## Environment Setup
1. Always activate your Python virtual environment before running any tests:
	```
	source venv/bin/activate
	```
2. Upgrade pip and install all dependencies:
	```
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	```


## Running Tests
Run individual unit and integration tests:
```
python -m unittest tests/test_attributes_unit.py
python -m unittest tests/test_attributes_integration.py
python -m unittest tests/test_sanitize_filename.py
python -m unittest tests/test_exporter_integration.py
```

Run all tests at once (recommended):
```
python -m unittest discover tests
```

## Test Organization
- All tests should be placed in the `tests/` folder.

## Notes
- Ensure all required environment variables are set or mocked for integration tests.
- All commands above assume you are inside your venv and using the correct Python interpreter.
