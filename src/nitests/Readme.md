# nitests
This is the test package for our Project.

## Structure

- src contains all the test suits mirroring the structure of the project. Should be used as test root
- resources contains all test files for the tests
- config contains global configuration for all tests as well as config files for single tests
- util contains test helper code that can be utitlized by all tests
- tmp a tempdir for all statically configured paths. cleared before session start


## Setting up test environment
- create copy `nitests/jsonfiles/backend.example.json` called `backend.json` and change the `SQLite_path` to the corresponding absolute path

## Run tests
- it is recommended to use pytest, but unittest should work as well
- use src as root for tests


## Creating new tests

1. if not already existing, create a mirror directory of the module you want to test
2. Create a file called test_<to_be_tested>.py
3. Create a class Test<ToBeTested> (unittest.TestCase)
4. create methods def test_<to_be_tested>(self)

## Notes

- Make sure that no import statements throw exceptions or gobble up to much runtime! The collection step might fail
  then.
