__author__ = "orim"
import re
import pytest
import json
import inspect
from attrdict import AttrDict
from pyfiglet import figlet_format
from pytest_scenario.exceptions import ImproperlyConfigured
from os.path import abspath


TEST_SCENARIOS_DIR = './sut/scenarios'

def pytest_addoption(parser):
    parser.addoption("--scenario", action="store", dest='scenario_name', metavar='name',
                     help="states the scenario that should be tested")


def pytest_configure(config):
    if config.pluginmanager.hasplugin('scenario') and config.option.scenario_name:
        scenario_name = config.option.scenario_name

        config._scenario = TestScenarioRunner(scenario_name)
        config.pluginmanager.register(config._scenario, name=scenario_name)
    else:
        # Register "test_case" markers.
        config_line = (
            'test_case: test case description',
        )
        config.addinivalue_line('markers', config_line)
        config._scenario = TestCaseRunner()
        config.pluginmanager.register(config._scenario, name='test_case_runner')


def pytest_unconfigure(config):
    scenario = getattr(config, '_scenario', None)
    if scenario:
        del config._scenario
        config.pluginmanager.unregister(scenario)


class BaseRunner(object):

    test_arg_fixture_binding_dict = {}
    item_setup_dict = {}

    def __init__(self):
        self.tw = None

    def pytest_generate_tests(self, metafunc):
        raise NotImplementedError()

    def pytest_collection_modifyitems(self, config, items):
        for item in items:
            try:
                if not item.get_marker('skipif'):
                    fully_qualified_name = '.'.join([item.module.__name__, item.cls.__name__, item.name])
                    fixture_binding_dict = self.test_arg_fixture_binding_dict[fully_qualified_name]
                    for argname, fixture_config in fixture_binding_dict.items():
                        func, _, fixture_params = fixture_config
                        _, arg2fixturedefs = item.session._fixturemanager.getfixtureclosure([func], item)
                        if fixture_params:
                            item._request._pyfuncitem.callspec.params[func] = AttrDict(fixture_params)
                        item._fixtureinfo.name2fixturedefs[func] = arg2fixturedefs[func]
                        if argname in item.fixturenames:
                            self.item_setup_dict[item.nodeid] = item
            except KeyError:
                pass

    def pytest_runtest_logstart(self, nodeid, location):
        try:
            item = self.item_setup_dict[nodeid]
        except KeyError:
            return
        try:
            fully_qualified_name = '.'.join([item.module.__name__, item.cls.__name__, item.name])
            fixture_binding_dict = self.test_arg_fixture_binding_dict[fully_qualified_name]
            for argname, fixture_config in fixture_binding_dict.items():
                func, scope, _ = fixture_config
                _, arg2fixturedefs = item.session._fixturemanager.getfixtureclosure([func], item)
                fixture_def = arg2fixturedefs[func][0]
                if scope and fixture_def.scope != scope:
                    fixture_def.finish()
                    fixture_def.scope = scope
                try:
                    item.funcargs[argname] = item._request.getfuncargvalue(func)
                except AttributeError as e:
                    raise ImproperlyConfigured(', '.join([item.name, str(e)])) from None
        except KeyError as e:
            raise RuntimeError("unable to find a fixture function named {}".format(e))

    def pytest_collection_finish(self, session):
        self.tw = session.config.pluginmanager.getplugin('terminalreporter')._tw

    def pytest_runtest_teardown(self, item, nextitem):
        self.tw.write('\n')
        self.tw.sep("=", "{} {}".format(item.name, 'skipped' if item.get_marker('skipif') else 'finished'))
        self.tw.write('\n')


