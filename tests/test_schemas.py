from typing import List, Optional, Union
from typing_extensions import Literal, Protocol

from artisan import (
    Artifact, DynamicArtifact, Namespace, Target,
    get_spec_dict_schema, get_spec_list_schema, get_spec_schema, using_context)



#-- Tests ----------------------------------------------------------------------

def test_type_annotations() -> None:
    class Helper_v0(Target):
        '[Helper description]'

        class Spec(Protocol):
            object_: object
            bool_: bool
            int_: int
            float_: float

    class Branch_v0(Artifact):
        '[Branch description]'

    class Leaf1_v0(Branch_v0):
        '[Leaf1 description]'

        class Spec(Protocol):
            str_: str
            list_: list
            bool_list: List[bool]
            optional_bool: Optional[bool]

    class Leaf2_v0(Branch_v0):
        # [No docstring]

        class Spec(Protocol):
            int_or_str: Union[int, str]
            literal: Literal[0, 1]
            leaf1: Leaf1_v0
            helper: Helper_v0.Spec

    scope = dict(
        Helper = Helper_v0,
        Branch = Branch_v0,
        Leaf1 = Leaf1_v0,
        Leaf2 = Leaf2_v0)

    with using_context(scope=scope):
        assert get_spec_schema() == {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            '$defs': {
                '__PathString::Branch': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf1': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf2': {
                    'pattern': '^@\\/.*'
                },
                'Helper': {
                    'type': 'object',
                    'description': '[Helper description]',
                    'required': ['object_', 'bool_', 'int_', 'float_'],
                    'properties': {
                        'object_': {},
                        'bool_': {'type': 'boolean'},
                        'int_': {'type': 'integer'},
                        'float_': {'type': 'number'}
                    }
                },
                'Branch': {
                    'description': '[Branch description]',
                    'oneOf': [
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf1'}}},
                            {'$ref': '#/$defs/Leaf1'}
                        ]},
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf2'}}},
                            {'$ref': '#/$defs/Leaf2'}
                        ]}
                    ]
                },
                'Leaf1': {
                    'type': 'object',
                    'description': '[Leaf1 description]',
                    'required': ['str_', 'list_', 'bool_list', 'optional_bool'],
                    'properties': {
                        'str_': {
                            'type': 'string'
                        },
                        'list_': {
                            'type': 'array'
                        },
                        'bool_list': {
                            'type': 'array',
                            'items': {'type': 'boolean'}
                        },
                        'optional_bool': {
                            'oneOf': [{'type': 'boolean'}, {'type': 'null'}]
                        },
                    }
                },
                'Leaf2': {
                    'type': 'object',
                    'description': '',
                    'required': ['int_or_str', 'literal', 'leaf1', 'helper'],
                    'properties': {
                        'int_or_str': {
                            'oneOf': [{'type': 'integer'}, {'type': 'string'}]
                        },
                        'literal': {
                            'enum': [0, 1]
                        },
                        'leaf1': {
                            '$ref': '#/$defs/__PathString::Leaf1'
                        },
                        'helper': {
                            '$ref': '#/$defs/Helper'
                        }
                    }
                }
            },
            'oneOf': [
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf1'}}},
                    {'$ref': '#/$defs/Leaf1'}
                ]},
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf2'}}},
                    {'$ref': '#/$defs/Leaf2'}
                ]}
            ]
        }


