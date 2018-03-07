# -*- coding: utf-8 -*-
import os
import sys
import boto3
import json
import logging
import decimal
import traceback
import settings
from boto3.dynamodb.conditions import Key, Attr
from jsonschema import validate, ValidationError
from decimal_encoder import DecimalEncoder


class ArticleInfoRecent(object):
    def __init__(self, event, context, dynamodb):
        self.event = event
        self.context = context
        self.dynamodb = dynamodb

    def main(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        schema = {
            'type': 'object',
            'properties': {
                'limit': settings.parameters['limit'],
                'article_id': settings.parameters['article_id'],
                'created_at': settings.parameters['sort_key']
            }
        }

        try:
            params = self.event['queryStringParameters']
            self.__cast_parameter_to_int(params, schema)
            validate(params, schema)

            dynamo_tbl = self.dynamodb.Table(os.environ['ARTICLE_INFO_TABLE_NAME'])

            query_params = {
                "Limit": int(params.get("limit")),
                "IndexName": "status-sort_key-index",
                "KeyConditionExpression": Key("status").eq("published"),
                "ScanIndexForward": False
            }

            if params.get("article_id") is not None and params.get("created_at") is not None:
                LastEvaluatedKey = {
                    "status": "published",
                    "article_id": params.get("article_id"),
                    "created_at": params.get("created_at")
                }

                query_params.update({"ExclusiveStartKey": LastEvaluatedKey})

            responce = dynamo_tbl.query(**query_params)

            return {
                "statusCode": 200,
                "body": json.dumps(responce, cls=DecimalEncoder)
            };
        except ValidationError as err:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Invalid parameter: {0}".format(err)})
            };

        except Exception as err:
            logger.fatal(err)
            traceback.print_exc()

            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Internal server error: {0}".format(err)})
            };


    def __cast_parameter_to_int(self, params, schema):
        properties = schema['properties']

        for key, value in params.items():
            if properties.get(key) is None:
                continue

            if properties[key]['type'] == 'integer' and value.isdigit():
                params[key] = int(value)