class TestCaseRunner(BaseRunner):

    id_counter = 0

    def pytest_generate_tests(self, metafunc):
        fully_qualified_name = '.'.join([metafunc.module.__name__, metafunc.cls.__name__, metafunc.function.__name__])
        if hasattr(metafunc.function, "test_case"):
            self.id_counter += 1
            argnames = []
            values = []
            try:
                test_params = metafunc.function.test_case.kwargs['test_params']
                for argname, _ in test_params:
                    if argname in metafunc.fixturenames:
                        argnames.append(argname)
                    else:
                        raise ImproperlyConfigured(
                            "'{}' is not a valid argument for {}".format(argname, fully_qualified_name))
                values = [argvalue for _, argvalue in test_params]
            except KeyError:
                pass
            try:
                fixture_binding = metafunc.function.test_case.kwargs['fixture_binding']
                instance_id = '%s[%d]' % (fully_qualified_name, self.id_counter)
                try:
                    for argname, fixture_config in fixture_binding:
                        try:
                            func = fixture_config['func']
                            scope = fixture_config.get('scope', None)
                            params = fixture_config.get('params', None)
                        except KeyError as e:
                            raise ImproperlyConfigured(
                                "missing '{}' key in while trying to bind a fixture to test param: "
                                "(test_param, {func='your fixture', scope='function \ class \ module \ session'})"
                                .format(e))
                        try:
                            self.test_arg_fixture_binding_dict[instance_id][argname] = (func, scope, params)
                        except KeyError:
                            self.test_arg_fixture_binding_dict[instance_id] = {}
                            self.test_arg_fixture_binding_dict[instance_id][argname] = (func, scope, params)
                        if argname in metafunc.fixturenames:
                            values.insert(0, func)
                            if argname not in argnames:
                                argnames.insert(0, argname)
                        else:
                            raise ImproperlyConfigured(
                                "'{}' is not a valid argument for {}".format(argname, fully_qualified_name))
                except ValueError:
                    raise ImproperlyConfigured(
                        "\n{} - fixture_binding attribute should be a tuple containing at least 3 elements: "
                        "(argname, fixture, scope, params=None)".format(fully_qualified_name))
            except KeyError:
                pass
            metafunc.parametrize(argnames, [values], ids=[self.id_counter], scope="function")


