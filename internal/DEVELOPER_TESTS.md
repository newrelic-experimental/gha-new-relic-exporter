# Developer Note: Running Tests


To run unit tests for the exporter, make sure you have your Python virtual environment activated and all dependencies installed:

```
python -m unittest src/custom_parser/test_attributes_unit.py
python -m unittest src/custom_parser/test_attributes_integration.py
```

You can run all tests at once with:
```
python -m unittest discover src/custom_parser
```

Ensure you have installed all required packages from `requirements.txt` before running tests:
```
pip install -r requirements.txt
```
