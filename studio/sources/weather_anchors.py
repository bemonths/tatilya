"""30A weather sampling points, NOT canonical neighborhood centers.

Coordinates/external IDs: live Visit South Walton beach access dataset (53 coastal
records). West/central/east selected by longitude ordering; these are corridor
samples for NWS point/grid forecasts, not neighborhood boundaries or centroids.
"""
ANCHOR_PROVENANCE = {
    "source_url": "https://www.visitsouthwalton.com/beach-bay-access-locations/",
    "selection": "53 kıyı erişim kaydının boylam sıralamasından batı / orta / doğu örnekleri",
    "scope": "30A koridoru için hava örnek noktaları; canonical mahalle merkezleri değildir.",
}
ANCHORS = (
    {"anchor_key": "west", "label": "Batı 30A", "source_beach_name": "Stallworth Preserve",
     "source_beach_external_id": "5c81ab02f836f9166348e96c", "latitude": 30.35548, "longitude": -86.2638},
    {"anchor_key": "central", "label": "Orta 30A", "source_beach_name": "Holly - 24",
     "source_beach_external_id": "5c81a5acf836f90dc03cccca", "latitude": 30.3167, "longitude": -86.12845},
    {"anchor_key": "east", "label": "Doğu 30A", "source_beach_name": "Lupine - 1",
     "source_beach_external_id": "5c81a6a2f836f9166348e961", "latitude": 30.2713, "longitude": -85.99579},
)
