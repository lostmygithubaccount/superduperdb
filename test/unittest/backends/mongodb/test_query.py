import random
from test.db_config import DBConfig

import numpy as np
import pytest

from superduperdb.backends.mongodb import query as q
from superduperdb.backends.mongodb.query import Collection
from superduperdb.base.config import BytesEncoding
from superduperdb.base.document import Document
from superduperdb.components.schema import Schema
from superduperdb.ext.numpy.encoder import array


@pytest.fixture
def schema(request):
    bytes_encoding = request.param if hasattr(request, 'param') else None

    array_tensor = array("float64", shape=(32,), bytes_encoding=bytes_encoding)
    schema = Schema(
        identifier=f'documents-{bytes_encoding}',
        fields={
            "x": array_tensor,
            "z": array_tensor,
        },
    )
    return schema


@pytest.mark.parametrize("db", [DBConfig.mongodb_empty], indirect=True)
def test_mongo_without_schema(db):
    collection_name = "documents"
    array_tensor = array("float64", shape=(32,))
    db.add(array_tensor)
    data = []

    for id_ in range(5):
        x = np.random.rand(32)
        y = int(random.random() > 0.5)
        z = np.random.randn(32)
        data.append(
            Document(
                {
                    "id": id_,
                    "x": array_tensor(x),
                    "y": y,
                    "z": array_tensor(z),
                }
            )
        )

    db.execute(
        Collection(collection_name).insert_many(data),
    )
    collection = Collection(collection_name)
    r = collection.find_one().execute(db)
    rs = list(collection.find().execute(db))

    rs = sorted(rs, key=lambda x: x['id'])

    assert np.array_equal(r['x'].x, data[0]['x'].x)
    assert np.array_equal(r['z'].x, data[0]['z'].x)

    assert np.array_equal(rs[0]['x'].x, data[0]['x'].x)
    assert np.array_equal(rs[0]['z'].x, data[0]['z'].x)


@pytest.mark.parametrize("db", [DBConfig.mongodb_empty], indirect=True)
@pytest.mark.parametrize(
    "schema", [BytesEncoding.BASE64, BytesEncoding.BYTES], indirect=True
)
def test_mongo_schema(db, schema):
    collection_name = "documents"
    data = []

    for id_ in range(5):
        x = np.random.rand(32)
        y = int(random.random() > 0.5)
        z = np.random.randn(32)
        data.append(
            Document(
                {
                    "id": id_,
                    "x": x,
                    "y": y,
                    "z": z,
                }
            )
        )

    db.add(schema)

    db.execute(
        Collection(collection_name).insert_many(data, schema=schema.identifier),
    )
    collection = Collection(collection_name)
    r = collection.find_one().execute(db)
    rs = list(collection.find().execute(db))

    rs = sorted(rs, key=lambda x: x['id'])

    assert np.array_equal(r['x'], data[0]['x'])
    assert np.array_equal(r['z'], data[0]['z'])

    assert np.array_equal(rs[0]['x'], data[0]['x'])
    assert np.array_equal(rs[0]['z'], data[0]['z'])


def test_select_missing_outputs(db):
    docs = list(db.execute(q.Collection('documents').find({}, {'_id': 1})))
    ids = [r['_id'] for r in docs[: len(docs) // 2]]
    db.execute(
        q.Collection('documents').update_many(
            {'_id': {'$in': ids}},
            Document({'$set': {'_outputs.x::test_model_output::0::0': 'test'}}),
        )
    )
    select = q.Collection('documents').find({}, {'_id': 1})
    modified_select = select.select_ids_of_missing_outputs('x::test_model_output::0::0')
    out = list(db.execute(modified_select))
    assert len(out) == (len(docs) - len(ids))
