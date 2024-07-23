# extent := "-124.733 45.543 -116.917 49.005" # WA
extent := "-114.052 36.998 -109.041 42.002" # UT

all: roads trails

roads:
    ogr2ogr -f GeoJSON -spat_srs EPSG:4326 -spat {{extent}} \
        RoadCore.geojson ~/Downloads/S_USA.RoadCore_FS.gdb

    jq -c '.features[]' RoadCore.geojson > RoadCore.ndjson
    python roads-to-osm.py < RoadCore.ndjson > RoadCore.osm.ndjson
    jq -cs '{ type: "FeatureCollection", features: . }' RoadCore.osm.ndjson > RoadCore.osm.geojson

trails:
    ogr2ogr -f GeoJSON -spat_srs EPSG:4326 -spat {{extent}} \
        TrailNFS.geojson ~/Downloads/S_USA.TrailNFS_Publish.gdb

    jq -c '.features[]' TrailNFS.geojson > TrailNFS.ndjson
    python trails-to-osm.py < TrailNFS.ndjson > TrailNFS.osm.ndjson
    jq -cs '{ type: "FeatureCollection", features: . }' TrailNFS.osm.ndjson > TrailNFS.osm.geojson

recsites:
    ogr2ogr -f GeoJSON -spat_srs EPSG:4326 -spat {{extent}} \
        RecOpportunities.geojson ~/Downloads/Recreation_Opportunities_\(Feature_Layer\).geojson

    jq -c '.features[]' RecOpportunities.geojson > RecOpportunities.ndjson
    python recsites-to-osm.py < RecOpportunities.ndjson > RecOpportunities.osm.ndjson
    jq -cs '{ type: "FeatureCollection", features: . }' RecOpportunities.osm.ndjson > RecOpportunities.osm.geojson
