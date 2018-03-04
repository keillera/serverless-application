import yaml
import os
import boto3
import json
from unittest import TestCase
from article_info_recent import ArticleInfoRecent

class TestArticleInfoRecent(TestCase):
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:4569/')

    @classmethod
    def setUpClass(cls):
        f = open("../../packaged-template.yaml", "r+")
        template = yaml.load(f)
        f.close()

        create_params = {
            'TableName': 'ArticleInfo'
        }
        create_params.update(template['Resources']['ArticleInfo']['Properties'])

        TestArticleInfoRecent.dynamodb.create_table(**create_params)

        os.environ['ARTICLE_INFO_TABLE_NAME'] = 'ArticleInfo'

    @classmethod
    def tearDownClass(cls):
        table = TestArticleInfoRecent.dynamodb.Table('ArticleInfo')
        table.delete()

    def test_main_ok(self):
        table = TestArticleInfoRecent.dynamodb.Table('ArticleInfo')

        items = [
            {
                'article_id': 'test_article_id1',
                'status': 'published',
                'sort_key': 1520150272000000
            },
            {
                'article_id': 'test_article_id2',
                'status': 'published',
                'sort_key': 1520150272000001
            }
        ]

        for item in items:
            table.put_item(Item=item)

        params = {
            'queryStringParameters': {
                'limit': '2'
            }
        }

        function = ArticleInfoRecent(params, {}, self.dynamodb)

        response = function.main()

        expected_item_list = [
            {
                'article_id': 'test_article_id2',
                'status': 'published',
                'sort_key': 1520150272000001
            },
            {
                'article_id': 'test_article_id1',
                'status': 'published',
                'sort_key': 1520150272000000
            }
        ]

        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(json.loads(response['body'])['Items'], expected_item_list)

    def test_main_ng(self):
        params = {
            'queryStringParameters': {
                'limit': '101'
            }
        }

        function = ArticleInfoRecent(params, {}, self.dynamodb)

        response = function.main()

        self.assertEqual(response['statusCode'], 400)
