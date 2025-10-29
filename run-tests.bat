@echo off
REM Windows batch script to run core tests

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing test dependencies...
python -m pip install pytest pytest-asyncio responses beautifulsoup4

echo Running core MCP server tests...
python -m pytest tests/test_models.py tests/test_utils.py tests/test_errors.py tests/test_project_analyzer.py tests/test_package_manager.py tests/test_server.py tests/test_integration.py -v

echo.
echo Core test run complete!
echo.
echo To run all tests including migration features:
echo python -m pytest tests/ -v
echo.
pause