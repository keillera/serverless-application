# -*- coding: utf-8 -*-
import os
import settings
import uuid
import json
import base64, hmac, hashlib
from db_util import DBUtil
from lambda_base import LambdaBase
from jsonschema import validate
from user_util import UserUtil
from datetime import datetime, timedelta


class MeArticlesImagesCreate(LambdaBase):
    def get_schema(self):
        return {
            'type': 'object',
            'properties': {
                'article_id': settings.parameters['article_id'],
                'image_size': settings.parameters['image_size']
            },
            'required': ['article_id', 'image_size']
        }

    def get_headers_schema(self):
        return {
            'type': 'object',
            "oneOf": [{
                'properties': {
                    'content-type': {
                        'type': 'string',
                        'enum': [
                            'image/gif',
                            'image/jpeg',
                            'image/png'
                        ]
                    }
                },
                'required': ['content-type']
            }, {
                'properties': {
                    'Content-Type': {
                        'type': 'string',
                        'enum': [
                            'image/gif',
                            'image/jpeg',
                            'image/png'
                        ]
                    }
                },
                'required': ['Content-Type']
            }]
        }

    def validate_params(self):
        UserUtil.verified_phone_and_email(self.event)
        # single
        # params
        validate(self.params, self.get_schema())
        # headers
        validate(self.event.get('headers'), self.get_headers_schema())
        # relation
        DBUtil.validate_article_existence(
            self.dynamodb,
            self.event['pathParameters']['article_id'],
            user_id=self.event['requestContext']['authorizer']['claims']['cognito:username']
        )

    def exec_main_proc(self):
        # post policy の有効期限（5分）
        expiration = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # S3 のファイルパス（key）を設定
        content_type = self.headers.get('content-type') \
            if self.headers.get('content-type') is not None else self.headers.get('Content-Type')
        ext = content_type.split('/')[1]
        user_id = self.event['requestContext']['authorizer']['claims']['cognito:username']
        key = settings.S3_ARTICLES_IMAGES_PATH + \
              user_id + '/' + self.params['article_id'] + '/' + str(uuid.uuid4()) + '.' + ext

        # policy を作成
        target_policy_json = json.dumps({
            'expiration': expiration,
            'conditions': [
                {'bucket': os.environ['DIST_S3_BUCKET_NAME']},
                {'key': key},
                {'Content-Type': content_type},
                {'acl': 'private'},
                ['content-length-range', 1, 10485760]
            ]
        })
        policy = base64.b64encode(target_policy_json.encode('ascii'))

        # signature を作成
        signature_hmac = hmac.new(os.environ['S3_SECRET_KEY'].encode('ascii'), policy, hashlib.sha1)
        signature = base64.b64encode(signature_hmac.digest())

        # 戻り値を作成
        # バイナリ形式は json に対応していないため、ascii でデコードしたものを返却する。
        return_body = {
            'image_url': 'https://' + os.environ['DOMAIN'] + '/' + key,
            'upload_url': 'https://' + os.environ['DIST_S3_BUCKET_NAME'] + '.s3.amazonaws.com/',
            'S3_ACCESS_KEY': os.environ['S3_ACCESS_KEY'],
            'signature': signature.decode('ascii'),
            'policy': policy.decode('ascii'),
            'key': key
        }

        return {
            'statusCode': 200,
            'body': json.dumps(return_body)
        }
