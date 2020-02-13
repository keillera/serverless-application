import os
import uuid
from unittest import TestCase
from unittest.mock import MagicMock, patch

import settings
from elasticsearch import Elasticsearch
from tests_es_util import TestsEsUtil

from articles_popular import ArticlesPopular
from tests_util import TestsUtil
import json


class TestArticlesPopular(TestCase):
    dynamodb = TestsUtil.get_dynamodb_client()
    elasticsearch = Elasticsearch(
        hosts=[{'host': 'localhost'}]
    )

    def setUp(self):
        TestsUtil.set_all_tables_name_to_env()
        TestsEsUtil.delete_alias(self.elasticsearch, settings.ARTICLE_SCORE_INDEX_NAME)

        # 実際のIndexと挙動をなるべく合わせるためエイリアスを利用している。
        index_name = settings.ARTICLE_SCORE_INDEX_NAME + str(uuid.uuid4())
        self.elasticsearch.indices.create(index=index_name)
        self.elasticsearch.indices.put_alias(index_name, settings.ARTICLE_SCORE_INDEX_NAME)

        article_info_items = [
            {
                'article_id': 'testid000001',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title02',
                'overview': 'overview02',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 12,
                'sort_key': 1520150272000001,
                'price': 100
            },
            {
                'article_id': 'testid000002',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title03',
                'overview': 'overview03',
                'status': 'public',
                'topic': 'fashion',
                'article_score': 18,
                'sort_key': 1520150272000002
            },
            {
                'article_id': 'testid000003',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title04',
                'overview': 'overview04',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 6,
                'sort_key': 1520150272000003
            },
            {
                'article_id': 'testid000004',
                'user_id': 'keillera',
                'created_at': 1520150272,
                'title': 'title05',
                'overview': 'overview05',
                'status': 'public',
                'topic': 'game',
                'article_score': 10,
                'sort_key': 1520150272000003
            }
        ]

        for article_info in article_info_items:
            self.elasticsearch.index(
                index=settings.ARTICLE_SCORE_INDEX_NAME,
                doc_type="article_score",
                id=article_info['article_id'],
                body=article_info
            )

        self.elasticsearch.indices.refresh(settings.ARTICLE_SCORE_INDEX_NAME)

        topic_items = [
            {'name': 'crypto', 'order': 1, 'index_hash_key': settings.TOPIC_INDEX_HASH_KEY},
            {'name': 'fashion', 'order': 2, 'index_hash_key': settings.TOPIC_INDEX_HASH_KEY},
            {'name': 'food', 'order': 3, 'index_hash_key': settings.TOPIC_INDEX_HASH_KEY}
        ]
        TestsUtil.create_table(self.dynamodb, os.environ['TOPIC_TABLE_NAME'], topic_items)

        TestsUtil.create_table(self.dynamodb, os.environ['SCREENED_ARTICLE_TABLE_NAME'], [])

    def tearDown(self):
        TestsUtil.delete_all_tables(self.dynamodb)

    def assert_bad_request(self, params):
        function = ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch)
        response = function.main()

        self.assertEqual(response['statusCode'], 400)

    def test_main_ok(self):
        params = {
            'queryStringParameters': {
                'limit': '3'
            }
        }

        response = ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch).main()

        expected_items = [
            {
                'article_id': 'testid000002',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title03',
                'overview': 'overview03',
                'status': 'public',
                'topic': 'fashion',
                'article_score': 18,
                'sort_key': 1520150272000002
            },
            {
                'article_id': 'testid000001',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title02',
                'overview': 'overview02',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 12,
                'sort_key': 1520150272000001,
                'price': 100
            },
            {
                'article_id': 'testid000004',
                'user_id': 'keillera',
                'created_at': 1520150272,
                'title': 'title05',
                'overview': 'overview05',
                'status': 'public',
                'topic': 'game',
                'article_score': 10,
                'sort_key': 1520150272000003
            }
        ]

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body'])['Items'], expected_items)

    def test_main_ok_exists_blacklisted_user(self):
        # blacklist のユーザ追加
        params = {
            'article_type': 'write_blacklisted',
            'users': ['keillera']
        }
        screened_article_table = self.dynamodb.Table(os.environ['SCREENED_ARTICLE_TABLE_NAME'])
        screened_article_table.put_item(Item=params)

        params = {
            'queryStringParameters': {
                'limit': '3'
            }
        }
        response = ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch).main()

        expected_items = [
            {
                'article_id': 'testid000002',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title03',
                'overview': 'overview03',
                'status': 'public',
                'topic': 'fashion',
                'article_score': 18,
                'sort_key': 1520150272000002
            },
            {
                'article_id': 'testid000001',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title02',
                'overview': 'overview02',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 12,
                'sort_key': 1520150272000001,
                'price': 100
            },
            {
                'article_id': 'testid000003',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title04',
                'overview': 'overview04',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 6,
                'sort_key': 1520150272000003
            }
        ]

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body'])['Items'], expected_items)

    def test_main_ok_with_no_limit(self):
        for i in range(21):
            self.elasticsearch.index(
                index=settings.ARTICLE_SCORE_INDEX_NAME,
                doc_type="article_score",
                id='test_limit_number' + str(i),
                body={
                    'article_id': 'test_limit_number' + str(i),
                    'user_id': 'matsumatsu20',
                    'created_at': 1520150272,
                    'title': 'title03',
                    'overview': 'overview03',
                    'status': 'public',
                    'topic': 'crypto',
                    'article_score': 30,
                    'sort_key': 1520150273000000 + i
                }
            )

        self.elasticsearch.indices.refresh(settings.ARTICLE_SCORE_INDEX_NAME)

        params = {
            'queryStringParameters': None
        }
        response = ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch).main()

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(json.loads(response['body'])['Items']), 20)

    def test_main_ok_with_topic(self):
        params = {
            'queryStringParameters': {
                'topic': 'crypto'
            }
        }

        response = ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch).main()

        expected_items = [
            {
                'article_id': 'testid000001',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title02',
                'overview': 'overview02',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 12,
                'sort_key': 1520150272000001,
                'price': 100
            },
            {
                'article_id': 'testid000003',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title04',
                'overview': 'overview04',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 6,
                'sort_key': 1520150272000003
            }
        ]

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body'])['Items'], expected_items)

    def test_main_ok_with_page(self):
        params = {
            'queryStringParameters': {
                'limit': '2',
                'page': '2'
            }
        }

        response = ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch).main()

        expected_items = [
            {
                'article_id': 'testid000004',
                'article_score': 10,
                'created_at': 1520150272,
                'overview': 'overview05',
                'sort_key': 1520150272000003,
                'status': 'public',
                'title': 'title05',
                'topic': 'game',
                'user_id': 'keillera'
            },
            {
                'article_id': 'testid000003',
                'user_id': 'matsumatsu20',
                'created_at': 1520150272,
                'title': 'title04',
                'overview': 'overview04',
                'status': 'public',
                'topic': 'crypto',
                'article_score': 6,
                'sort_key': 1520150272000003
            }
        ]

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body'])['Items'], expected_items)

    def test_main_with_no_index(self):
        TestsEsUtil.delete_alias(self.elasticsearch, settings.ARTICLE_SCORE_INDEX_NAME)
        params = {
            'queryStringParameters': {
                'limit': '2'
            }
        }

        response = ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch).main()

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body'])['Items'], [])

    def test_call_validate_topic(self):
        params = {
            'queryStringParameters': {
                'topic': 'crypto'
            }
        }

        mock_lib = MagicMock()
        with patch('articles_popular.DBUtil', mock_lib):
            ArticlesPopular(params, {}, dynamodb=self.dynamodb, elasticsearch=self.elasticsearch).main()

            self.assertTrue(mock_lib.validate_topic.called)
            args, kwargs = mock_lib.validate_topic.call_args
            self.assertTrue(args[0])
            self.assertEqual(args[1], 'crypto')

    def test_validation_limit_type(self):
        params = {
            'queryStringParameters': {
                'limit': 'ALIS'
            }
        }

        self.assert_bad_request(params)

    def test_validation_limit_max(self):
        params = {
            'queryStringParameters': {
                'limit': '101'
            }
        }

        self.assert_bad_request(params)

    def test_validation_limit_min(self):
        params = {
            'queryStringParameters': {
                'limit': '0'
            }
        }

        self.assert_bad_request(params)

    def test_validation_topic_max(self):
        params = {
            'queryStringParameters': {
                'topic': 'A' * 21
            }
        }

        self.assert_bad_request(params)

    def test_validation_page_type(self):
        params = {
            'queryStringParameters': {
                'page': 'A' * 21
            }
        }

        self.assert_bad_request(params)

    def test_validation_page_max(self):
        params = {
            'queryStringParameters': {
                'page': '100001'
            }
        }

        self.assert_bad_request(params)

    def test_validation_page_min(self):
        params = {
            'queryStringParameters': {
                'page': '0'
            }
        }

        self.assert_bad_request(params)
