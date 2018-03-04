# -*- coding: utf-8 -*-
import boto3

dynamodb =  boto3.resource('dynamodb')

def lambda_handler(event, context):
    article_info_recent = ArticleInfoRecent(event, context, dynamodb)
    article_info_recent.main()
