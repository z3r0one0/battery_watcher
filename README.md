# Battery Watcher

A simple Windows application that monitors battery status and sends notifications when the battery is low or fully charged.

## Features

- Monitors battery percentage and charging status
- Sends notifications when battery is low and not charging
- Sends notifications when battery is full and still charging
- Prevents system from sleeping during notifications
- Designed with testability in mind

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the battery watcher script:

```
python battery_watcher.py
```

Or use the batch file:

```
start_battery_monitor.bat
```

## Code Design

The battery watcher script is designed with testability in mind:

1. **Lazy Initialization**: WMI connections are initialized only when needed
2. **Test Mode**: The main function accepts a `test_mode` parameter that allows tests to run without actual delays
3. **Iteration Control**: Tests can specify the number of loop iterations to run
4. **Clear Function Responsibilities**: Each function has a single responsibility
5. **Improved Error Handling**: All exceptions are properly caught and handled

## Testing

This project uses pytest for testing. The tests demonstrate several important testing concepts:

1. **Mocking external dependencies**: The tests mock WMI, notifications, and system calls to avoid actual side effects during testing.
2. **Fixtures**: Reusable test components that set up the testing environment.
3. **Test organization**: Tests are organized into classes by functionality.
4. **Exception handling**: Tests verify that the code properly handles exceptions.
5. **Code coverage**: The tests achieve 95% code coverage.

### Running the tests

To run the tests:

```
pytest
```

To run tests with verbose output:

```
pytest -v
```

To run tests with coverage report:

```
pytest --cov=battery_watcher
```

## Test Coverage

The current test suite achieves 95% code coverage. The only lines not covered are related to time.sleep() calls in non-test mode, which are intentionally skipped during testing to make tests run faster. 