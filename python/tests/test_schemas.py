from typing import Dict, List, Optional, Union

from artisan._schemas import conf_schema_from_type


#------------------------------------------------------------------------------
# Type and field docstrings

class TypeAndFieldDocstringTest:
    ''' [Short description] '''

    a: object; '[Description of A]'
    b: object; '[Description of B]'

    '''
    [Further description,
     spanning multiple lines]

    [Second paragraph]
    '''

    def f1(self): pass
    def f2(self): pass

    ''' [Third paragraph] '''

    def f3(self): pass


def test_type_and_field_docstrings():
    assert conf_schema_from_type(TypeAndFieldDocstringTest) == {
        'type': 'object',
        'description': (
            '[Short description]\n'
            '\n'
            '[Further description,\n'
            ' spanning multiple lines]\n'
            '\n'
            '[Second paragraph]\n'
            '\n'
            '[Third paragraph]'
        ),
        'outputDescriptions': {
            'a': '[Description of A]',
            'b': '[Description of B]',
        },
        'properties': {},
        'required': []
    }


#------------------------------------------------------------------------------
# Prop type annotations

class PropTypeAnnotationTest:
    class Conf:
        my_object: object
        my_bool: bool
        my_int: int
        my_float: float
        my_str: str
        my_list: list
        my_dict: dict
        my_list_of_bool: List[bool]
        my_dict_of_bool: Dict[str, bool]
        my_optional_bool: Optional[bool]
        my_int_or_str: Union[int, str]


def test_prop_type_annotations():
    assert conf_schema_from_type(PropTypeAnnotationTest) == {
        'type': 'object',
        'description': '',
        'outputDescriptions': {},
        'properties': {
            'my_object': {},
            'my_bool': {'type': 'boolean'},
            'my_int': {'type': 'integer'},
            'my_float': {'type': 'number'},
            'my_str': {'type': 'string'},
            'my_list': {'type': 'array'},
            'my_dict': {'type': 'object'},
            'my_list_of_bool': {
                'type': 'array',
                'items': {'type': 'boolean'}
            },
            'my_dict_of_bool': {
                'type': 'object',
                'additionalProperties': {'type': 'boolean'}
            },
            'my_optional_bool': {
                'oneOf': [{'type': 'boolean'}, {'type': 'null'}]
            },
            'my_int_or_str': {
                'oneOf': [{'type': 'integer'}, {'type': 'string'}]
            }
        },
        'required': [
            'my_object',
            'my_bool',
            'my_int',
            'my_float',
            'my_str',
            'my_list',
            'my_dict',
            'my_list_of_bool',
            'my_dict_of_bool',
            'my_optional_bool',
            'my_int_or_str'
        ]
    }


#------------------------------------------------------------------------------
# Prop default annotations

class PropDefaultAnnotationTest:
    class Conf:
        my_none_type = None
        my_bool = False
        my_int = 0
        my_float = 0.0
        my_str = 'hello'
        my_list = [False, 1, 2.0]
        my_dict = {'zero': 0, 'one': 1.0}
        my_list_of_bool = [False, True]
        my_dict_of_bool = {'false': False, 'true': True}


def test_prop_default_annotations():
    assert conf_schema_from_type(PropDefaultAnnotationTest) == {
        'type': 'object',
        'description': '',
        'outputDescriptions': {},
        'properties': {
            'my_none_type': {'default': None},
            'my_bool': {'default': False},
            'my_int': {'default': 0},
            'my_float': {'default': 0.0},
            'my_str': {'default': 'hello'},
            'my_list': {'default': [False, 1, 2.0]},
            'my_dict': {'default': {'zero': 0, 'one': 1.0}},
            'my_list_of_bool': {'default': [False, True]},
            'my_dict_of_bool': {'default': {'false': False, 'true': True}}
        },
        'required': []
    }


#------------------------------------------------------------------------------
# Prop type annotations mixed with default annotations

class PropTypeAndDefaultAnnotationTest:
    class Conf:
        my_object: object = '[Some object]'
        my_bool: bool = False
        my_int: int = 0
        my_float: float = 0.0
        my_str: str = 'hello'
        my_list: list = [False, 1, 2.0]
        my_dict: dict = {'zero': 0, 'one': 1.0}
        my_list_of_bool: List[bool] = [False, True]
        my_dict_of_bool: Dict[str, bool] = {'false': False, 'true': True}
        my_optional_bool_a: Optional[bool] = None
        my_optional_bool_b: Optional[bool] = False
        my_int_or_str_a: Union[int, str] = 0
        my_int_or_str_b: Union[int, str] = 'zero'


