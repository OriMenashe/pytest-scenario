.. |project| replace:: pytest-scenario
.. |author| replace:: OriMenashe
.. raw:: html

		<a href="https://github.com/OriMenashe"><img style="position: fixed; top: 0; right: 0; border: 0;" src="https://camo.githubusercontent.com/365986a132ccd6a44c23a9169022c0b5c890c387/68747470733a2f2f73332e616d617a6f6e6177732e636f6d2f6769746875622f726962626f6e732f666f726b6d655f72696768745f7265645f6161303030302e706e67" alt="Fork me on GitHub" data-canonical-src="https://s3.amazonaws.com/github/ribbons/forkme_right_red_aa0000.png"></a>

|project|: parameterized test case instances and test scenarios.
====================================================================

|project| is a *pytest* plugin that aims to extend current test parameterization  capabilities.
After installing |project| you will be able run a test suite constructed from a JSON formatted test plan (AKA Test Scenario).

**Note**:
pytest-scenario is currently classified as *alpha*, feel free to contact me with any issue at: https://github.com/OriMenashe


Features
--------

- Test parameterization (including fixtures and test arguments).

- Test instantiation - run multiple test instances with different parameters.
 
- Test ordering - running tests in a thoughtful, user-defined order.

- Test exclusion - excluding unwanted tests during collection stage.
 

Installation
------------

Install |project| by running:

.. code-block:: shell

    pip install pytest-scenario
	
Quickstart
----------

- Test parameterization is done by using a new **test_case** marker as follows:

.. code-block:: python
   
   @pytest.fixture
   def db1(request):
       # connect to db1 database server...
       return db1

   @pytest.fixture
   def db2(request):
       # connect to db2 database server...
       return db2
   
   class TestDBIntegrity:
   
       @pytest.mark.test_case(fixture_binding=[('db', 'db1', 'session')], params=[('table', 'USERS'), ('field_name', 'user_name'), ('field_value', 'orim')])
       def test_value_exists(self, db, table, field_name, field_value):
              # Query USERS table inside db1 for a user named orim.
              assert db.query("SELECT * from {} WHERE '{}'=={};").format(table, field_name, field_value)

- Test scenario is a JSON file located at the root of your project at <projects_root>/sut/scenarios/**<scenario_name>.json** :


.. code-block:: json
	
	[
	    {
	        "id": 1,
	        "module_name": "tests.db_tests",
	        "class_name": "TestDBIntegrity",
	        "test_name": "test_value_exists",
	        "fixture_binding": {
	            "db": [
	                "db1",
	                "session"
	            ]
	        },
	        "params": {
	            "table": "USERS",
	            "field_name": "user_name",
	            "field_value": "orim"
	        },
	        "skip": false,
	        "xfail": false
	    },
	    {
	        "id": 2,
	        "module_name": "tests.db_tests",
	        "class_name": "TestDBIntegrity",
	        "test_name": "test_value_exists",
	        "fixture_binding": {
	            "db": [
	                "db2",
	                "session"
	            ]
	        },
	        "params": {
	            "table": "USERS",
	            "field_name": "user_name",
	            "field_value": "miked"
	        },
	        "skip": false,
	        "xfail": false
	    },
	]
	
Invocation of a test scenario will be done as follows:

.. code-block:: shell

	~/workspace/projects_root$ py.test tests/ --scenario=<scenario_name>

License
-------

.. raw:: html
	
   
	The project is licensed under the  <span><a href="http://www.wtfpl.net/"><img
		       src="http://www.wtfpl.net/wp-content/uploads/2012/12/wtfpl-badge-1.png"
		       width="80" height="15" alt="WTFPL" /></a></span>  license.
