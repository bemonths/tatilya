"""Idempotent connector default repair; never an edit to user-authored fields."""
from .catalog import SEEDS
from .sources.restaurants import RestaurantsConnector, SOURCE_URL

OLD_RESTAURANT_NOTE = 'Restoran dizini. Menü ve fiyatlar için işletmelerin kendi sayfaları ayrıca incelenecek.'
RESTAURANT_NOTE = next(seed[3] for seed in SEEDS if seed[1] == SOURCE_URL)


def reconcile_connector_defaults(con):
    """Caller owns transaction. Only untouched defaults on matching sources change."""
    connector = RestaurantsConnector()
    candidates = con.execute(
        "SELECT * FROM sources WHERE method=? OR notes=?",
        ('Belirlenecek', OLD_RESTAURANT_NOTE)).fetchall()
    for source in candidates:
        if not connector.supports(dict(source)):
            continue
        changes = {}
        if source['method'] == 'Belirlenecek':
            changes['method'] = connector.method
        if source['notes'] == OLD_RESTAURANT_NOTE:
            changes['notes'] = RESTAURANT_NOTE
        if changes:
            assignments = ','.join(f'{field}=?' for field in changes)
            con.execute(f'UPDATE sources SET {assignments} WHERE id=?', (*changes.values(), source['id']))