def test_prop_type_and_default_annotations():
    assert conf_schema_from_type(PropTypeAndDefaultAnnotationTest) == {
        'type': 'object',
        'description': '',
        'outputDescriptions': {},
        'properties': {
            'my_object': {'default': '[Some object]'},
            'my_bool': {'type': 'boolean', 'default': False},
            'my_int': {'type': 'integer', 'default': 0},
            'my_float': {'type': 'number', 'default': 0.0},
            'my_str': {'type': 'string', 'default': 'hello'},
            'my_list': {'type': 'array', 'default': [False, 1, 2.0]},
            'my_dict': {'type': 'object', 'default': {'zero': 0, 'one': 1.0}},
            'my_list_of_bool': {
                'type': 'array',
                'items': {'type': 'boolean'},
                'default': [False, True]
            },
            'my_dict_of_bool': {
                'type': 'object',
                'additionalProperties': {'type': 'boolean'},
                'default': {'false': False, 'true': True}
            },
            'my_optional_bool_a': {
                'oneOf': [{'type': 'boolean'}, {'type': 'null'}],
                'default': None
            },
            'my_optional_bool_b': {
                'oneOf': [{'type': 'boolean'}, {'type': 'null'}],
                'default': False
            },
            'my_int_or_str_a': {
                'oneOf': [{'type': 'integer'}, {'type': 'string'}],
                'default': 0
            },
            'my_int_or_str_b': {
                'oneOf': [{'type': 'integer'}, {'type': 'string'}],
                'default': 'zero'
            }
        },
        'required': []
    }


#------------------------------------------------------------------------------
# Postfix annotations

class PostfixAnnotationTest:
    class Conf:
        prop_a: int; '[Prop A description]'
        prop_b: int = 0; '[Prop B description]'
        prop_c = 0; '[Prop C description]'

        prop_d: int; {'enum': [0, 1, 2]}
        prop_e: int = 0; {'minimum': -2}
        prop_f = 0; {'multipleOf': 3}

        prop_g: int; '[Prop G description]', {'enum': [0, 1, 2]}
        prop_h: int = 0; '[Prop H description]', {'minimum': -2}
        prop_i = 0; '[Prop I description]', {'multipleOf': 3}

        prop_j: int; {'enum': [0, 1, 2]}, '[Prop J description]'
        prop_k: int = 0; {'minimum': -2}, '[Prop K description]'
        prop_l = 0; {'multipleOf': 3}, '[Prop L description]'


def test_postfix_annotations():
    assert conf_schema_from_type(PostfixAnnotationTest) == {
        'type': 'object',
        'description': '',
        'outputDescriptions': {},
        'properties': {
            'prop_a': {
                'type': 'integer',
                'description': '[Prop A description]'
            },
            'prop_b': {
                'type': 'integer',
                'default': 0,
                'description': '[Prop B description]'
            },
            'prop_c': {
                'default': 0,
                'description': '[Prop C description]'
            },

            'prop_d': {
                'type': 'integer',
                'enum': [0, 1, 2]
            },
            'prop_e': {
                'type': 'integer',
                'default': 0,
                'minimum': -2
            },
            'prop_f': {
                'default': 0,
                'multipleOf': 3
            },

            'prop_g': {
                'type': 'integer',
                'description': '[Prop G description]',
                'enum': [0, 1, 2]
            },
            'prop_h': {
                'type': 'integer',
                'default': 0,
                'description': '[Prop H description]',
                'minimum': -2
            },
            'prop_i': {
                'default': 0,
                'description': '[Prop I description]',
                'multipleOf': 3
            },

            'prop_j': {
                'type': 'integer',
                'description': '[Prop J description]',
                'enum': [0, 1, 2]
            },
            'prop_k': {
                'type': 'integer',
                'default': 0,
                'description': '[Prop K description]',
                'minimum': -2
            },
            'prop_l': {
                'default': 0,
                'description': '[Prop L description]',
                'multipleOf': 3
            }
        },
        'required': [
            'prop_a',
            'prop_d',
            'prop_g',
            'prop_j'
        ]
    }


#------------------------------------------------------------------------------
# Nested prop types

class CustomType:
    class Conf:
        pass


class NestedPropTypeTest:
    class Conf:
        prop_a: CustomType.Conf
        prop_b: CustomType.Conf = None # type: ignore


def test_nested_prop_types():
    scope = {'CustomType': CustomType}
    assert conf_schema_from_type(NestedPropTypeTest, scope) == {
        'type': 'object',
        'description': '',
        'outputDescriptions': {},
        'properties': {
            'prop_a': {'$ref': '#/definitions/CustomType'},
            'prop_b': {'$ref': '#/definitions/CustomType', 'default': None}
        },
        'required': ['prop_a']
    }
