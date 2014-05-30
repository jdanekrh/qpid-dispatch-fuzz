#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# 'License'); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#


#pylint: disable=wildcard-import,missing-docstring,too-many-public-methods

import unittest, json
from qpid_dispatch_internal.management.schema import Schema, EntityType, BooleanType, EnumType, AttributeDef, SchemaError, schema_file
from qpid_dispatch_internal.management.entity import Entity

SCHEMA_1 = {
    "prefix":"org.example",
    "includes": {
        "entity-id": {
            "name": {"type":"String", "required": True, "unique":True}
        },
    },
    "entity_types": {
        "container": {
            "singleton": True,
            "include" : ["entity-id"],
            "attributes": {
                "worker-threads" : {"type":"Integer", "default": 1}
            }
        },
        "listener": {
            "include" : ["entity-id"],
            "attributes": {
                "addr" : {"type":"String"}
            }
        },
        "connector": {
            "include" : ["entity-id"],
            "attributes": {
                "addr" : {"type":"String"}
            }
        }
    }
}


class SchemaTest(unittest.TestCase):

    def test_bool(self):
        b = BooleanType()
        self.assertTrue(b.validate('on'))
        self.assertTrue(b.validate(True))
        self.assertFalse(b.validate(False))
        self.assertFalse(b.validate('no'))
        self.assertRaises(ValueError, b.validate, 'x')

    def test_enum(self):
        e = EnumType(['a', 'b', 'c'])
        self.assertEqual(e.validate('a'), 'a')
        self.assertEqual(e.validate(1), 'b')
        self.assertEqual(e.validate('c', enum_as_int=True), 2)
        self.assertEqual(e.validate(2, enum_as_int=True), 2)
        self.assertRaises(ValueError, e.validate, 'foo')
        self.assertRaises(ValueError, e.validate, 3)

    def test_attribute_def(self):
        a = AttributeDef('foo', 'String', 'FOO', False)
        self.assertEqual(a.validate('x'), 'x')
        self.assertEqual(a.validate(None), 'FOO')
        a = AttributeDef('foo', 'String', 'FOO', True)
        self.assertEqual('FOO', a.validate(None))
        a = AttributeDef('foo', 'Integer', None, True)
        self.assertRaises(SchemaError, a.validate, None) # Missing default

    def test_entity_type(self):
        s = Schema(includes={
            'i1':{'foo1': {'type':'String', 'default':'FOO1'}},
            'i2':{'foo2': {'type':'String', 'default':'FOO2'}}})

        e = EntityType('MyEntity', s, attributes={
            'foo': {'type':'String', 'default':'FOO'},
            'req': {'type':'Integer', 'required':True},
            'e': {'type':['x', 'y']}})
        self.assertRaises(SchemaError, e.validate, {}) # Missing required 'req'
        self.assertEqual(e.validate({'req':42, 'e':None}), {'foo': 'FOO', 'req': 42})
        # Try with an include
        e = EntityType('e2', s, attributes={'x':{'type':'Integer'}}, include=['i1', 'i2'])
        self.assertEqual(e.validate({'x':1}), {'x':1, 'foo1': 'FOO1', 'foo2': 'FOO2'})

    qdrouter_json = schema_file('qdrouter.json')


    @staticmethod
    def load_schema(fname=qdrouter_json):
        with open(fname) as f:
            j = json.load(f)
            return Schema(**j)

    def test_schema_dump(self):
        s = Schema(**SCHEMA_1)
        self.maxDiff = None     # pylint: disable=invalid-name
        expect = {
            "prefix":"org.example",
            "includes": {"entity-id": {"name": {"required": True, "unique":True, "type": "String"}}},
            "entity_types": {
                "container": {
                    "singleton": True,
                    "attributes": {
                        "name": {"type":"String", "required": True},
                        "worker-threads": {"type":"Integer", "default": 1}
                    }
                    },
                    "listener": {
                        "attributes": {
                            "name": {"type":"String", "required": True},
                            "addr" : {"type":"String"}
                        }
                    },
                "connector": {
                    "attributes": {
                        "name": {"type":"String", "required": True},
                        "addr" : {"type":"String"}
                    }
                }
            }
        }
        self.assertEquals(s.dump(), expect)

        s2 = Schema(**s.dump())
        self.assertEqual(s.dump(), s2.dump())

    def test_schema_validate(self):
        s = Schema(**SCHEMA_1)
        # Duplicate unique attribute 'name'
        m = [Entity('listener', {'name':'x'}, s),
             Entity('listener', {'name':'x'}, s)]
        self.assertRaises(SchemaError, s.validate, m)
        # Duplicate singleton entity 'container'
        m = [Entity('container', {'name':'x'}, s),
             Entity('container', {'name':'y'}, s)]
        self.assertRaises(SchemaError, s.validate, m)
        # Valid model
        m = [Entity('container', {'name':'x'}, s),
             Entity('listener', {'name':'y'}, s)]
        s.validate(m)

if __name__ == '__main__':
    unittest.main()
