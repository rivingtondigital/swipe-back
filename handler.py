import json
import boto3

client = boto3.client('s3')
BUCKET = 'flip.rdig.co'

class QSet:
    def __init__(self, name, choices, tags=None):
        self.name = name
        self.choices = choices
        if not tags:
            tags = []
        self.tags = tags
    
    @classmethod
    def set_list(cls):
        keys = [x['Key'] for x in client.list_objects(Bucket=BUCKET, Prefix='meta/')['Contents']]
        categories = [k.split('/')[-1].split('.')[0] for k in keys]
        return categories
   
    @classmethod
    def from_meta(cls, name):
        keyname = "meta/{}.json".format(name)
        obj = client.get_object(Bucket=BUCKET, Key=keyname)['Body'].read()
        data = json.loads(obj)
        return cls(data['name'], data['choices'], data['tags'])
        
    def write_meta(self):
        keyname = "meta/{}.json".format(self.name)
        data = {
            'tags': self.tags,
            'choices': self.choices,
            'name': self.name
        }
        client.put_object(Bucket=BUCKET, Key=keyname, Body=json.dumps(data))
        
    @staticmethod
    def get_unpaged(prefix):
        paginator = client.get_paginator('list_objects')
        page_iterator = paginator.paginate(Bucket=BUCKET, Prefix=prefix)        
        for page in page_iterator:
            if 'Contents' in page:
                keys = page['Contents']
                for key in keys:
                    if 'json' in key['Key']:
                        name = key['Key'].split('/')[-1]
                        yield name
    
    def get_cards(self):
        return self.get_unpaged('q_cards/{}'.format(self.name))
    
    def get_answered(self, user):
        return self.get_unpaged('answers/{}/{}'.format(self.name, user))
        
        
    def next_unanswered(self, user):
        answered = set(self.get_answered(user))
        for key in self.get_cards():
            if key not in answered:
                return self.to_card(key, user)
        
    def to_card(self, key, user):        
        key_path = "q_cards/{}/{}".format(self.name, key)
        data = client.get_object(Bucket=BUCKET, Key=key_path)['Body'].read()
        card = json.loads(data)
        return {
            'qcard': card,
            'user': user,
            'a_round': 1,
            'answer': None,
            's_name': self.name
        }
    
    @classmethod
    def set_answer(cls, card):
        key = "{}/{}/{}/{}/{}.json".format('answers',
                            card['s_name'], 
                            card['user'],
                            card['a_round'],
                            card['qcard']['name']
        )
        client.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(card))
        return key

#======================================================
# Views
#======================================================

def list_sets(event, context):
    data = {
        'Sets': QSet.set_list()
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(data)
    }

    return response

def get_card(event, context):
    path = event['pathParameters']
    q = path['qset']
    userid = path['userid']
    
    qset = QSet.from_meta(q)
    card = qset.next_unanswered(userid)

    
    response = {
        "statusCode": 200,
        "body": json.dumps(card)
    }

    return response

def answer_card(event, context):
    card = json.loads(event['body'])
    key = QSet.set_answer(card)
    print(key)

    return {
        "statusCode": 200,
        "body": 'OK'
    }


