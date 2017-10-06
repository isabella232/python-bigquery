# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import email
import io
import json
import unittest

import mock
from six.moves import http_client
import pytest

from google.cloud.bigquery.dataset import DatasetReference


class _SchemaBase(object):

    def _verify_field(self, field, r_field):
        self.assertEqual(field.name, r_field['name'])
        self.assertEqual(field.field_type, r_field['type'])
        self.assertEqual(field.mode, r_field.get('mode', 'NULLABLE'))

    def _verifySchema(self, schema, resource):
        r_fields = resource['schema']['fields']
        self.assertEqual(len(schema), len(r_fields))

        for field, r_field in zip(schema, r_fields):
            self._verify_field(field, r_field)


class TestTableReference(unittest.TestCase):

    @staticmethod
    def _get_target_class():
        from google.cloud.bigquery.table import TableReference

        return TableReference

    def _make_one(self, *args, **kw):
        return self._get_target_class()(*args, **kw)

    def test_ctor_defaults(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset_ref = DatasetReference('project_1', 'dataset_1')

        table_ref = self._make_one(dataset_ref, 'table_1')
        self.assertEqual(table_ref.dataset_id, dataset_ref.dataset_id)
        self.assertEqual(table_ref.table_id, 'table_1')

    def test_to_api_repr(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset_ref = DatasetReference('project_1', 'dataset_1')
        table_ref = self._make_one(dataset_ref, 'table_1')

        resource = table_ref.to_api_repr()

        self.assertEqual(
            resource,
            {
                'projectId': 'project_1',
                'datasetId': 'dataset_1',
                'tableId': 'table_1',
            })

    def test_from_api_repr(self):
        from google.cloud.bigquery.dataset import DatasetReference
        from google.cloud.bigquery.table import TableReference
        dataset_ref = DatasetReference('project_1', 'dataset_1')
        expected = self._make_one(dataset_ref, 'table_1')

        got = TableReference.from_api_repr(
            {
                'projectId': 'project_1',
                'datasetId': 'dataset_1',
                'tableId': 'table_1',
            })

        self.assertEqual(expected, got)

    def test___eq___wrong_type(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset_ref = DatasetReference('project_1', 'dataset_1')
        table = self._make_one(dataset_ref, 'table_1')
        other = object()
        self.assertNotEqual(table, other)
        self.assertEqual(table, mock.ANY)

    def test___eq___project_mismatch(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset = DatasetReference('project_1', 'dataset_1')
        other_dataset = DatasetReference('project_2', 'dataset_1')
        table = self._make_one(dataset, 'table_1')
        other = self._make_one(other_dataset, 'table_1')
        self.assertNotEqual(table, other)

    def test___eq___dataset_mismatch(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset = DatasetReference('project_1', 'dataset_1')
        other_dataset = DatasetReference('project_1', 'dataset_2')
        table = self._make_one(dataset, 'table_1')
        other = self._make_one(other_dataset, 'table_1')
        self.assertNotEqual(table, other)

    def test___eq___table_mismatch(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset = DatasetReference('project_1', 'dataset_1')
        table = self._make_one(dataset, 'table_1')
        other = self._make_one(dataset, 'table_2')
        self.assertNotEqual(table, other)

    def test___eq___equality(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset = DatasetReference('project_1', 'dataset_1')
        table = self._make_one(dataset, 'table_1')
        other = self._make_one(dataset, 'table_1')
        self.assertEqual(table, other)

    def test___hash__set_equality(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset = DatasetReference('project_1', 'dataset_1')
        table1 = self._make_one(dataset, 'table1')
        table2 = self._make_one(dataset, 'table2')
        set_one = {table1, table2}
        set_two = {table1, table2}
        self.assertEqual(set_one, set_two)

    def test___hash__not_equals(self):
        from google.cloud.bigquery.dataset import DatasetReference
        dataset = DatasetReference('project_1', 'dataset_1')
        table1 = self._make_one(dataset, 'table1')
        table2 = self._make_one(dataset, 'table2')
        set_one = {table1}
        set_two = {table2}
        self.assertNotEqual(set_one, set_two)

    def test___repr__(self):
        dataset = DatasetReference('project1', 'dataset1')
        table1 = self._make_one(dataset, 'table1')
        expected = "TableReference('project1', 'dataset1', 'table1')"
        self.assertEqual(repr(table1), expected)


class TestTable(unittest.TestCase, _SchemaBase):

    PROJECT = 'prahj-ekt'
    DS_ID = 'dataset-name'
    TABLE_NAME = 'table-name'

    @staticmethod
    def _get_target_class():
        from google.cloud.bigquery.table import Table

        return Table

    def _make_one(self, *args, **kw):
        return self._get_target_class()(*args, **kw)

    def _setUpConstants(self):
        import datetime
        from google.cloud._helpers import UTC

        self.WHEN_TS = 1437767599.006
        self.WHEN = datetime.datetime.utcfromtimestamp(self.WHEN_TS).replace(
            tzinfo=UTC)
        self.ETAG = 'ETAG'
        self.TABLE_FULL_ID = '%s:%s:%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        self.RESOURCE_URL = 'http://example.com/path/to/resource'
        self.NUM_BYTES = 12345
        self.NUM_ROWS = 67

    def _makeResource(self):
        self._setUpConstants()
        return {
            'creationTime': self.WHEN_TS * 1000,
            'tableReference':
                {'projectId': self.PROJECT,
                 'datasetId': self.DS_ID,
                 'tableId': self.TABLE_NAME},
            'schema': {'fields': [
                {'name': 'full_name', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'age', 'type': 'INTEGER', 'mode': 'REQUIRED'}]},
            'etag': 'ETAG',
            'id': self.TABLE_FULL_ID,
            'lastModifiedTime': self.WHEN_TS * 1000,
            'location': 'US',
            'selfLink': self.RESOURCE_URL,
            'numRows': self.NUM_ROWS,
            'numBytes': self.NUM_BYTES,
            'type': 'TABLE',
        }

    def _verifyReadonlyResourceProperties(self, table, resource):
        if 'creationTime' in resource:
            self.assertEqual(table.created, self.WHEN)
        else:
            self.assertIsNone(table.created)

        if 'etag' in resource:
            self.assertEqual(table.etag, self.ETAG)
        else:
            self.assertIsNone(table.etag)

        if 'numRows' in resource:
            self.assertEqual(table.num_rows, self.NUM_ROWS)
        else:
            self.assertIsNone(table.num_rows)

        if 'numBytes' in resource:
            self.assertEqual(table.num_bytes, self.NUM_BYTES)
        else:
            self.assertIsNone(table.num_bytes)

        if 'selfLink' in resource:
            self.assertEqual(table.self_link, self.RESOURCE_URL)
        else:
            self.assertIsNone(table.self_link)

        self.assertEqual(table.full_table_id, self.TABLE_FULL_ID)
        self.assertEqual(table.table_type,
                         'TABLE' if 'view' not in resource else 'VIEW')

    def _verifyResourceProperties(self, table, resource):

        self._verifyReadonlyResourceProperties(table, resource)

        if 'expirationTime' in resource:
            self.assertEqual(table.expires, self.EXP_TIME)
        else:
            self.assertIsNone(table.expires)

        self.assertEqual(table.description, resource.get('description'))
        self.assertEqual(table.friendly_name, resource.get('friendlyName'))
        self.assertEqual(table.location, resource.get('location'))

        if 'view' in resource:
            self.assertEqual(table.view_query, resource['view']['query'])
            self.assertEqual(
                table.view_use_legacy_sql,
                resource['view'].get('useLegacySql'))
        else:
            self.assertIsNone(table.view_query)
            self.assertIsNone(table.view_use_legacy_sql)

        if 'schema' in resource:
            self._verifySchema(table.schema, resource)
        else:
            self.assertEqual(table.schema, [])

    def test_ctor(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        self.assertEqual(table.table_id, self.TABLE_NAME)
        self.assertEqual(table.project, self.PROJECT)
        self.assertEqual(table.dataset_id, self.DS_ID)
        self.assertEqual(
            table.path,
            '/projects/%s/datasets/%s/tables/%s' % (
                self.PROJECT, self.DS_ID, self.TABLE_NAME))
        self.assertEqual(table.schema, [])

        self.assertIsNone(table.created)
        self.assertIsNone(table.etag)
        self.assertIsNone(table.modified)
        self.assertIsNone(table.num_bytes)
        self.assertIsNone(table.num_rows)
        self.assertIsNone(table.self_link)
        self.assertIsNone(table.full_table_id)
        self.assertIsNone(table.table_type)

        self.assertIsNone(table.description)
        self.assertIsNone(table.expires)
        self.assertIsNone(table.friendly_name)
        self.assertIsNone(table.location)
        self.assertIsNone(table.view_query)
        self.assertIsNone(table.view_use_legacy_sql)

    def test_ctor_w_schema(self):
        from google.cloud.bigquery.table import SchemaField

        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)

        self.assertEqual(table.schema, [full_name, age])

    def test_num_bytes_getter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        # Check with no value set.
        self.assertIsNone(table.num_bytes)

        num_bytes = 1337
        # Check with integer value set.
        table._properties = {'numBytes': num_bytes}
        self.assertEqual(table.num_bytes, num_bytes)

        # Check with a string value set.
        table._properties = {'numBytes': str(num_bytes)}
        self.assertEqual(table.num_bytes, num_bytes)

        # Check with invalid int value.
        table._properties = {'numBytes': 'x'}
        with self.assertRaises(ValueError):
            getattr(table, 'num_bytes')

    def test_num_rows_getter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        # Check with no value set.
        self.assertIsNone(table.num_rows)

        num_rows = 42
        # Check with integer value set.
        table._properties = {'numRows': num_rows}
        self.assertEqual(table.num_rows, num_rows)

        # Check with a string value set.
        table._properties = {'numRows': str(num_rows)}
        self.assertEqual(table.num_rows, num_rows)

        # Check with invalid int value.
        table._properties = {'numRows': 'x'}
        with self.assertRaises(ValueError):
            getattr(table, 'num_rows')

    def test_schema_setter_non_list(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        with self.assertRaises(TypeError):
            table.schema = object()

    def test_schema_setter_invalid_field(self):
        from google.cloud.bigquery.table import SchemaField

        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        with self.assertRaises(ValueError):
            table.schema = [full_name, object()]

    def test_schema_setter(self):
        from google.cloud.bigquery.table import SchemaField

        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table.schema = [full_name, age]
        self.assertEqual(table.schema, [full_name, age])

    def test_props_set_by_server(self):
        import datetime
        from google.cloud._helpers import UTC
        from google.cloud._helpers import _millis

        CREATED = datetime.datetime(2015, 7, 29, 12, 13, 22, tzinfo=UTC)
        MODIFIED = datetime.datetime(2015, 7, 29, 14, 47, 15, tzinfo=UTC)
        TABLE_FULL_ID = '%s:%s:%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        URL = 'http://example.com/projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table._properties['creationTime'] = _millis(CREATED)
        table._properties['etag'] = 'ETAG'
        table._properties['lastModifiedTime'] = _millis(MODIFIED)
        table._properties['numBytes'] = 12345
        table._properties['numRows'] = 66
        table._properties['selfLink'] = URL
        table._properties['id'] = TABLE_FULL_ID
        table._properties['type'] = 'TABLE'

        self.assertEqual(table.created, CREATED)
        self.assertEqual(table.etag, 'ETAG')
        self.assertEqual(table.modified, MODIFIED)
        self.assertEqual(table.num_bytes, 12345)
        self.assertEqual(table.num_rows, 66)
        self.assertEqual(table.self_link, URL)
        self.assertEqual(table.full_table_id, TABLE_FULL_ID)
        self.assertEqual(table.table_type, 'TABLE')

    def test_description_setter_bad_value(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        with self.assertRaises(ValueError):
            table.description = 12345

    def test_description_setter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table.description = 'DESCRIPTION'
        self.assertEqual(table.description, 'DESCRIPTION')

    def test_expires_setter_bad_value(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        with self.assertRaises(ValueError):
            table.expires = object()

    def test_expires_setter(self):
        import datetime
        from google.cloud._helpers import UTC

        WHEN = datetime.datetime(2015, 7, 28, 16, 39, tzinfo=UTC)
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table.expires = WHEN
        self.assertEqual(table.expires, WHEN)

    def test_friendly_name_setter_bad_value(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        with self.assertRaises(ValueError):
            table.friendly_name = 12345

    def test_friendly_name_setter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table.friendly_name = 'FRIENDLY'
        self.assertEqual(table.friendly_name, 'FRIENDLY')

    def test_location_setter_bad_value(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        with self.assertRaises(ValueError):
            table.location = 12345

    def test_location_setter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table.location = 'LOCATION'
        self.assertEqual(table.location, 'LOCATION')

    def test_view_query_setter_bad_value(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        with self.assertRaises(ValueError):
            table.view_query = 12345

    def test_view_query_setter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table.view_query = 'select * from foo'
        self.assertEqual(table.view_query, 'select * from foo')

    def test_view_query_deleter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table.view_query = 'select * from foo'
        del table.view_query
        self.assertIsNone(table.view_query)

    def test_view_use_legacy_sql_setter_bad_value(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        with self.assertRaises(ValueError):
            table.view_use_legacy_sql = 12345

    def test_view_use_legacy_sql_setter(self):
        client = _Client(self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        table.view_use_legacy_sql = False
        table.view_query = 'select * from foo'
        self.assertEqual(table.view_use_legacy_sql, False)
        self.assertEqual(table.view_query, 'select * from foo')

    def test_from_api_repr_missing_identity(self):
        self._setUpConstants()
        client = _Client(self.PROJECT)
        RESOURCE = {}
        klass = self._get_target_class()
        with self.assertRaises(KeyError):
            klass.from_api_repr(RESOURCE, client)

    def test_from_api_repr_bare(self):
        self._setUpConstants()
        client = _Client(self.PROJECT)
        RESOURCE = {
            'id': '%s:%s:%s' % (self.PROJECT, self.DS_ID, self.TABLE_NAME),
            'tableReference': {
                'projectId': self.PROJECT,
                'datasetId': self.DS_ID,
                'tableId': self.TABLE_NAME,
            },
            'type': 'TABLE',
        }
        klass = self._get_target_class()
        table = klass.from_api_repr(RESOURCE, client)
        self.assertEqual(table.table_id, self.TABLE_NAME)
        self.assertIs(table._client, client)
        self._verifyResourceProperties(table, RESOURCE)

    def test_from_api_repr_w_properties(self):
        client = _Client(self.PROJECT)
        RESOURCE = self._makeResource()
        klass = self._get_target_class()
        table = klass.from_api_repr(RESOURCE, client)
        self.assertIs(table._client, client)
        self._verifyResourceProperties(table, RESOURCE)

    def test_partition_type_setter_bad_type(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        with self.assertRaises(ValueError):
            table.partitioning_type = 123

    def test_partition_type_setter_unknown_value(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        with self.assertRaises(ValueError):
            table.partitioning_type = "HASH"

    def test_partition_type_setter_w_known_value(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        self.assertIsNone(table.partitioning_type)
        table.partitioning_type = 'DAY'
        self.assertEqual(table.partitioning_type, 'DAY')

    def test_partition_type_setter_w_none(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        table._properties['timePartitioning'] = {'type': 'DAY'}
        table.partitioning_type = None
        self.assertIsNone(table.partitioning_type)
        self.assertFalse('timePartitioning' in table._properties)

    def test_partition_experation_bad_type(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        with self.assertRaises(ValueError):
            table.partition_expiration = "NEVER"

    def test_partition_expiration_w_integer(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        self.assertIsNone(table.partition_expiration)
        table.partition_expiration = 100
        self.assertEqual(table.partitioning_type, "DAY")
        self.assertEqual(table.partition_expiration, 100)

    def test_partition_expiration_w_none(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        self.assertIsNone(table.partition_expiration)
        table._properties['timePartitioning'] = {
            'type': 'DAY',
            'expirationMs': 100,
        }
        table.partition_expiration = None
        self.assertEqual(table.partitioning_type, "DAY")
        self.assertIsNone(table.partition_expiration)

    def test_partition_expiration_w_none_no_partition_set(self):
        from google.cloud.bigquery.table import SchemaField

        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        self.assertIsNone(table.partition_expiration)
        table.partition_expiration = None
        self.assertIsNone(table.partitioning_type)
        self.assertIsNone(table.partition_expiration)

    def test_list_partitions(self):
        from google.cloud.bigquery.table import SchemaField

        conn = _Connection()
        client = _Client(project=self.PROJECT, connection=conn)
        client._query_results = [(20160804, None), (20160805, None)]
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        self.assertEqual(table.list_partitions(), [20160804, 20160805])

    def test_exists_miss_w_bound_client(self):
        PATH = 'projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        conn = _Connection()
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        self.assertFalse(table.exists())

        self.assertEqual(len(conn._requested), 1)
        req = conn._requested[0]
        self.assertEqual(req['method'], 'GET')
        self.assertEqual(req['path'], '/%s' % PATH)
        self.assertEqual(req['query_params'], {'fields': 'id'})

    def test_exists_hit_w_alternate_client(self):
        PATH = 'projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        conn1 = _Connection()
        client1 = _Client(project=self.PROJECT, connection=conn1)
        conn2 = _Connection({})
        client2 = _Client(project=self.PROJECT, connection=conn2)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client1)

        self.assertTrue(table.exists(client=client2))

        self.assertEqual(len(conn1._requested), 0)
        self.assertEqual(len(conn2._requested), 1)
        req = conn2._requested[0]
        self.assertEqual(req['method'], 'GET')
        self.assertEqual(req['path'], '/%s' % PATH)
        self.assertEqual(req['query_params'], {'fields': 'id'})

    def test_patch_w_invalid_expiration(self):
        RESOURCE = self._makeResource()
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        with self.assertRaises(ValueError):
            table.patch(expires='BOGUS')

    def test_patch_w_bound_client(self):
        PATH = 'projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        DESCRIPTION = 'DESCRIPTION'
        TITLE = 'TITLE'
        RESOURCE = self._makeResource()
        RESOURCE['description'] = DESCRIPTION
        RESOURCE['friendlyName'] = TITLE
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        table.patch(description=DESCRIPTION,
                    friendly_name=TITLE,
                    view_query=None)

        self.assertEqual(len(conn._requested), 1)
        req = conn._requested[0]
        self.assertEqual(req['method'], 'PATCH')
        SENT = {
            'description': DESCRIPTION,
            'friendlyName': TITLE,
            'view': None,
        }
        self.assertEqual(req['data'], SENT)
        self.assertEqual(req['path'], '/%s' % PATH)
        self._verifyResourceProperties(table, RESOURCE)

    def test_patch_w_alternate_client(self):
        import datetime
        from google.cloud._helpers import UTC
        from google.cloud._helpers import _millis
        from google.cloud.bigquery.table import SchemaField

        PATH = 'projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        QUERY = 'select fullname, age from person_ages'
        LOCATION = 'EU'
        RESOURCE = self._makeResource()
        RESOURCE['view'] = {'query': QUERY}
        RESOURCE['type'] = 'VIEW'
        RESOURCE['location'] = LOCATION
        self.EXP_TIME = datetime.datetime(2015, 8, 1, 23, 59, 59,
                                          tzinfo=UTC)
        RESOURCE['expirationTime'] = _millis(self.EXP_TIME)
        conn1 = _Connection()
        client1 = _Client(project=self.PROJECT, connection=conn1)
        conn2 = _Connection(RESOURCE)
        client2 = _Client(project=self.PROJECT, connection=conn2)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client1)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='NULLABLE')

        table.patch(client=client2, view_query=QUERY, location=LOCATION,
                    expires=self.EXP_TIME, schema=[full_name, age])

        self.assertEqual(len(conn1._requested), 0)
        self.assertEqual(len(conn2._requested), 1)
        req = conn2._requested[0]
        self.assertEqual(req['method'], 'PATCH')
        self.assertEqual(req['path'], '/%s' % PATH)
        SENT = {
            'view': {'query': QUERY},
            'location': LOCATION,
            'expirationTime': _millis(self.EXP_TIME),
            'schema': {'fields': [
                {'name': 'full_name', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'age', 'type': 'INTEGER', 'mode': 'NULLABLE'}]},
        }
        self.assertEqual(req['data'], SENT)
        self._verifyResourceProperties(table, RESOURCE)

    def test_patch_w_schema_None(self):
        # Simulate deleting schema:  not sure if back-end will actually
        # allow this operation, but the spec says it is optional.
        PATH = 'projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        DESCRIPTION = 'DESCRIPTION'
        TITLE = 'TITLE'
        RESOURCE = self._makeResource()
        RESOURCE['description'] = DESCRIPTION
        RESOURCE['friendlyName'] = TITLE
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        table.patch(schema=None)

        self.assertEqual(len(conn._requested), 1)
        req = conn._requested[0]
        self.assertEqual(req['method'], 'PATCH')
        SENT = {'schema': None}
        self.assertEqual(req['data'], SENT)
        self.assertEqual(req['path'], '/%s' % PATH)
        self._verifyResourceProperties(table, RESOURCE)

    def test_update_w_bound_client(self):
        from google.cloud.bigquery.table import SchemaField

        PATH = 'projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        DESCRIPTION = 'DESCRIPTION'
        TITLE = 'TITLE'
        RESOURCE = self._makeResource()
        RESOURCE['description'] = DESCRIPTION
        RESOURCE['friendlyName'] = TITLE
        conn = _Connection(RESOURCE)
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        table = self._make_one(table_ref, schema=[full_name, age],
                               client=client)
        table.description = DESCRIPTION
        table.friendly_name = TITLE

        table.update()

        self.assertEqual(len(conn._requested), 1)
        req = conn._requested[0]
        self.assertEqual(req['method'], 'PUT')
        SENT = {
            'tableReference':
                {'projectId': self.PROJECT,
                 'datasetId': self.DS_ID,
                 'tableId': self.TABLE_NAME},
            'schema': {'fields': [
                {'name': 'full_name', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'age', 'type': 'INTEGER', 'mode': 'REQUIRED'}]},
            'description': DESCRIPTION,
            'friendlyName': TITLE,
        }
        self.assertEqual(req['data'], SENT)
        self.assertEqual(req['path'], '/%s' % PATH)
        self._verifyResourceProperties(table, RESOURCE)

    def test_update_w_alternate_client(self):
        import datetime
        from google.cloud._helpers import UTC
        from google.cloud._helpers import _millis

        PATH = 'projects/%s/datasets/%s/tables/%s' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        DEF_TABLE_EXP = 12345
        LOCATION = 'EU'
        QUERY = 'select fullname, age from person_ages'
        RESOURCE = self._makeResource()
        RESOURCE['defaultTableExpirationMs'] = 12345
        RESOURCE['location'] = LOCATION
        self.EXP_TIME = datetime.datetime(2015, 8, 1, 23, 59, 59,
                                          tzinfo=UTC)
        RESOURCE['expirationTime'] = _millis(self.EXP_TIME)
        RESOURCE['view'] = {'query': QUERY, 'useLegacySql': True}
        RESOURCE['type'] = 'VIEW'
        conn1 = _Connection()
        client1 = _Client(project=self.PROJECT, connection=conn1)
        conn2 = _Connection(RESOURCE)
        client2 = _Client(project=self.PROJECT, connection=conn2)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client1)
        table.default_table_expiration_ms = DEF_TABLE_EXP
        table.location = LOCATION
        table.expires = self.EXP_TIME
        table.view_query = QUERY
        table.view_use_legacy_sql = True

        table.update(client=client2)

        self.assertEqual(len(conn1._requested), 0)
        self.assertEqual(len(conn2._requested), 1)
        req = conn2._requested[0]
        self.assertEqual(req['method'], 'PUT')
        self.assertEqual(req['path'], '/%s' % PATH)
        SENT = {
            'tableReference':
                {'projectId': self.PROJECT,
                 'datasetId': self.DS_ID,
                 'tableId': self.TABLE_NAME},
            'expirationTime': _millis(self.EXP_TIME),
            'location': 'EU',
            'view': {'query': QUERY, 'useLegacySql': True},
        }
        self.assertEqual(req['data'], SENT)
        self._verifyResourceProperties(table, RESOURCE)

    def test_row_from_mapping_wo_schema(self):
        from google.cloud.bigquery.table import _TABLE_HAS_NO_SCHEMA
        MAPPING = {'full_name': 'Phred Phlyntstone', 'age': 32}
        client = _Client(project=self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        with self.assertRaises(ValueError) as exc:
            table.row_from_mapping(MAPPING)

        self.assertEqual(exc.exception.args, (_TABLE_HAS_NO_SCHEMA,))

    def test_row_from_mapping_w_invalid_schema(self):
        from google.cloud.bigquery.table import SchemaField
        MAPPING = {
            'full_name': 'Phred Phlyntstone',
            'age': 32,
            'colors': ['red', 'green'],
            'bogus': 'WHATEVER',
        }
        client = _Client(project=self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        colors = SchemaField('colors', 'DATETIME', mode='REPEATED')
        bogus = SchemaField('joined', 'STRING', mode='BOGUS')
        table = self._make_one(table_ref,
                               schema=[full_name, age, colors, bogus],
                               client=client)

        with self.assertRaises(ValueError) as exc:
            table.row_from_mapping(MAPPING)

        self.assertIn('Unknown field mode: BOGUS', str(exc.exception))

    def test_row_from_mapping_w_schema(self):
        from google.cloud.bigquery.table import SchemaField
        MAPPING = {
            'full_name': 'Phred Phlyntstone',
            'age': 32,
            'colors': ['red', 'green'],
            'extra': 'IGNORED',
        }
        client = _Client(project=self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        colors = SchemaField('colors', 'DATETIME', mode='REPEATED')
        joined = SchemaField('joined', 'STRING', mode='NULLABLE')
        table = self._make_one(table_ref,
                               schema=[full_name, age, colors, joined],
                               client=client)

        self.assertEqual(
            table.row_from_mapping(MAPPING),
            ('Phred Phlyntstone', 32, ['red', 'green'], None))

    def test_insert_data_wo_schema(self):
        from google.cloud.bigquery.table import _TABLE_HAS_NO_SCHEMA

        client = _Client(project=self.PROJECT)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)
        ROWS = [
            ('Phred Phlyntstone', 32),
            ('Bharney Rhubble', 33),
            ('Wylma Phlyntstone', 29),
            ('Bhettye Rhubble', 27),
        ]

        with self.assertRaises(ValueError) as exc:
            table.insert_data(ROWS)

        self.assertEqual(exc.exception.args, (_TABLE_HAS_NO_SCHEMA,))

    def test_insert_data_w_bound_client(self):
        import datetime
        from google.cloud._helpers import UTC
        from google.cloud._helpers import _datetime_to_rfc3339
        from google.cloud._helpers import _microseconds_from_datetime
        from google.cloud.bigquery.table import SchemaField

        WHEN_TS = 1437767599.006
        WHEN = datetime.datetime.utcfromtimestamp(WHEN_TS).replace(
            tzinfo=UTC)
        PATH = 'projects/%s/datasets/%s/tables/%s/insertAll' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        conn = _Connection({})
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        joined = SchemaField('joined', 'TIMESTAMP', mode='NULLABLE')
        table = self._make_one(table_ref, schema=[full_name, age, joined],
                               client=client)
        ROWS = [
            ('Phred Phlyntstone', 32, _datetime_to_rfc3339(WHEN)),
            ('Bharney Rhubble', 33, WHEN + datetime.timedelta(seconds=1)),
            ('Wylma Phlyntstone', 29, WHEN + datetime.timedelta(seconds=2)),
            ('Bhettye Rhubble', 27, None),
        ]

        def _row_data(row):
            joined = row[2]
            if isinstance(row[2], datetime.datetime):
                joined = _microseconds_from_datetime(joined) * 1e-6
            return {'full_name': row[0],
                    'age': str(row[1]),
                    'joined': joined}

        SENT = {
            'rows': [{'json': _row_data(row)} for row in ROWS],
        }

        errors = table.insert_data(ROWS)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(conn._requested), 1)
        req = conn._requested[0]
        self.assertEqual(req['method'], 'POST')
        self.assertEqual(req['path'], '/%s' % PATH)
        self.assertEqual(req['data'], SENT)

    def test_insert_data_w_alternate_client(self):
        from google.cloud.bigquery.table import SchemaField

        PATH = 'projects/%s/datasets/%s/tables/%s/insertAll' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        RESPONSE = {
            'insertErrors': [
                {'index': 1,
                 'errors': [
                     {'reason': 'REASON',
                      'location': 'LOCATION',
                      'debugInfo': 'INFO',
                      'message': 'MESSAGE'}
                 ]},
            ]}
        conn1 = _Connection()
        client1 = _Client(project=self.PROJECT, connection=conn1)
        conn2 = _Connection(RESPONSE)
        client2 = _Client(project=self.PROJECT, connection=conn2)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        voter = SchemaField('voter', 'BOOLEAN', mode='NULLABLE')
        table = self._make_one(table_ref, schema=[full_name, age, voter],
                               client=client1)
        ROWS = [
            ('Phred Phlyntstone', 32, True),
            ('Bharney Rhubble', 33, False),
            ('Wylma Phlyntstone', 29, True),
            ('Bhettye Rhubble', 27, True),
        ]

        def _row_data(row):
            return {
                'full_name': row[0],
                'age': str(row[1]),
                'voter': row[2] and 'true' or 'false',
            }

        SENT = {
            'skipInvalidRows': True,
            'ignoreUnknownValues': True,
            'templateSuffix': '20160303',
            'rows': [{'insertId': index, 'json': _row_data(row)}
                     for index, row in enumerate(ROWS)],
        }

        errors = table.insert_data(
            client=client2,
            rows=ROWS,
            row_ids=[index for index, _ in enumerate(ROWS)],
            skip_invalid_rows=True,
            ignore_unknown_values=True,
            template_suffix='20160303',
        )

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['index'], 1)
        self.assertEqual(len(errors[0]['errors']), 1)
        self.assertEqual(errors[0]['errors'][0],
                         RESPONSE['insertErrors'][0]['errors'][0])

        self.assertEqual(len(conn1._requested), 0)
        self.assertEqual(len(conn2._requested), 1)
        req = conn2._requested[0]
        self.assertEqual(req['method'], 'POST')
        self.assertEqual(req['path'], '/%s' % PATH)
        self.assertEqual(req['data'], SENT)

    def test_insert_data_w_repeated_fields(self):
        from google.cloud.bigquery.table import SchemaField

        PATH = 'projects/%s/datasets/%s/tables/%s/insertAll' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        conn = _Connection({})
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('color', 'STRING', mode='REPEATED')
        index = SchemaField('index', 'INTEGER', 'REPEATED')
        score = SchemaField('score', 'FLOAT', 'REPEATED')
        struct = SchemaField('struct', 'RECORD', mode='REPEATED',
                             fields=[index, score])
        table = self._make_one(table_ref, schema=[full_name, struct],
                               client=client)
        ROWS = [
            (['red', 'green'], [{'index': [1, 2], 'score': [3.1415, 1.414]}]),
        ]

        def _row_data(row):
            return {'color': row[0],
                    'struct': row[1]}

        SENT = {
            'rows': [{'json': _row_data(row)} for row in ROWS],
        }

        errors = table.insert_data(ROWS)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(conn._requested), 1)
        req = conn._requested[0]
        self.assertEqual(req['method'], 'POST')
        self.assertEqual(req['path'], '/%s' % PATH)
        self.assertEqual(req['data'], SENT)

    def test_insert_data_w_record_schema(self):
        from google.cloud.bigquery.table import SchemaField

        PATH = 'projects/%s/datasets/%s/tables/%s/insertAll' % (
            self.PROJECT, self.DS_ID, self.TABLE_NAME)
        conn = _Connection({})
        client = _Client(project=self.PROJECT, connection=conn)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        area_code = SchemaField('area_code', 'STRING', 'REQUIRED')
        local_number = SchemaField('local_number', 'STRING', 'REQUIRED')
        rank = SchemaField('rank', 'INTEGER', 'REQUIRED')
        phone = SchemaField('phone', 'RECORD', mode='NULLABLE',
                            fields=[area_code, local_number, rank])
        table = self._make_one(table_ref, schema=[full_name, phone],
                               client=client)
        ROWS = [
            ('Phred Phlyntstone', {'area_code': '800',
                                   'local_number': '555-1212',
                                   'rank': 1}),
            ('Bharney Rhubble', {'area_code': '877',
                                 'local_number': '768-5309',
                                 'rank': 2}),
            ('Wylma Phlyntstone', None),
        ]

        def _row_data(row):
            return {'full_name': row[0],
                    'phone': row[1]}

        SENT = {
            'rows': [{'json': _row_data(row)} for row in ROWS],
        }

        errors = table.insert_data(ROWS)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(conn._requested), 1)
        req = conn._requested[0]
        self.assertEqual(req['method'], 'POST')
        self.assertEqual(req['path'], '/%s' % PATH)
        self.assertEqual(req['data'], SENT)

    def test__get_transport(self):
        client = mock.Mock(spec=[u'_credentials', '_http'])
        client._http = mock.sentinel.http
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        transport = table._get_transport(client)

        self.assertIs(transport, mock.sentinel.http)

    @staticmethod
    def _mock_requests_response(status_code, headers, content=b''):
        return mock.Mock(
            content=content, headers=headers, status_code=status_code,
            spec=['content', 'headers', 'status_code'])

    def _mock_transport(self, status_code, headers, content=b''):
        fake_transport = mock.Mock(spec=['request'])
        fake_response = self._mock_requests_response(
            status_code, headers, content=content)
        fake_transport.request.return_value = fake_response
        return fake_transport

    def _initiate_resumable_upload_helper(self, num_retries=None):
        from google.resumable_media.requests import ResumableUpload
        from google.cloud.bigquery.table import _DEFAULT_CHUNKSIZE
        from google.cloud.bigquery.table import _GENERIC_CONTENT_TYPE
        from google.cloud.bigquery.table import _get_upload_headers
        from google.cloud.bigquery.table import _get_upload_metadata

        connection = _Connection()
        client = _Client(self.PROJECT, connection=connection)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        # Create mocks to be checked for doing transport.
        resumable_url = 'http://test.invalid?upload_id=hey-you'
        response_headers = {'location': resumable_url}
        fake_transport = self._mock_transport(
            http_client.OK, response_headers)
        client._http = fake_transport

        # Create some mock arguments and call the method under test.
        data = b'goodbye gudbi gootbee'
        stream = io.BytesIO(data)
        metadata = _get_upload_metadata(
            'CSV', table._schema, table.project,
            table.dataset_id, table.table_id)
        upload, transport = table._initiate_resumable_upload(
            client, stream, metadata, num_retries)

        # Check the returned values.
        self.assertIsInstance(upload, ResumableUpload)
        upload_url = (
            'https://www.googleapis.com/upload/bigquery/v2/projects/' +
            self.PROJECT +
            '/jobs?uploadType=resumable')
        self.assertEqual(upload.upload_url, upload_url)
        expected_headers = _get_upload_headers(connection.USER_AGENT)
        self.assertEqual(upload._headers, expected_headers)
        self.assertFalse(upload.finished)
        self.assertEqual(upload._chunk_size, _DEFAULT_CHUNKSIZE)
        self.assertIs(upload._stream, stream)
        self.assertIsNone(upload._total_bytes)
        self.assertEqual(upload._content_type, _GENERIC_CONTENT_TYPE)
        self.assertEqual(upload.resumable_url, resumable_url)

        retry_strategy = upload._retry_strategy
        self.assertEqual(retry_strategy.max_sleep, 64.0)
        if num_retries is None:
            self.assertEqual(retry_strategy.max_cumulative_retry, 600.0)
            self.assertIsNone(retry_strategy.max_retries)
        else:
            self.assertIsNone(retry_strategy.max_cumulative_retry)
            self.assertEqual(retry_strategy.max_retries, num_retries)
        self.assertIs(transport, fake_transport)
        # Make sure we never read from the stream.
        self.assertEqual(stream.tell(), 0)

        # Check the mocks.
        request_headers = expected_headers.copy()
        request_headers['x-upload-content-type'] = _GENERIC_CONTENT_TYPE
        fake_transport.request.assert_called_once_with(
            'POST',
            upload_url,
            data=json.dumps(metadata).encode('utf-8'),
            headers=request_headers,
        )

    def test__initiate_resumable_upload(self):
        self._initiate_resumable_upload_helper()

    def test__initiate_resumable_upload_with_retry(self):
        self._initiate_resumable_upload_helper(num_retries=11)

    def _do_multipart_upload_success_helper(
            self, get_boundary, num_retries=None):
        from google.cloud.bigquery.table import _get_upload_headers
        from google.cloud.bigquery.table import _get_upload_metadata

        connection = _Connection()
        client = _Client(self.PROJECT, connection=connection)
        dataset = DatasetReference(self.PROJECT, self.DS_ID)
        table_ref = dataset.table(self.TABLE_NAME)
        table = self._make_one(table_ref, client=client)

        # Create mocks to be checked for doing transport.
        fake_transport = self._mock_transport(http_client.OK, {})
        client._http = fake_transport

        # Create some mock arguments.
        data = b'Bzzzz-zap \x00\x01\xf4'
        stream = io.BytesIO(data)
        metadata = _get_upload_metadata(
            'CSV', table._schema, table.project,
            table.dataset_id, table.table_id)
        size = len(data)
        response = table._do_multipart_upload(
            client, stream, metadata, size, num_retries)

        # Check the mocks and the returned value.
        self.assertIs(response, fake_transport.request.return_value)
        self.assertEqual(stream.tell(), size)
        get_boundary.assert_called_once_with()

        upload_url = (
            'https://www.googleapis.com/upload/bigquery/v2/projects/' +
            self.PROJECT +
            '/jobs?uploadType=multipart')
        payload = (
            b'--==0==\r\n' +
            b'content-type: application/json; charset=UTF-8\r\n\r\n' +
            json.dumps(metadata).encode('utf-8') + b'\r\n' +
            b'--==0==\r\n' +
            b'content-type: */*\r\n\r\n' +
            data + b'\r\n' +
            b'--==0==--')
        headers = _get_upload_headers(connection.USER_AGENT)
        headers['content-type'] = b'multipart/related; boundary="==0=="'
        fake_transport.request.assert_called_once_with(
            'POST',
            upload_url,
            data=payload,
            headers=headers,
        )

    @mock.patch(u'google.resumable_media._upload.get_boundary',
                return_value=b'==0==')
    def test__do_multipart_upload(self, get_boundary):
        self._do_multipart_upload_success_helper(get_boundary)

    @mock.patch(u'google.resumable_media._upload.get_boundary',
                return_value=b'==0==')
    def test__do_multipart_upload_with_retry(self, get_boundary):
        self._do_multipart_upload_success_helper(get_boundary, num_retries=8)


class TestTableUpload(object):
    # NOTE: This is a "partner" to `TestTable` meant to test some of the
    #       "upload" portions of `Table`. It also uses `pytest`-style tests
    #       rather than `unittest`-style.

    @staticmethod
    def _make_table(transport=None):
        from google.cloud.bigquery import _http
        from google.cloud.bigquery import client
        from google.cloud.bigquery import dataset
        from google.cloud.bigquery import table

        connection = mock.create_autospec(_http.Connection, instance=True)
        client = mock.create_autospec(client.Client, instance=True)
        client._connection = connection
        client._credentials = mock.sentinel.credentials
        client._http = transport
        client.project = 'project_id'

        dataset_ref = dataset.DatasetReference('project_id', 'test_dataset')
        table_ref = dataset_ref.table('test_table')
        table = table.Table(table_ref, client=client)

        return table

    @staticmethod
    def _make_response(status_code, content='', headers={}):
        """Make a mock HTTP response."""
        import requests
        response = requests.Response()
        response.request = requests.Request(
            'POST', 'http://example.com').prepare()
        response._content = content.encode('utf-8')
        response.headers.update(headers)
        response.status_code = status_code
        return response

    @classmethod
    def _make_do_upload_patch(cls, table, method, side_effect=None):
        """Patches the low-level upload helpers."""
        if side_effect is None:
            side_effect = [cls._make_response(
                http_client.OK,
                json.dumps({}),
                {'Content-Type': 'application/json'})]
        return mock.patch.object(
            table, method, side_effect=side_effect, autospec=True)

    EXPECTED_CONFIGURATION = {
        'configuration': {
            'load': {
                'sourceFormat': 'CSV',
                'destinationTable': {
                    'projectId': 'project_id',
                    'datasetId': 'test_dataset',
                    'tableId': 'test_table'
                }
            }
        }
    }

    @staticmethod
    def _make_file_obj():
        return io.BytesIO(b'hello, is it me you\'re looking for?')

    # High-level tests

    def test_upload_from_file_resumable(self):
        import google.cloud.bigquery.table

        table = self._make_table()
        file_obj = self._make_file_obj()

        do_upload_patch = self._make_do_upload_patch(
            table, '_do_resumable_upload')
        with do_upload_patch as do_upload:
            table.upload_from_file(file_obj, source_format='CSV')

        do_upload.assert_called_once_with(
            table._client,
            file_obj,
            self.EXPECTED_CONFIGURATION,
            google.cloud.bigquery.table._DEFAULT_NUM_RETRIES)

    def test_upload_file_resumable_metadata(self):
        table = self._make_table()
        file_obj = self._make_file_obj()

        config_args = {
            'source_format': 'CSV',
            'allow_jagged_rows': False,
            'allow_quoted_newlines': False,
            'create_disposition': 'CREATE_IF_NEEDED',
            'encoding': 'utf8',
            'field_delimiter': ',',
            'ignore_unknown_values': False,
            'max_bad_records': 0,
            'quote_character': '"',
            'skip_leading_rows': 1,
            'write_disposition': 'WRITE_APPEND',
            'job_name': 'oddjob',
            'null_marker': r'\N',
        }

        expected_config = {
            'configuration': {
                'load': {
                    'sourceFormat': config_args['source_format'],
                    'destinationTable': {
                        'projectId': table.project,
                        'datasetId': table.dataset_id,
                        'tableId': table.table_id,
                    },
                    'allowJaggedRows': config_args['allow_jagged_rows'],
                    'allowQuotedNewlines':
                        config_args['allow_quoted_newlines'],
                    'createDisposition': config_args['create_disposition'],
                    'encoding': config_args['encoding'],
                    'fieldDelimiter': config_args['field_delimiter'],
                    'ignoreUnknownValues':
                        config_args['ignore_unknown_values'],
                    'maxBadRecords': config_args['max_bad_records'],
                    'quote': config_args['quote_character'],
                    'skipLeadingRows': config_args['skip_leading_rows'],
                    'writeDisposition': config_args['write_disposition'],
                    'jobReference': {'jobId': config_args['job_name']},
                    'nullMarker': config_args['null_marker'],
                },
            },
        }

        do_upload_patch = self._make_do_upload_patch(
            table, '_do_resumable_upload')
        with do_upload_patch as do_upload:
            table.upload_from_file(
                file_obj, **config_args)

        do_upload.assert_called_once_with(
            table._client,
            file_obj,
            expected_config,
            mock.ANY)

    def test_upload_from_file_multipart(self):
        import google.cloud.bigquery.table

        table = self._make_table()
        file_obj = self._make_file_obj()
        file_obj_size = 10

        do_upload_patch = self._make_do_upload_patch(
            table, '_do_multipart_upload')
        with do_upload_patch as do_upload:
            table.upload_from_file(
                file_obj, source_format='CSV', size=file_obj_size)

        do_upload.assert_called_once_with(
            table._client,
            file_obj,
            self.EXPECTED_CONFIGURATION,
            file_obj_size,
            google.cloud.bigquery.table._DEFAULT_NUM_RETRIES)

    def test_upload_from_file_with_retries(self):
        table = self._make_table()
        file_obj = self._make_file_obj()
        num_retries = 20

        do_upload_patch = self._make_do_upload_patch(
            table, '_do_resumable_upload')
        with do_upload_patch as do_upload:
            table.upload_from_file(
                file_obj, source_format='CSV', num_retries=num_retries)

        do_upload.assert_called_once_with(
            table._client,
            file_obj,
            self.EXPECTED_CONFIGURATION,
            num_retries)

    def test_upload_from_file_with_rewind(self):
        table = self._make_table()
        file_obj = self._make_file_obj()
        file_obj.seek(2)

        with self._make_do_upload_patch(table, '_do_resumable_upload'):
            table.upload_from_file(
                file_obj, source_format='CSV', rewind=True)

        assert file_obj.tell() == 0

    def test_upload_from_file_failure(self):
        from google.resumable_media import InvalidResponse
        from google.cloud import exceptions

        table = self._make_table()
        file_obj = self._make_file_obj()

        response = self._make_response(
            content='Someone is already in this spot.',
            status_code=http_client.CONFLICT)

        do_upload_patch = self._make_do_upload_patch(
            table, '_do_resumable_upload',
            side_effect=InvalidResponse(response))

        with do_upload_patch, pytest.raises(exceptions.Conflict) as exc_info:
            table.upload_from_file(
                file_obj, source_format='CSV', rewind=True)

        assert response.text in exc_info.value.message
        assert exc_info.value.errors == []

    def test_upload_from_file_bad_mode(self):
        table = self._make_table()
        file_obj = mock.Mock(spec=['mode'])
        file_obj.mode = 'x'

        with pytest.raises(ValueError):
            table.upload_from_file(
                file_obj, source_format='CSV',)

    # Low-level tests

    @classmethod
    def _make_resumable_upload_responses(cls, size):
        """Make a series of responses for a successful resumable upload."""
        from google import resumable_media

        resumable_url = 'http://test.invalid?upload_id=and-then-there-was-1'
        initial_response = cls._make_response(
            http_client.OK, '', {'location': resumable_url})
        data_response = cls._make_response(
            resumable_media.PERMANENT_REDIRECT,
            '', {'range': 'bytes=0-{:d}'.format(size - 1)})
        final_response = cls._make_response(
            http_client.OK,
            json.dumps({'size': size}),
            {'Content-Type': 'application/json'})
        return [initial_response, data_response, final_response]

    @staticmethod
    def _make_transport(responses=None):
        import google.auth.transport.requests

        transport = mock.create_autospec(
            google.auth.transport.requests.AuthorizedSession, instance=True)
        transport.request.side_effect = responses
        return transport

    def test__do_resumable_upload(self):
        file_obj = self._make_file_obj()
        file_obj_len = len(file_obj.getvalue())
        transport = self._make_transport(
            self._make_resumable_upload_responses(file_obj_len))
        table = self._make_table(transport)

        result = table._do_resumable_upload(
            table._client,
            file_obj,
            self.EXPECTED_CONFIGURATION,
            None)

        content = result.content.decode('utf-8')
        assert json.loads(content) == {'size': file_obj_len}

        # Verify that configuration data was passed in with the initial
        # request.
        transport.request.assert_any_call(
            'POST',
            mock.ANY,
            data=json.dumps(self.EXPECTED_CONFIGURATION).encode('utf-8'),
            headers=mock.ANY)

    def test__do_multipart_upload(self):
        transport = self._make_transport([self._make_response(http_client.OK)])
        table = self._make_table(transport)
        file_obj = self._make_file_obj()
        file_obj_len = len(file_obj.getvalue())

        table._do_multipart_upload(
            table._client,
            file_obj,
            self.EXPECTED_CONFIGURATION,
            file_obj_len,
            None)

        # Verify that configuration data was passed in with the initial
        # request.
        request_args = transport.request.mock_calls[0][2]
        request_data = request_args['data'].decode('utf-8')
        request_headers = request_args['headers']

        request_content = email.message_from_string(
            'Content-Type: {}\r\n{}'.format(
                request_headers['content-type'].decode('utf-8'),
                request_data))

        # There should be two payloads: the configuration and the binary daya.
        configuration_data = request_content.get_payload(0).get_payload()
        binary_data = request_content.get_payload(1).get_payload()

        assert json.loads(configuration_data) == self.EXPECTED_CONFIGURATION
        assert binary_data.encode('utf-8') == file_obj.getvalue()

    def test__do_multipart_upload_wrong_size(self):
        table = self._make_table()
        file_obj = self._make_file_obj()
        file_obj_len = len(file_obj.getvalue())

        with pytest.raises(ValueError):
            table._do_multipart_upload(
                table._client,
                file_obj,
                {},
                file_obj_len+1,
                None)


class Test_parse_schema_resource(unittest.TestCase, _SchemaBase):

    def _call_fut(self, resource):
        from google.cloud.bigquery.table import _parse_schema_resource

        return _parse_schema_resource(resource)

    def _makeResource(self):
        return {
            'schema': {'fields': [
                {'name': 'full_name', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'age', 'type': 'INTEGER', 'mode': 'REQUIRED'},
            ]},
        }

    def test__parse_schema_resource_defaults(self):
        RESOURCE = self._makeResource()
        schema = self._call_fut(RESOURCE['schema'])
        self._verifySchema(schema, RESOURCE)

    def test__parse_schema_resource_subfields(self):
        RESOURCE = self._makeResource()
        RESOURCE['schema']['fields'].append(
            {'name': 'phone',
             'type': 'RECORD',
             'mode': 'REPEATED',
             'fields': [{'name': 'type',
                         'type': 'STRING',
                         'mode': 'REQUIRED'},
                        {'name': 'number',
                         'type': 'STRING',
                         'mode': 'REQUIRED'}]})
        schema = self._call_fut(RESOURCE['schema'])
        self._verifySchema(schema, RESOURCE)

    def test__parse_schema_resource_fields_without_mode(self):
        RESOURCE = self._makeResource()
        RESOURCE['schema']['fields'].append(
            {'name': 'phone',
             'type': 'STRING'})

        schema = self._call_fut(RESOURCE['schema'])
        self._verifySchema(schema, RESOURCE)


class Test_build_schema_resource(unittest.TestCase, _SchemaBase):

    def _call_fut(self, resource):
        from google.cloud.bigquery.table import _build_schema_resource

        return _build_schema_resource(resource)

    def test_defaults(self):
        from google.cloud.bigquery.table import SchemaField

        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        resource = self._call_fut([full_name, age])
        self.assertEqual(len(resource), 2)
        self.assertEqual(resource[0],
                         {'name': 'full_name',
                          'type': 'STRING',
                          'mode': 'REQUIRED'})
        self.assertEqual(resource[1],
                         {'name': 'age',
                          'type': 'INTEGER',
                          'mode': 'REQUIRED'})

    def test_w_description(self):
        from google.cloud.bigquery.table import SchemaField

        DESCRIPTION = 'DESCRIPTION'
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED',
                                description=DESCRIPTION)
        age = SchemaField('age', 'INTEGER', mode='REQUIRED')
        resource = self._call_fut([full_name, age])
        self.assertEqual(len(resource), 2)
        self.assertEqual(resource[0],
                         {'name': 'full_name',
                          'type': 'STRING',
                          'mode': 'REQUIRED',
                          'description': DESCRIPTION})
        self.assertEqual(resource[1],
                         {'name': 'age',
                          'type': 'INTEGER',
                          'mode': 'REQUIRED'})

    def test_w_subfields(self):
        from google.cloud.bigquery.table import SchemaField

        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        ph_type = SchemaField('type', 'STRING', 'REQUIRED')
        ph_num = SchemaField('number', 'STRING', 'REQUIRED')
        phone = SchemaField('phone', 'RECORD', mode='REPEATED',
                            fields=[ph_type, ph_num])
        resource = self._call_fut([full_name, phone])
        self.assertEqual(len(resource), 2)
        self.assertEqual(resource[0],
                         {'name': 'full_name',
                          'type': 'STRING',
                          'mode': 'REQUIRED'})
        self.assertEqual(resource[1],
                         {'name': 'phone',
                          'type': 'RECORD',
                          'mode': 'REPEATED',
                          'fields': [{'name': 'type',
                                      'type': 'STRING',
                                      'mode': 'REQUIRED'},
                                     {'name': 'number',
                                      'type': 'STRING',
                                      'mode': 'REQUIRED'}]})


class Test__get_upload_metadata(unittest.TestCase):

    @staticmethod
    def _call_fut(source_format, schema, project, dataset_id, name):
        from google.cloud.bigquery.table import _get_upload_metadata

        return _get_upload_metadata(
            source_format, schema, project, dataset_id, name)

    def test_empty_schema(self):
        source_format = 'AVRO'
        dataset = mock.Mock(project='prediction',
                            spec=['dataset_id', 'project'])
        dataset.dataset_id = 'market'  # mock.Mock() treats `name` specially.
        table_name = 'chairs'
        metadata = self._call_fut(source_format, [], dataset.project,
                                  dataset.dataset_id, table_name)

        expected = {
            'configuration': {
                'load': {
                    'sourceFormat': source_format,
                    'destinationTable': {
                        'projectId': dataset.project,
                        'datasetId': dataset.dataset_id,
                        'tableId': table_name,
                    },
                },
            },
        }
        self.assertEqual(metadata, expected)

    def test_with_schema(self):
        from google.cloud.bigquery.table import SchemaField

        source_format = 'CSV'
        full_name = SchemaField('full_name', 'STRING', mode='REQUIRED')
        dataset = mock.Mock(project='blind', spec=['dataset_id', 'project'])
        dataset.dataset_id = 'movie'  # mock.Mock() treats `name` specially.
        table_name = 'teebull-neem'
        metadata = self._call_fut(
            source_format, [full_name], dataset.project,
            dataset.dataset_id, table_name)

        expected = {
            'configuration': {
                'load': {
                    'sourceFormat': source_format,
                    'destinationTable': {
                        'projectId': dataset.project,
                        'datasetId': dataset.dataset_id,
                        'tableId': table_name,
                    },
                    'schema': {
                        'fields': [
                            {
                                'name': full_name.name,
                                'type': full_name.field_type,
                                'mode': full_name.mode,
                            },
                        ],
                    },
                },
            },
        }
        self.assertEqual(metadata, expected)


class _Client(object):

    _query_results = ()

    def __init__(self, project='project', connection=None):
        self.project = project
        self._connection = connection

    def run_sync_query(self, query):
        return _Query(query, self)


class _Query(object):

    def __init__(self, query, client):
        self.query = query
        self.rows = []
        self.client = client

    def run(self):
        self.rows = self.client._query_results


class _Connection(object):

    API_BASE_URL = 'http://example.com'
    USER_AGENT = 'testing 1.2.3'

    def __init__(self, *responses):
        self._responses = responses[:]
        self._requested = []

    def api_request(self, **kw):
        from google.cloud.exceptions import NotFound

        self._requested.append(kw)

        try:
            response, self._responses = self._responses[0], self._responses[1:]
        except IndexError:
            raise NotFound('miss')
        else:
            return response
