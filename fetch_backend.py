from __future__ import annotations

import datetime
import logging
from collections import defaultdict

import asqlite
from aiohttp import web
from rich.logging import RichHandler

__version__ = '0.1.0'

# set up logging using rich's logging handler for pretty logs
log = logging.getLogger('fetch_backend')

logging.getLogger().setLevel(logging.INFO)
sh = RichHandler()
sh.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
logging.getLogger().addHandler(sh)

# set up routes table and db appkey for accessing the sqlite db
routes = web.RouteTableDef()
db = web.AppKey('db', asqlite.Pool)
db_path = web.AppKey('db_path', str)


@routes.get('/')
async def index(request: web.Request) -> web.StreamResponse:
    """Responds with the version of the app"""

    return web.Response(text=f'fetch backend v{__version__}')


@routes.post('/add')
async def add(request: web.Request) -> web.StreamResponse:
    """Adds a transaction to the database"""

    # resolve transaction fields from body
    data = await request.json()
    payer = data['payer']
    points = data['points']
    timestamp = data['timestamp']

    # insert transaction into database
    SQL = 'INSERT INTO transactions (payer, points, timestamp) VALUES (?, ?, ?)'
    async with request.app[db].acquire() as conn:
        await conn.execute(SQL, (payer, points, timestamp))

    # 200 succeeded
    return web.Response()


async def get_payer_points(conn: asqlite.Connection) -> dict[str, int]:
    """Helper function that returns a dict with point totals for each payer"""

    # we use a SQL query to resolve payer point totals
    QUERY = 'SELECT payer, SUM(points) FROM transactions GROUP BY payer'
    rows = await conn.fetchall(QUERY)
    # each row looks like a tuple of (payer, points), and dict.__init__
    # accepts a list of 2-tuples, so we'll convert the rows to a dict
    # for convenience
    return dict(rows)  # type: ignore


@routes.post('/spend')
async def spend(request: web.Request) -> web.StreamResponse:
    """Spends a user's points"""

    # resolve points to spend
    data = await request.json()
    points_to_spend = data['points']

    # for this we make two queries, one to get all transactions from the database,
    # and one to get each payer's point totals for calculating total point values
    ALL_TRANSACTIONS = 'SELECT payer, points FROM transactions ORDER BY timestamp ASC'
    async with request.app[db].acquire() as conn:
        transactions = await conn.fetchall(ALL_TRANSACTIONS)
        payer_points = await get_payer_points(conn)

    # sum up all payer points
    total_points = sum(payer_points.values())

    if points_to_spend > total_points:
        # trying to spend too many points
        return web.Response(
            text=f'You are trying to spend {points_to_spend} points when you have {total_points} points.',
            status=400,
        )

    # initialize dict to track points spent for each payer
    # the defaultdict will ensure all possible keys have a default value of 0
    # for conciseness of code
    spent_points: defaultdict[str, int] = defaultdict(int)
    # initialize remaining points to spend
    remaining_points = points_to_spend

    for payer, points in transactions:
        if remaining_points <= 0:
            # we've already spent all the points,
            # so we can exit the loop
            break

        # we need to determine how many points are available to spend
        available_points = min(
            # the number of points in the transaction is the limit
            points,
            # the total number of points remaining in the payer is the limit
            payer_points[payer] - spent_points[payer],
            # the total number of points remaining to spend is the limit
            remaining_points,
        )

        # add the spent points to the payer's spent points total
        spent_points[payer] += available_points
        # and subtract from the available points
        remaining_points -= available_points

    if remaining_points > 0:
        # we haven't spent all our points
        return web.Response(
            text=f'Unable to spend points. {remaining_points} points remaining.', status=400
        )

    # this is our response body
    response = []
    # these are the transaction values we need to insert into the database
    insertion_data = []
    # the current timestamp in iso format
    now = datetime.datetime.now().isoformat()

    for payer, points in spent_points.items():
        if points <= 0:
            # we don't need to track payers whose points have not
            # been spent
            continue

        insertion_data.append((payer, -points, now))
        response.append({'payer': payer, 'points': -points})

    # insert new transactions into the database
    SQL = 'INSERT INTO transactions (payer, points, timestamp) VALUES (?, ?, ?)'
    async with request.app[db].acquire() as conn:
        await conn.executemany(SQL, insertion_data)

    # return our response body
    return web.json_response(response)


@routes.get('/balance')
async def balance(request: web.Request) -> web.StreamResponse:
    """Get's the user's point balance"""

    # use our helper function to get payer point totals
    async with request.app[db].acquire() as conn:
        payer_points = await get_payer_points(conn)

    return web.json_response(payer_points)


async def db_context(app: web.Application):
    """aiohttp cleanup context for connecting to and closing the sqlite connection"""

    # this code runs on startup
    #
    # we connect to our sqlite database
    app[db] = await asqlite.create_pool(app[db_path])

    # and initialize it by executing the schema
    with open('schema.sql', 'r') as f:
        schema = f.read()

    async with app[db].acquire() as conn:
        await conn.execute(schema)

    # then yield for the web server to run
    yield

    # this code runs on shutdown
    await app[db].close()


def create_app(database_path: str = 'app.db') -> web.Application:
    """Creates and returns an aiohttp.web.Application with our configuration

    :param database_path: path to database file. defaults to "app.db"
    """

    app = web.Application()
    app[db_path] = database_path
    app.cleanup_ctx.append(db_context)  # manages our db connection
    app.add_routes(routes)
    return app


if __name__ == '__main__':
    web.run_app(create_app(), port=8000)
