"""Documented representative points. These are city-level markers, not boundaries."""

from decimal import Decimal

# Retrieved 2026-11-24 from OpenStreetMap Nominatim
# (https://nominatim.openstreetmap.org) search:
# city=Meerut, state=Uttar Pradesh, country=India, format=jsonv2.
# Result: display_name "Meerut, Uttar Pradesh, 250001, India",
# OSM class/type city, osm_id 571773704, lat 28.9963296, lon 77.7061915.
# Rounded to the Area model's 6 decimal places. This is a representative
# populated-place coordinate for city-level weather interpolation, not a
# municipal polygon or ward boundary.
MEERUT_CITY_POINT = {
    "source_name": "OpenStreetMap Nominatim",
    "source_url": (
        "https://nominatim.openstreetmap.org/search"
        "?city=Meerut&state=Uttar+Pradesh&country=India&format=jsonv2"
    ),
    "retrieved_on": "2026-11-24",
    "osm_id": 571773704,
    "display_name": "Meerut, Uttar Pradesh, 250001, India",
    "latitude": Decimal("28.996330"),
    "longitude": Decimal("77.706192"),
    "limitation": (
        "Point marker for Meerut city-level analysis only. Verified municipal "
        "or ward polygons are not available in this dataset."
    ),
}
