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

- Fixture parameterization on a test level.

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

*	Test parameterization is done by using a new **test_case** marker as follows:

	.. literalinclude:: ../tests/test_parametrize.py
		:language: python
		:lines: 5-45
		:emphasize-lines: 18-30

	*	Output:
	
	.. code-block:: shell
		
    		first_fixture_place_holder: 100
    		second_fixture_place_holder: Hello World
    		third_fixture_place_holder: I am not parametrized
    		test_param: 1.04
    		PASSED
    		====================================== test_fixture_param_persistency finished ======================================

	Another test can benefit from privious parameterization if defined in the same scope, i.e.:
	
	.. literalinclude:: ../tests/test_parametrize.py
		:language: python
		:lines: 47-51
		:emphasize-lines: 1

	*	Output:
	
	.. code-block:: bash
		
    		fixture_place_holder param: Hello World
    		PASSED
    		====================================== test_fixture_param_persistency finished ======================================

*	Test scenario is represented by a JSON file located at:
	
	.. code-block:: shell
	
 		<projects_root>/sut/scenarios/<scenario_name>.json
	Below is an example for a scenario named **"main scenario"**:

	.. literalinclude:: ../sut/scenarios/main scenario.json
		:language: json
	
	**"main scenario"** is referencing a second scenario named **"sub scenario"** (Nesting is supported):

	.. literalinclude:: ../sut/scenarios/sub scenario.json
		:language: json
	
	*	Invocation of a test scenario would be done as follows:

	.. code-block:: shell
		
		~/workspace/projects_root$ py.test tests/ --scenario="main scenario"
	
	*	Output:
	
	.. code-block:: shell

    		collected 3 items 
    		selected scenario: 
    		                 _                                       _       
    		 _ __ ___   __ _(_)_ __    ___  ___ ___ _ __   __ _ _ __(_) ___  
    		| `_ ` _ \ / _` | | `_ \  / __|/ __/ _ \ `_ \ / _` | `__| |/ _ \ 
    		| | | | | | (_| | | | | | \__ \ (_|  __/ | | | (_| | |  | | (_) |
    		|_| |_| |_|\__,_|_|_| |_| |___/\___\___|_| |_|\__,_|_|  |_|\___/ 
                                                                 

    		tests/test_parametrize.py::TestParametrize::test_scenario_instantiation[main scenario-1] 
    		
    		Hello World
    		PASSED
    		=============================== test_scenario_instantiation[main scenario-1] finished ===============================
    		    		
    		
    		tests/test_parametrize.py::TestParametrize::test_scenario_instantiation[main scenario-2/sub scenario-1] 
    		
    		Hello Bob
    		PASSED
    		======================= test_scenario_instantiation[main scenario-2/sub scenario-1] finished ========================
    		
    		
    		tests/test_parametrize.py::TestParametrize::test_scenario_instantiation[main scenario-2/sub scenario-2] 
    		
    		Bye Bob
    		PASSED
    		======================= test_scenario_instantiation[main scenario-2/sub scenario-2] finished ========================

License
-------

.. raw:: html
	
   
	The project is licensed under the  <span><a href="http://www.wtfpl.net/"><img
		       src="http://www.wtfpl.net/wp-content/uploads/2012/12/wtfpl-badge-1.png"
		       width="80" height="15" alt="WTFPL" /></a></span>  license.