def test_default_annotations() -> None:
    class Helper_v1(Target):
        '[Helper description]'
        class Spec:
            object_ = None
            bool_ = False
            int_ = 0
            float_ = 0.1

    class Branch_v1(Artifact):
        '[Branch description]'

    class Leaf1_v1(Branch_v1):
        '[Leaf1 description]'
        class Spec:
            str_ = '[some data]'
            list_ = [False, 1, 2.3]
            bool_list = [False, True]
            optional_bool = None

    class Leaf2_v1(Branch_v1):
        # [No docstring]
        class Spec:
            int_or_str = '[possibly an int]'
            literal = 0
            leaf1 = DynamicArtifact @ '.'
            helper = Namespace(
                object_ = '[object]',
                bool_ = True,
                int_ = 1,
                float_ = 2.3)

    scope = dict(
        Helper = Helper_v1,
        Branch = Branch_v1,
        Leaf1 = Leaf1_v1,
        Leaf2 = Leaf2_v1)

    with using_context(scope=scope):
        assert get_spec_schema() == {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            '$defs': {
                '__PathString::Branch': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf1': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf2': {
                    'pattern': '^@\\/.*'
                },
                'Helper': {
                    'type': 'object',
                    'description': '[Helper description]',
                    'required': [],
                    'properties': {
                        'object_': {'default': None},
                        'bool_': {'default': False},
                        'int_': {'default': 0},
                        'float_': {'default': 0.1}
                    }
                },
                'Branch': {
                    'description': '[Branch description]',
                    'oneOf': [
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf1'}}},
                            {'$ref': '#/$defs/Leaf1'}
                        ]},
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf2'}}},
                            {'$ref': '#/$defs/Leaf2'}
                        ]}
                    ]
                },
                'Leaf1': {
                    'type': 'object',
                    'description': '[Leaf1 description]',
                    'required': [],
                    'properties': {
                        'str_': {'default': '[some data]'},
                        'list_': {'default': [False, 1, 2.3]},
                        'bool_list': {'default': [False, True]},
                        'optional_bool': {'default': None},
                    }
                },
                'Leaf2': {
                    'type': 'object',
                    'description': '',
                    'required': [],
                    'properties': {
                        'int_or_str': {'default': '[possibly an int]'},
                        'literal': {'default': 0},
                        'leaf1': {'default': '@/'},
                        'helper': {'default': {
                            'object_': '[object]',
                            'bool_': True,
                            'int_': 1,
                            'float_': 2.3
                        }}
                    }
                }
            },
            'oneOf': [
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf1'}}},
                    {'$ref': '#/$defs/Leaf1'}
                ]},
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf2'}}},
                    {'$ref': '#/$defs/Leaf2'}
                ]}
            ]
        }


def test_type_and_default_annotations() -> None:
    class Helper_v2(Target):
        '[Helper description]'
        class Spec(Protocol):
            object_: object = None
            bool_: bool = False
            int_: int = 0
            float_: float = 0.1

    class Branch_v2(Artifact):
        '[Branch description]'

    class Leaf1_v2(Branch_v2):
        '[Leaf1 description]'
        class Spec(Protocol):
            str_: str = '[some data]'
            list_: list = [False, 1, 2.3]
            bool_list: List[bool] = [False, True]
            optional_bool: Optional[bool] = None

    class Leaf2_v2(Branch_v2):
        # [No docstring]
        class Spec(Protocol):
            int_or_str: Union[int, str] = '[possibly an int]'
            literal: Literal[0, 1] = 0
            leaf1: Leaf1_v2 = DynamicArtifact @ '.' # type: ignore
            helper: Helper_v2.Spec = Namespace(
                object_ = '[object]',
                bool_ = True,
                int_ = 1,
                float_ = 2.3)

    scope = dict(
        Helper = Helper_v2,
        Branch = Branch_v2,
        Leaf1 = Leaf1_v2,
        Leaf2 = Leaf2_v2)

    with using_context(scope=scope):
        assert get_spec_schema() == {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            '$defs': {
                '__PathString::Branch': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf1': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf2': {
                    'pattern': '^@\\/.*'
                },
                'Helper': {
                    'type': 'object',
                    'description': '[Helper description]',
                    'required': [],
                    'properties': {
                        'object_': {'default': None},
                        'bool_': {'type': 'boolean', 'default': False},
                        'int_': {'type': 'integer', 'default': 0},
                        'float_': {'type': 'number', 'default': 0.1}
                    }
                },
                'Branch': {
                    'description': '[Branch description]',
                    'oneOf': [
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf1'}}},
                            {'$ref': '#/$defs/Leaf1'}
                        ]},
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf2'}}},
                            {'$ref': '#/$defs/Leaf2'}
                        ]}
                    ]
                },
                'Leaf1': {
                    'type': 'object',
                    'description': '[Leaf1 description]',
                    'required': [],
                    'properties': {
                        'str_': {
                            'type': 'string',
                            'default': '[some data]'
                        },
                        'list_': {
                            'type': 'array',
                            'default': [False, 1, 2.3]
                        },
                        'bool_list': {
                            'type': 'array',
                            'items': {'type': 'boolean'},
                            'default': [False, True]
                        },
                        'optional_bool': {
                            'oneOf': [{'type': 'boolean'}, {'type': 'null'}],
                            'default': None
                        }
                    }
                },
                'Leaf2': {
                    'type': 'object',
                    'description': '',
                    'required': [],
                    'properties': {
                        'int_or_str': {
                            'oneOf': [{'type': 'integer'}, {'type': 'string'}],
                            'default': '[possibly an int]'
                        },
                        'literal': {
                            'enum': [0, 1],
                            'default': 0
                        },
                        'leaf1': {
                            '$ref': '#/$defs/__PathString::Leaf1',
                            'default': '@/'
                        },
                        'helper': {
                            '$ref': '#/$defs/Helper',
                            'default': {
                                'object_': '[object]',
                                'bool_': True,
                                'int_': 1,
                                'float_': 2.3
                            }
                        }
                    }
                }
            },
            'oneOf': [
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf1'}}},
                    {'$ref': '#/$defs/Leaf1'}
                ]},
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf2'}}},
                    {'$ref': '#/$defs/Leaf2'}
                ]}
            ]
        }


