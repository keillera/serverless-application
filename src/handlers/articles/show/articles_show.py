# -*- coding: utf-8 -*-
import os
import json
import settings
from db_util import DBUtil
from lambda_base import LambdaBase
from jsonschema import validate, ValidationError
from decimal_encoder import DecimalEncoder


class ArticlesShow(LambdaBase):
    def get_schema(self):
        return {
            'type': 'object',
            'properties': {
                'article_id': settings.parameters['article_id']
            },
            'required': ['article_id']
        }

    def validate_params(self):
        # single
        params = self.event.get('pathParameters')

        if params is None:
            raise ValidationError('pathParameters is required')

        validate(params, self.get_schema())
        # relation
        DBUtil.validate_article_existence(
            self.dynamodb,
            params['article_id'],
            status='public'
        )

    def exec_main_proc(self):
        params = self.event.get('pathParameters')

        article_info_table = self.dynamodb.Table(os.environ['ARTICLE_INFO_TABLE_NAME'])
        article_content_table = self.dynamodb.Table(os.environ['ARTICLE_CONTENT_TABLE_NAME'])

        article_info = article_info_table.get_item(Key={'article_id': params['article_id']}).get('Item')
        article_content = article_content_table.get_item(Key={'article_id': params['article_id']}).get('Item')

        if article_info is None or article_content is None:
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'Record Not Found'})
            }

        article_content.pop('paid_body', None)
        article_info.update(article_content)

        return {
            'statusCode': 200,
            'body': json.dumps(article_info, cls=DecimalEncoder)
        }