class TestScenarioRunner(BaseRunner):

    def __init__(self, scenario_name: str):
        BaseRunner.__init__(self)
        self._name = scenario_name
        self.tests_dict, _ = self.generate_test_plan(scenario_name)

    def generate_test_plan(self, scenario_name, parent_ref='', order=0):
        tests_dict = {}
        scenario_file_path = '{}/{}.json'.format(TEST_SCENARIOS_DIR, scenario_name)
        try:
            with open(scenario_file_path) as scenario_file:
                scenario_config = json.load(scenario_file)
        except FileNotFoundError:
            raise RuntimeError("'{}' scenario is not defined (make sure {} is present)"
                               .format(scenario_name, abspath(scenario_file_path)))
        id_counter = set()
        for test_instance in scenario_config:
            assert "id" in test_instance,\
                "test case record in scenario '{}' is missing an id field.".format(scenario_name)
            test_id = '-'.join([scenario_name, str(test_instance["id"])])
            if parent_ref:
                test_id = '/'.join([parent_ref, test_id])
            assert test_id not in id_counter,\
                "found a duplicate test id {} in scenario '{}'".format(test_instance["id"], scenario_name)
            id_counter.add(test_id)
            if test_instance.get('@ref', None):
                sub_scenario_tests, order = self.generate_test_plan(test_instance['@ref'], test_id, order)
                tests_dict.update(sub_scenario_tests)
            else:
                assert "test_name" in test_instance,\
                    "test case record in scenario '{}' is missing a test_name field.".format(scenario_name)
                test_instance["id"] = test_id
                order += 1
                test_instance["order"] = order
                tests_dict.update({'%s.%s.%s[%s]' % (test_instance["module_name"],
                                                     test_instance["class_name"],
                                                     test_instance["test_name"],
                                                     test_id): test_instance})
        return tests_dict, order

    def pytest_pycollect_makeitem(self, collector, name, obj):
        tests_dict = self.tests_dict
        if inspect.isfunction(obj) and name.startswith("test_") and isinstance(collector, pytest.Instance):
            fully_qualified_name = '.'.join([obj.__module__, obj.__qualname__])
            for test_id in tests_dict.keys():
                if fully_qualified_name == re.sub('\[.*?\]$', '', test_id):
                    return
            return []

    def pytest_collection_modifyitems(self, config, items):
        grouped_items = {}
        for item in items:
            fully_qualified_name = '.'.join([item.module.__name__, item.cls.__name__, item.name])
            try:
                test = self.tests_dict[fully_qualified_name]
            except KeyError:
                items.remove(item)
                continue
            try:
                if test['skip']:
                    item.add_marker(pytest.mark.skipif)
                else:
                    item.keywords['skipif'] = None
                    item.keywords['skip'] = None
                if test['xfail']:
                    item.add_marker(pytest.mark.xfail)
                else:
                    item.keywords['xfail'] = None

                grouped_items.setdefault(test['order'], []).append(item)
            except KeyError as e:
                raise ImproperlyConfigured('missing {} field in {} configuration'.format(e, item.name))
        if grouped_items:
            items[:] = self.order_items(grouped_items)
        BaseRunner.pytest_collection_modifyitems(self, config, items)

    def order_items(self, grouped_items):
        # Algorithm provided by https://github.com/ftobia
        if grouped_items:
            unordered_items = grouped_items.pop(None, None)
            sorted_items = []
            prev_key = 0
            for key, ordered_items in grouped_items.items():
                if unordered_items and key < 0 <= prev_key:
                    sorted_items.extend(unordered_items)
                    unordered_items = None
                prev_key = key
                sorted_items.extend(ordered_items)
            if unordered_items:
                sorted_items.extend(unordered_items)
            return sorted_items

    def pytest_generate_tests(self, metafunc):
        fully_qualified_name = '.'.join([metafunc.module.__name__, metafunc.cls.__name__, metafunc.function.__name__])
        test_instances = [test for test in self.tests_dict.items()
                          if fully_qualified_name == re.sub('\[.*?\]$', '', test[0])]
        idlist = []
        argnames = []
        argvalues = []
        try:
            params = test_instances[0][1]['test_params'].items()
        except KeyError:
            raise ImproperlyConfigured('missing params field in {} configuration'.format(test_instances[0]))
        for argname, _ in params:
            if argname in metafunc.fixturenames:
                argnames.append(argname)
            else:
                raise ImproperlyConfigured("'{}' is not a valid argument for {}".format(argname, fully_qualified_name))
        for instance_id, test_config in test_instances:
            try:
                idlist.append(test_config['id'])
                values = [x[1] for x in test_config['test_params'].items()]
                fixture_binding = test_config['fixture_binding']
                for argname, fixture_config in fixture_binding.items():
                    try:
                        func = fixture_config['func']
                        scope = fixture_config.get('scope', None)
                        params = fixture_config.get('params', None)
                    except KeyError as e:
                            raise ImproperlyConfigured(
                                "missing {} key in {} fixture binding configuration".format(e, argname))
                    try:
                        self.test_arg_fixture_binding_dict[instance_id][argname] = (func, scope, params)
                    except KeyError:
                        self.test_arg_fixture_binding_dict[instance_id] = {}
                        self.test_arg_fixture_binding_dict[instance_id][argname] = (func, scope, params)
                    if argname in metafunc.fixturenames:
                        values.insert(0, func)
                        if argname not in argnames:
                            argnames.insert(0, argname)
                    else:
                        raise ImproperlyConfigured(
                            "'{}' is not a valid argument for {}".format(argname, fully_qualified_name))
                argvalues.append(values)
            except KeyError as e:
                raise ImproperlyConfigured(
                    'missing {} field in test {} configuration'.format(e, instance_id))
        if idlist:
                metafunc.parametrize(argnames, argvalues, ids=idlist, scope="function")

    def pytest_collection_finish(self, session):
        self.tw = session.config.pluginmanager.getplugin('terminalreporter')._tw
        self.tw.write("selected scenario: \n", bold=True)
        self.tw.write(figlet_format(self._name + '\n'), bold=True, blink=True)
