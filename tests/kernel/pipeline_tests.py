# Copyright 2015 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

from __future__ import absolute_import
from __future__ import unicode_literals
import mock
from oauth2client.client import AccessTokenCredentials
import unittest

# import Python so we can mock the parts we need to here.
import IPython
import IPython.core.magic


def noop_decorator(func):
  return func


IPython.core.magic.register_line_cell_magic = noop_decorator
IPython.core.magic.register_line_magic = noop_decorator
IPython.core.magic.register_cell_magic = noop_decorator
IPython.get_ipython = mock.Mock()


import google.datalab.bigquery
import google.datalab.pipeline  # noqa
import google.datalab.pipeline.commands  # noqa
import google.datalab.utils.commands  # noqa


class TestCases(unittest.TestCase):

  @staticmethod
  def _create_context():
    project_id = 'test'
    creds = AccessTokenCredentials('test_token', 'test_ua')
    return google.datalab.Context(project_id, creds)

  @mock.patch('google.datalab.pipeline.Pipeline.py', new_callable=mock.PropertyMock)
  @mock.patch('google.datalab.utils.commands.notebook_environment')
  @mock.patch('google.datalab.Context.default')
  def test_create_cell_no_name(
      self, mock_default_context, mock_notebook_environment, mock_create_py):
    env = {}
    mock_default_context.return_value = TestCases._create_context()
    mock_notebook_environment.return_value = env
    IPython.get_ipython().user_ns = env

    # test pipeline creation
    p_body = """
email: foo@bar.com
schedule:
  start_date: Jun 1 2005  1:33PM
  end_date: Jun 10 2005  1:33PM
  datetime_format: '%b %d %Y %I:%M%p'
  schedule_interval: '@hourly'
tasks:
  print_pdt_date:
    type: bash
    bash_command: date
  print_utc_date:
    type: bash
    bash_command: date -u
    up_stream:
      - print_pdt_date
"""

    # no pipeline name specified. should execute
    with self.assertRaises(Exception):
      google.datalab.pipeline.commands._pipeline._create_cell({'name': None},
                                                              p_body)

  @mock.patch('google.datalab.utils.commands.notebook_environment')
  @mock.patch('google.datalab.Context.default')
  def test_create_cell_with_name(
      self, mock_default_context, mock_notebook_environment):
    env = {}
    mock_default_context.return_value = TestCases._create_context()
    mock_notebook_environment.return_value = env
    IPython.get_ipython().user_ns = env

    # test pipeline creation
    p_body = """
email: foo@bar.com
schedule:
  start_date: Jun 1 2005  1:33PM
  end_date: Jun 10 2005  1:33PM
  datetime_format: '%b %d %Y %I:%M%p'
  schedule_interval: '@hourly'
tasks:
  print_pdt_date:
    type: bash
    bash_command: date
  print_utc_date:
    type: bash
    bash_command: date -u
    up_stream:
      - print_pdt_date
"""
    # test pipeline creation
    google.datalab.pipeline.commands._pipeline._create_cell({'name': 'p1'},
                                                            p_body)

    p1 = env['p1']
    self.assertIsNotNone(p1)
    self.assertEqual(p_body, p1.spec)
    self.assertEqual(p1.py, """
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.contrib.operators.bigquery_table_delete_operator import BigQueryTableDeleteOperator
from airflow.contrib.operators.bigquery_to_bigquery import BigQueryToBigQueryOperator
from airflow.contrib.operators.bigquery_to_gcs import BigQueryToCloudStorageOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'Datalab',
    'depends_on_past': False,
    'email': ['foo@bar.com'],
    'start_date': datetime.strptime('Jun 1 2005  1:33PM', '%b %d %Y %I:%M%p'),
    'end_date': datetime.strptime('Jun 10 2005  1:33PM', '%b %d %Y %I:%M%p'),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(dag_id='p1', schedule_interval='@hourly', default_args=default_args)

print_utc_date = BashOperator(task_id='print_utc_date_id', bash_command='date -u', dag=dag)
print_pdt_date = BashOperator(task_id='print_pdt_date_id', bash_command='date', dag=dag)
print_utc_date.set_upstream(print_pdt_date)
""")

  @mock.patch('google.datalab.utils.commands.notebook_environment')
  @mock.patch('google.datalab.Context.default')
  def test_create_cell_with_variable(
      self, mock_default_context, mock_notebook_environment):
    mock_default_context.return_value = TestCases._create_context()
    env = {}
    env['foo_query'] = google.datalab.bigquery.Query(
        'SELECT * FROM publicdata.samples.wikipedia LIMIT 5')
    mock_notebook_environment.return_value = env
    #TODO(rajivpb): Possibly not necessary
    IPython.get_ipython().user_ns = env

    # test pipeline creation
    p_body = """
email: foo@bar.com
schedule:
  start_date: Jun 1 2005  1:33PM
  end_date: Jun 10 2005  1:33PM
  datetime_format: '%b %d %Y %I:%M%p'
  schedule_interval: '@hourly'
tasks:
  print_pdt_date:
    type: bq
    query: $foo_query
"""

    # no pipeline name specified. should execute
    google.datalab.pipeline.commands._pipeline._create_cell({'name': 'p1'},
                                                            p_body)

    p1 = env['p1']
    self.assertIsNotNone(p1)
    self.assertEqual(p_body, p1.spec)
    self.assertEqual(p1.py, """
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.contrib.operators.bigquery_table_delete_operator import BigQueryTableDeleteOperator
from airflow.contrib.operators.bigquery_to_bigquery import BigQueryToBigQueryOperator
from airflow.contrib.operators.bigquery_to_gcs import BigQueryToCloudStorageOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'Datalab',
    'depends_on_past': False,
    'email': ['foo@bar.com'],
    'start_date': datetime.strptime('Jun 1 2005  1:33PM', '%b %d %Y %I:%M%p'),
    'end_date': datetime.strptime('Jun 10 2005  1:33PM', '%b %d %Y %I:%M%p'),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(dag_id='p1', schedule_interval='@hourly', default_args=default_args)

print_pdt_date = BigQueryOperator(task_id='print_pdt_date_id', bql='SELECT * FROM publicdata.samples.wikipedia LIMIT 5', use_legacy_sql=False, dag=dag)
""")