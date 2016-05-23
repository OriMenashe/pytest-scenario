__author__ = 'orim'
import pytest


@pytest.fixture
def not_parametrized_fixture():
    return "I am not parametrized"


@pytest.fixture
def int_parametrized_fixture(request):
    return request.param.num


@pytest.fixture
def string_parametrized_fixture(request):
    return request.param.string


class TestParametrize:

    @pytest.mark.test_case(fixture_binding=[('first_fixture_place_holder', {'func': 'int_parametrized_fixture',
                                                                            'scope': 'function',
                                                                            'params': [('num', 100)]
                                                                            }),
                                            ('second_fixture_place_holder', {'func': 'string_parametrized_fixture',
                                                                             'scope': 'class',
                                                                             'params': [('string', 'Hello World')]
                                                                             }),
                                            ('third_fixture_place_holder', {'func': 'not_parametrized_fixture',
                                                                            'scope': 'module',
                                                                            })
                                            ],
                           test_params=[('test_param', 1.04)])
    def test_fixture_param(self, first_fixture_place_holder, second_fixture_place_holder, third_fixture_place_holder,
                            test_param):
        print('\n')
        assert isinstance(first_fixture_place_holder, int)
        print('first_fixture_place_holder: %d' % first_fixture_place_holder)
        assert isinstance(second_fixture_place_holder, str)
        print('second_fixture_place_holder: %s' % second_fixture_place_holder)
        assert isinstance(third_fixture_place_holder, str)
        print('third_fixture_place_holder: %s' % third_fixture_place_holder)
        assert isinstance(test_param, float)
        print('test_param: %s' % test_param)

    @pytest.mark.test_case(fixture_binding=[('fixture_place_holder', {'func': 'string_parametrized_fixture'})])
    def test_fixture_param_persistency(self, fixture_place_holder):
        print('\n')
        assert isinstance(fixture_place_holder, str)
        print('fixture_place_holder param: %s' % fixture_place_holder)

    @pytest.mark.skip
    def test_scenario_instantiation(self, fixture_place_holder, test_param):
        print('\n')
        assert isinstance(fixture_place_holder, str)
        assert isinstance(test_param, str)
        print('%s %s' % (fixture_place_holder, test_param))
