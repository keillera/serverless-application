# -*- coding: utf-8 -*-
import os
import settings
import json
import requests
import time
from time_util import TimeUtil
from aws_requests_auth.aws_auth import AWSRequestsAuth
from jsonschema import validate
from lambda_base import LambdaBase
from jsonschema import ValidationError
from exceptions import SendTransactionError
from user_util import UserUtil


class MeWalletTokenSend(LambdaBase):

    def get_schema(self):
        return {
            'type': 'object',
            'properties': {
                'recipient_eth_address': settings.parameters['recipient_eth_address'],
                'send_value': settings.parameters['send_value'],
            },
            'required': ['recipient_eth_address', 'send_value']
        }

    def validate_params(self):
        UserUtil.verified_phone_and_email(self.event)

        # send_value について数値でのチェックを行うため、int に変換
        try:
            self.params['send_value'] = int(self.params['send_value'])
        except ValueError:
            raise ValidationError('Tip value must be numeric')
        validate(self.params, self.get_schema())

    def exec_main_proc(self):
        from_user_eth_address = self.event['requestContext']['authorizer']['claims']['custom:private_eth_address']
        recipient_eth_address = self.params['recipient_eth_address']
        send_value = self.params['send_value']

        # approve
        approve_transaction_hash = self.__approve(from_user_eth_address, send_value)

        withdraw_transaction_hash = self.__withdraw(from_user_eth_address, recipient_eth_address, send_value)

        # create tip info
        self.__create_send_info(approve_transaction_hash, withdraw_transaction_hash)

        return {
            'statusCode': 200
        }

    @staticmethod
    def __approve(from_user_eth_address, send_value):
        headers = {'content-type': 'application/json'}
        payload = json.dumps(
            {
                'from_user_eth_address': from_user_eth_address,
                'spender_eth_address': os.environ['PRIVATE_CHAIN_BRIDGE_ADDRESS'],
                'value': format(send_value, '064x')
            }
        )
        auth = AWSRequestsAuth(aws_access_key=os.environ['PRIVATE_CHAIN_AWS_ACCESS_KEY'],
                               aws_secret_access_key=os.environ['PRIVATE_CHAIN_AWS_SECRET_ACCESS_KEY'],
                               aws_host=os.environ['PRIVATE_CHAIN_EXECUTE_API_HOST'],
                               aws_region='ap-northeast-1',
                               aws_service='execute-api')
        response = requests.post('https://' + os.environ['PRIVATE_CHAIN_EXECUTE_API_HOST'] +
                                 '/production/wallet/approve', auth=auth, headers=headers, data=payload)

        # exists error
        if json.loads(response.text).get('error'):
            raise SendTransactionError(json.loads(response.text).get('error'))

        # return transaction hash
        return json.dumps(json.loads(response.text).get('result')).replace('"', '')

    @staticmethod
    def __withdraw(from_user_eth_address, recipient_eth_address, send_value):
        headers = {'content-type': 'application/json'}
        payload = json.dumps(
            {
                'from_user_eth_address': from_user_eth_address,
                'recipient_eth_address': recipient_eth_address,
                'amount': format(send_value, '064x')
            }
        )
        auth = AWSRequestsAuth(aws_access_key=os.environ['PRIVATE_CHAIN_AWS_ACCESS_KEY'],
                               aws_secret_access_key=os.environ['PRIVATE_CHAIN_AWS_SECRET_ACCESS_KEY'],
                               aws_host=os.environ['PRIVATE_CHAIN_EXECUTE_API_HOST'],
                               aws_region='ap-northeast-1',
                               aws_service='execute-api')
        response = requests.post('https://' + os.environ['PRIVATE_CHAIN_EXECUTE_API_HOST'] +
                                 '/production/wallet/withdraw', auth=auth, headers=headers, data=payload)

        # exists error
        if json.loads(response.text).get('error'):
            raise SendTransactionError(json.loads(response.text).get('error'))

        # return transaction hash
        return json.dumps(json.loads(response.text).get('result')).replace('"', '')

    def __create_send_info(self, approve_transaction_hash, withdraw_transaction_hash):
        token_send_table = self.dynamodb.Table(os.environ['TOKEN_SEND_TABLE_NAME'])

        sort_key = TimeUtil.generate_sort_key()
        user_id = self.event['requestContext']['authorizer']['claims']['cognito:username']

        send_info = {
            'user_id': user_id,
            'send_value': self.params['send_value'],
            'approve_transaction': approve_transaction_hash,
            'withdraw_transaction_hash': withdraw_transaction_hash,
            'uncompleted': 1,
            'sort_key': sort_key,
            'created_at': int(time.time())
        }

        token_send_table.put_item(
            Item=send_info,
            ConditionExpression='attribute_not_exists(user_id)'
        )
