# fetch-backend

![lint](https://github.com/Fyssion/fetch-backend/actions/workflows/lint.yml/badge.svg)
![test](https://github.com/Fyssion/fetch-backend/actions/workflows/test.yml/badge.svg)

-----

## Table of Contents

- [Installation](#installation)
- [Running](#running)
- [License](#license)

## Installation

> [!IMPORTANT]
> Before installing the project, please ensure you have [Python 3.12+][python]
> installed. You can download Python from [their official site][python-dl].

First, install the project requirements. The below command installs
requirements for the test suite as well, but if you just want to run
the app, you can just install `requirements.txt`.

```sh
# Windows
py -m pip install requirements/requirements-test.txt

# MacOS/Linux
python3 -m pip install requirements/requirements-test.txt
```

## Running

To run the app, simply invoke the following:

```sh
# Windows
py fetch_backend.py

# MacOS/Linux
python3 fetch_backend.py
```

### Tests

> [!NOTE]
> Test suite status can be seen in the badge at the top of this README.

To run the test suite:

```sh
# Windows
py -m pytest

# MacOS/Linux
python3 -m pytest
```

## License

`fetch-backend` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

[python]: https://www.python.org/
[python-dl]: https://www.python.org/downloads
