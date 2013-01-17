# -*- coding: utf-8 -*-

from tori.centre      import services
from tori.db.fixture  import Fixture

def auto_load_mongodb():
    dataset = {
        'tori.security.collection.provider': {
            'google': { '_id': 1, 'name': 'Google' },
            'github': { '_id': 2, 'name': 'GitHub' }
        }
    }

    for service_id in dataset:
        repository = services.get(service_id)
        ''' :type repository: tori.db.odm.collection.Collection '''

        for alias in dataset[service_id]:
            criteria = dataset[service_id][alias]

            entity = repository.filter_one(**criteria)

            if entity:
                continue

            entity = repository.new_document(**criteria)

            repository.post(entity)