def test_postfix_annotations() -> None:
    class Helper_v3(Target):
        '[Helper description]'

        class Spec(Protocol):
            object_: object; '[object_ description]'
            bool_: bool; {'default': False}
            int_: int; '[int_ description]', {'minimum': 0}
            float_: float; {'maximum': 100}, '[float_ description]'

    class Branch_v3(Artifact):
        '[Branch description]'

    class Leaf1_v3(Branch_v3):
        '[Leaf1 description]'

        class Spec:
            str_ = '[some data]'; '[str_ description]'
            list_ = [False, 1, 2.3]; {'maxItems': 4}
            bool_list = [False, True]; '[bool_list description]', {}
            optional_bool = None; {}, '[optional_bool description]'

    class Leaf2_v3(Branch_v3):
        # [No docstring]

        class Spec:
            int_or_str: Union[int, str] = '[possibly an int]'
            {'$comment': '[comment for int_or_str]'}

            literal: Literal[0, 1] = 0
            '[literal description]'

            leaf1: Leaf1_v3 = DynamicArtifact @ '.' # type: ignore
            '[leaf1 description]', {'$comment': '[comment for leaf1]'}

            helper: Helper_v3.Spec = Namespace(
                object_ = '[object]',
                bool_ = True,
                int_ = 1,
                float_ = 2.3)
            {'$comment': '[comment for helper]'}, '[helper description]'

    scope = dict(
        Helper = Helper_v3,
        Branch = Branch_v3,
        Leaf1 = Leaf1_v3,
        Leaf2 = Leaf2_v3)

    with using_context(scope=scope):
        assert get_spec_schema() == {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            '$defs': {
                '__PathString::Branch': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf1': {
                    'pattern': '^@\\/.*'
                },
                '__PathString::Leaf2': {
                    'pattern': '^@\\/.*'
                },
                'Helper': {
                    'type': 'object',
                    'description': '[Helper description]',
                    'required': ['object_', 'int_', 'float_'],
                    'properties': {
                        'object_': {
                            'description': '[object_ description]'
                        },
                        'bool_': {
                            'type': 'boolean',
                            'default': False
                        },
                        'int_': {
                            'type': 'integer',
                            'description': '[int_ description]',
                            'minimum': 0
                        },
                        'float_': {
                            'type': 'number',
                            'maximum': 100,
                            'description': '[float_ description]'
                        }
                    }
                },
                'Branch': {
                    'description': '[Branch description]',
                    'oneOf': [
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf1'}}},
                            {'$ref': '#/$defs/Leaf1'}
                        ]},
                        {'allOf': [
                            {'required': ['type']},
                            {'properties': {'type': {'const': 'Leaf2'}}},
                            {'$ref': '#/$defs/Leaf2'}
                        ]}
                    ]
                },
                'Leaf1': {
                    'type': 'object',
                    'description': '[Leaf1 description]',
                    'required': [],
                    'properties': {
                        'str_': {
                            'default': '[some data]',
                            'description': '[str_ description]'
                        },
                        'list_': {
                            'default': [False, 1, 2.3],
                            'maxItems': 4
                        },
                        'bool_list': {
                            'default': [False, True],
                            'description': '[bool_list description]'
                        },
                        'optional_bool': {
                            'default': None,
                            'description': '[optional_bool description]'
                        },
                    }
                },
                'Leaf2': {
                    'type': 'object',
                    'description': '',
                    'required': [],
                    'properties': {
                        'int_or_str': {
                            'oneOf': [{'type': 'integer'}, {'type': 'string'}],
                            'default': '[possibly an int]',
                            '$comment': '[comment for int_or_str]'
                        },
                        'literal': {
                            'description': '[literal description]',
                            'enum': [0, 1],
                            'default': 0
                        },
                        'leaf1': {
                            '$ref': '#/$defs/__PathString::Leaf1',
                            'default': '@/',
                            'description': '[leaf1 description]',
                            '$comment': '[comment for leaf1]'
                        },
                        'helper': {
                            '$ref': '#/$defs/Helper',
                            'default': {
                                'object_': '[object]',
                                'bool_': True,
                                'int_': 1,
                                'float_': 2.3
                            },
                            'description': '[helper description]',
                            '$comment': '[comment for helper]',
                        }
                    }
                }
            },
            'oneOf': [
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf1'}}},
                    {'$ref': '#/$defs/Leaf1'}
                ]},
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf2'}}},
                    {'$ref': '#/$defs/Leaf2'}
                ]}
            ]
        }


