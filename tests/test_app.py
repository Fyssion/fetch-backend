import pytest

import fetch_backend


@pytest.fixture
async def client(aiohttp_client):
    # create an http client to our backend
    # and store sqlite db in memory
    return await aiohttp_client(fetch_backend.create_app(':memory:'))


async def test_index(client):
    """Tests the index of our app"""

    resp = await client.get('/')
    assert resp.status == 200
    text = await resp.text()
    assert text == f'fetch backend v{fetch_backend.__version__}'


async def test_add(client):
    """Tests the add endpoint using the example in the PDF"""

    TRANSACTION = {"payer": "DANNON", "points": 5000, "timestamp": "2020-11-02T14:00:00Z"}
    resp = await client.post('/add', json=TRANSACTION)
    assert resp.status == 200


async def test_spend_fail(client):
    """Tests a failure of the spend endpoint with a too large point total"""

    # first add a transaction to the db
    TRANSACTION = {"payer": "DANNON", "points": 5000, "timestamp": "2020-11-02T14:00:00Z"}
    resp = await client.post('/add', json=TRANSACTION)
    assert resp.status == 200

    # then spend too many points
    resp = await client.post('/spend', json={'points': 10000})
    assert resp.status == 400

    error = await resp.text()
    assert error == 'You are trying to spend 10000 points when you have 5000 points.'


async def test_all(client):
    """Tests all endpoints using the provided test in the PDF"""

    # first add the transactions
    TRANSACTIONS_TO_ADD = [
        {"payer": "DANNON", "points": 300, "timestamp": "2022-10-31T10:00:00Z"},
        {"payer": "UNILEVER", "points": 200, "timestamp": "2022-10-31T11:00:00Z"},
        {"payer": "DANNON", "points": -200, "timestamp": "2022-10-31T15:00:00Z"},
        {"payer": "MILLER COORS", "points": 10000, "timestamp": "2022-11-01T14:00:00Z"},
        {"payer": "DANNON", "points": 1000, "timestamp": "2022-11-02T14:00:00Z"},
    ]

    for transaction in TRANSACTIONS_TO_ADD:
        resp = await client.post('/add', json=transaction)
        assert resp.status == 200

    # then spend the points
    resp = await client.post('/spend', json={'points': 5000})
    assert resp.status == 200

    data = await resp.json()
    assert data == [
        {
            'payer': 'DANNON',
            'points': -100,
        },
        {
            'payer': 'UNILEVER',
            'points': -200,
        },
        {
            'payer': 'MILLER COORS',
            'points': -4700,
        },
    ]

    # then ensure the balance is correct
    resp = await client.get('/balance')
    assert resp.status == 200

    data = await resp.json()
    assert data == {"DANNON": 1000, "UNILEVER": 0, "MILLER COORS": 5300}
