"""
Reads USDA National Forest System Roads ('S_USA.RoadCore') data as newline-delimited
GeoJSON features from STDIN, converts attributes to OSM-compatible tags, and writes
the resulting GeoJSON features to STDOUT.
"""

import sys
import json

ABBREVIATIONS = {
    "N": "North",
    "S": "South",
    "E": "East",
    "W": "West",
    "MTN": "Mountian",
    "CG": "Campground",
    "CR": "Creek",
    "FK": "Fork",
    "LK": "Lake",
    "TS": "Timber Sale",
    "T.S.": "Timber Sale",
    "FY": "Fiscal Year",
}

BAD_WORDS = {
    # "Filler" words to delete from names
    "(FDR)",
}

BAD_NAMES = {
    # "Names" that should be considered equivalent to null values
    "NO NAME",
    "UNNAMED",
    "UN-NAMED",
    "UNKNOWN",
    "LOCAL",
    "MAJOR LOCAL",
    "HUC", # some roads near Rainier, meaning unknown
    "(FDR)", # Forest Development Road
    "MRS", # Minimum Road System
    "2B DECOMM'D", # to be decommissioned
    
}

def squeeze(string):
    """Replace any runs of whitespace in string with a single space"""
    return " ".join(string.split())

def highway(props):
    if props.get("FUNCTIONAL_CLASS") == "A - ARTERIAL":
        return "unclassified"
    else:
        return "track"
    
def name(props):
    name = props["NAME"]
    id = props["ID"]
    
    if not name or id in name or name in BAD_NAMES:
        return None

    name = squeeze(name.replace(".", " ")).strip()

    if name.isnumeric() or name.startswith("FR") and name[2:].strip().isnumeric():
        return None

    words = []
    for word in name.split():
        word = word.upper()
        if word in BAD_WORDS:
            continue
        elif word in ABBREVIATIONS:
            word = ABBREVIATIONS[word]
        else:
            word = word[0] + word[1:].lower()
        words.append(word)

    if not words:
        return None

    if words[-1] != "Road":
        words.append("Road") # FIXME or " Trail"
        
    return " ".join(words)

def ref(props):
    ref = props["ID"]
    
    if len(ref) == 7:
        if ref.endswith("00000"):
            return "NF " + ref[:2]
        elif ref.endswith("000"):
            return "FR " + ref[:4]
        else:
            return "FR " + ref[:4] + "-" + ref[4:]
    else:
        return "FR " + ref

def operator(props):
    if props["JURISDICTION"] == "FS - FOREST SERVICE":
        return "US Forest Service"
    else:
        return None

SURFACE_MAP = {
    "AC - ASPHALT": "asphalt",
    "AGG - CRUSHED AGGREGATE OR GRAVEL": "gravel",
    "BST - BITUMINOUS SURFACE TREATMENT": "chipseal",
    "CSOIL - COMPACTED SOIL": "compacted",
    "IMP - IMPROVED NATIVE MATERIAL": "gravel", # more like gravel than ground
    "NAT - NATIVE MATERIAL": "ground",
    "P - PAVED": "paved",
    "PCC - PORTLAND CEMENT CONCRETE": "concrete",
}

def surface(props):
    return SURFACE_MAP.get(props.get("SURFACE_TYPE"))

SMOOTHNESS_MAP = {
    # See https://wiki.openstreetmap.org/wiki/Key:smoothness
    # and https://www.fs.usda.gov/Internet/FSE_DOCUMENTS/stelprd3793545.pdf
    
    # Level 5 roads are almost always paved (usually with asphalt or chipseal) and provide
    # a high degree of comfort and convenience for travelers in passenger cars.
    "5 - HIGH DEGREE OF USER COMFORT": "good",
    # Level 4 roads are usually compacted and provide "moderate comfort at moderate speeds".
    "4 - MODERATE DEGREE OF USER COMFORT": "intermediate",
    # Level 3 roads are passable by prudent drivers in a passenger car. Comfort and convenience
    # are "not a priority".
    "3 - SUITABLE FOR PASSENGER CARS": "bad",
    # Level 2 roads are open to use by high clearance vehicles. "Passenger car traffic, user
    # comfort, and user convenience are not considerations".
    "2 - HIGH CLEARANCE VEHICLES": "very_bad",
    # Level 1 roads may technically be any type of road that are closed to vehicle traffic for
    # for an extended period, so we can't be sure about their smoothness. In practice most L1
    # roads are severely degraded and impassable by any vehicle.
    "1 - BASIC CUSTODIAL CARE (CLOSED)": None,
}

def smoothness(props):
    return SMOOTHNESS_MAP.get(props.get("OPER_MAINT_LEVEL"))

def motor_vehicle(props):
    if props.get("OPENFORUSETO") != "ALL" or props.get("OPER_MAINT_LEVEL") == "1 - BASIC CUSTODIAL CARE (CLOSED)":
        return "no"
    else:
        return "yes"

def disused(props):
    return props.get("OBJECTIVE_MAINT_LEVEL") == "D - DECOMMISSION"

def lanes(props):
    lanes = props.get("LANES")
    if lanes and lanes[0].isnumeric():
        return lanes[0]
    else:
        return None
        

def properties_to_osm(props):
    """Converts a feature properties dict to OSM tags"""
    # tags = {**props}
    tags = {}

    tags["highway"] = highway(props)
    tags["name"] = name(props)
    tags["ref"] = ref(props)
    tags["operator"] = operator(props)
    tags["surface"] = surface(props)
    tags["smoothness"] = smoothness(props)
    tags["lanes"] = lanes(props)

    if disused(props):
        tags["disused"] = "yes"

    if not motor_vehicle(props):
        tags["motor_vehicle"] = "no"
    
    return tags
    
def feature_to_osm(feature):
    """Converts a single GeoJSON feature to OSM-compatible form"""
    feature["properties"] = properties_to_osm(feature["properties"])
    return feature

if __name__ == "__main__":
    for line in sys.stdin:
        feature = json.loads(line)
        try:
            result = feature_to_osm(feature)
        except Exception as e:
            print(feature["properties"])
            raise e
            
        print(json.dumps(result))