def test_spec_collection_schemas() -> None:
    '''
    Test `get_spec_list_schema` and `get_spec_dict_schema`.
    '''
    class Helper_v4(Target): pass
    class Branch_v4(Artifact): pass
    class Leaf1_v4(Branch_v4): pass
    class Leaf2_v4(Branch_v4): pass

    scope = dict(
        Helper = Helper_v4,
        Branch = Branch_v4,
        Leaf1 = Leaf1_v4,
        Leaf2 = Leaf2_v4)

    schema_defs = {
        '__PathString::Branch': {
            'pattern': '^@\\/.*'
        },
        '__PathString::Leaf1': {
            'pattern': '^@\\/.*'
        },
        '__PathString::Leaf2': {
            'pattern': '^@\\/.*'
        },
        'Helper': {
            'type': 'object',
            'description': '',
            'required': [],
            'properties': {}
        },
        'Branch': {
            'description': '',
            'oneOf': [
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf1'}}},
                    {'$ref': '#/$defs/Leaf1'}
                ]},
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf2'}}},
                    {'$ref': '#/$defs/Leaf2'}
                ]}
            ]
        },
        'Leaf1': {
            'type': 'object',
            'description': '',
            'required': [],
            'properties': {}
        },
        'Leaf2': {
            'type': 'object',
            'description': '',
            'required': [],
            'properties': {}
        }
    }

    with using_context(scope=scope):
        assert get_spec_list_schema() == {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            '$defs': schema_defs,
            'type': 'array',
            'items': {'oneOf': [
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf1'}}},
                    {'$ref': '#/$defs/Leaf1'}
                ]},
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf2'}}},
                    {'$ref': '#/$defs/Leaf2'}
                ]}
            ]}
        }
        assert get_spec_dict_schema() == {
            '$schema': 'http://json-schema.org/draft-07/schema#',
            '$defs': schema_defs,
            'type': 'object',
            'properties': {'$schema': {'type': 'string'}},
            'additionalProperties': {'oneOf': [
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf1'}}},
                    {'$ref': '#/$defs/Leaf1'}
                ]},
                {'allOf': [
                    {'required': ['type']},
                    {'properties': {'type': {'const': 'Leaf2'}}},
                    {'$ref': '#/$defs/Leaf2'}
                ]}
            ]}
        }



#-- Supporting definitions -----------------------------------------------------

def meta_schema(type_name: str) -> dict:
    '''
    Return a schema for an artifact's `_meta_` field.
    '''
    return {
        'type': 'object',
        'required': ['spec'],
        'properties': {
            'spec': {
                'type': 'object',
                'required': ['type'],
                'properties': {
                    'type': {'const': type_name}
                }
            }
        }
    }


def ndarray_schema() -> dict:
    return {
        'type': 'array',
        'cborTags': [40],
        'items': [
            {'type': 'array', 'items': {'type': 'integer'}},
            {'cborType': 'bstr'}
        ]
    }
