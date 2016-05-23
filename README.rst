.. |project| replace:: pytest-scenario
.. |author| replace:: OriMenashe

|project|: parameterized test case instances and test scenarios.
====================================================================

|project| is a *pytest* plugin that aims to extend current test parameterization  capabilities.
After installing |project| you will be able run a test suite constructed from a JSON formatted test plan (AKA Test Scenario).

**Note**:
pytest-scenario is currently classified as *alpha*, feel free to contact me with any issue at: https://github.com/OriMenashe


Features
--------

- Test parameterization (including fixtures and test arguments).

- Fixture parameterization on a test level.

- Test instantiation - run multiple test instances with different parameters.
 
- Test ordering - running tests in a thoughtful, user-defined order.

- Test exclusion - excluding unwanted tests during collection stage.
 

Installation
------------

Install |project| by running:

.. code-block:: shell

    pip install pytest-scenario
	
Documentation
-------------

A quick start guide can be found `here`_.

.. _here: http://pytest-scenario.readthedocs.io/en/latest/#quickstart


License
-------

The project is licensed under the WTFPL license.
