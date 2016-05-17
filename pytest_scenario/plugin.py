__author__ = "orim"
import re
import pytest
import json
import inspect
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
                        fixture, scope = fixture_config
                        _, arg2fixturedefs = item.session._fixturemanager.getfixtureclosure([fixture], item)
                        if scope:
                            arg2fixturedefs[fixture][0].scope = scope
                        item._fixtureinfo.name2fixturedefs[fixture] = arg2fixturedefs[fixture]
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
                fixture, _ = fixture_config
                item._request._get_active_fixturedef(fixture)
                item.funcargs[argname] = item._request._funcargs[fixture]
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
            argvalues = []
            values = []
            try:
                params = metafunc.function.test_case.kwargs['params']
                for argname, _ in params:
                    if argname in metafunc.fixturenames:
                        argnames.append(argname)
                    else:
                        raise ImproperlyConfigured(
                            "'{}' is not a valid argument for {}".format(argname, fully_qualified_name))
                values = [argvalue for _, argvalue in params]
            except KeyError:
                pass
            try:
                fixture_binding = metafunc.function.test_case.kwargs['fixture_binding']
                instance_id = '%s[%d]' % (fully_qualified_name, self.id_counter)
                try:
                    for argname, fixture, scope in fixture_binding:
                        try:
                            self.test_arg_fixture_binding_dict[instance_id][argname] = (fixture, scope)
                        except KeyError:
                            self.test_arg_fixture_binding_dict[instance_id] = {}
                            self.test_arg_fixture_binding_dict[instance_id][argname] = (fixture, scope)
                        if argname in metafunc.fixturenames:
                            values.insert(0, fixture)
                            if argname not in argnames:
                                argnames.insert(0, argname)
                        else:
                            raise ImproperlyConfigured(
                                "'{}' is not a valid argument for {}".format(argname, fully_qualified_name))
                    argvalues.append(values)
                except ValueError:
                    raise ImproperlyConfigured(
                        "\n{} - fixture_binding member should be a tuple of size 3: "
                        "(argname, fixture, scope)".format(fully_qualified_name))
            except KeyError:
                pass
            metafunc.parametrize(argnames, argvalues, ids=[self.id_counter], scope="function")


class TestScenarioRunner(BaseRunner):

    def __init__(self, scenario_name: str):
        BaseRunner.__init__(self)
        self._name = scenario_name
        scenario_file_path = '{}/{}.json'.format(TEST_SCENARIOS_DIR, scenario_name)
        try:
            with open(scenario_file_path) as scenario_file:
                scenario_config = json.load(scenario_file)
        except FileNotFoundError:
            raise RuntimeError("'{}' scenario is not defined (make sure {} is present)"
                               .format(scenario_name, abspath(scenario_file_path)))
        id_counter = set()
        for test_instance in list(self.mark_order(scenario_config)):
            assert "test_name" in test_instance and "id" in test_instance,\
                "test case record in scenario '{}' is missing a test_name and \ or an id field.".format(scenario_name)
            test_id = test_instance["id"]
            assert test_id not in id_counter,\
                "found a duplicate test id {} in scenario '{}'".format(test_id, scenario_name)
            id_counter.add(test_id)
        self.tests_dict = {'%s.%s.%s[%d]' % (test_instance["module_name"],
                                             test_instance["class_name"],
                                             test_instance["test_name"],
                                             test_instance["id"]): test_instance
                           for test_instance in list(self.mark_order(scenario_config))}

    @staticmethod
    def mark_order(sequence):
        order = 0
        for i in sequence:
            order += 1
            i['order'] = order
            yield i

    def pytest_pycollect_makeitem(self, collector, name, obj):
        tests_dict = collector.config._scenario.tests_dict
        if inspect.isfunction(obj) and name.startswith("test_") and isinstance(collector, pytest.Instance):
            fully_qualified_name = '.'.join([obj.__module__, obj.__qualname__])
            for test_id in tests_dict.keys():
                if fully_qualified_name == re.sub('\[\d+\]$', '', test_id):
                    return
            return []

    def pytest_collection_modifyitems(self, config, items):
        tests_dict = config._scenario.tests_dict
        grouped_items = {}
        for item in items:
            fully_qualified_name = '.'.join([item.module.__name__, item.cls.__name__, item.name])
            try:
                test = tests_dict[fully_qualified_name]
            except KeyError:
                items.remove(item)
                continue
            try:
                if test['skip']:
                    item.add_marker(pytest.mark.skipif)
                else:
                    item.keywords['skipif'] = None
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
        tests_dict = metafunc.config._scenario.tests_dict
        test_instances = [test for test in tests_dict.items()
                          if fully_qualified_name == re.sub('\[\d+\]$', '', test[0])]
        idlist = []
        argnames = []
        argvalues = []
        try:
            params = test_instances[0][1]['params'].items()
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
                values = [x[1] for x in test_config['params'].items()]
                fixture_binding = test_config['fixture_binding']
                for argname, fixture_config in fixture_binding.items():
                    if len(fixture_config) != 2:
                        raise ImproperlyConfigured(
                            "\n{} - fixture_binding member should be a list of size 2: "
                            "[fixture, scope]".format(fully_qualified_name))
                    try:
                        self.test_arg_fixture_binding_dict[instance_id][argname] = fixture_config
                    except KeyError:
                        self.test_arg_fixture_binding_dict[instance_id] = {}
                        self.test_arg_fixture_binding_dict[instance_id][argname] = fixture_config
                    if argname in metafunc.fixturenames:
                        values.insert(0, fixture_config[0])
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
