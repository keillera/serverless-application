parameters = {
    'limit': {
        'type': 'integer',
        'minimum': 1,
        'maximum': 100
    },
    'article_id': {
        'type': 'string',
        "minLength": 10,
        "maxLength": 20
    },
    'sort_key': {
        'type': 'integer',
        "minLength": 16,
        "maxLength": 16
    }
}
