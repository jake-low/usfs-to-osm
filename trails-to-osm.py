"""
Reads USDA National Forest System Trails ('S_USA.TrailNFS') data newline-
delimited GeoJSON features from STDIN, converts attributes to OSM-compatible tags, and
writes the resulting GeoJSON features to STDOUT.
"""

import json
import re
import sys

ABBREVIATIONS = {
    "N": "North",
    "S": "South",
    "SO": "South",
    "E": "East",
    "W": "West",
    "MT": "Mount",
    "MTN": "Mountian",
    "NTL": "National",
    "NATL": "National",
    "CG": "Campground",
    "CK": "Creek",
    "CR": "Creek",
    "CRK": "Creek",
    "CYN": "Canyon",
    "FK": "Fork",
    "I.T.": "Interpretive Trail", # include only I.T., not IT (the word 'it')
    "LK": "Lake",
    "LKS": "Lakes",
    "PK": "Park",
    "RD": "Road",
    "ST": "Saint",
    "TR": "Trail",
    "SMT": "Snowmobile Trail",
    "HWT": "Hunter Walking Trail",
    "NRT": "National Recreation Trail",
    "NST": "National Scenic Trail",

    # specific long distance trail names
    "PCT": "Pacific Crest Trail",
    "PCNST": "Pacific Crest National Scenic Trail",
    "CDT": "Continental Divide Trail",
    "GWT": "Great Western Trail",
    "INHT": "Iditarod National Historic Trail",
    "TRT": "Tahoe Rim Trail",
    "FNST": "Florida National Scenic Trail",
    "LSHT": "Lone Star Hiking Trail",
    "MCCT": "Michigan Cross-Country Cycle Trail",
    "MCCCT": "Michigan Cross-Country Cycle Trail",
}

SPECIAL_CASES = {
    "ATV": "ATV",
    "OHV": "OHV",
    "XC": "XC",
    "OF": "of",
    "THE": "the",
    "IN": "in",
    "TO": "to",
}

BAD_WORDS = {
    # "Filler" words to delete from names
    "FDR",
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

BAD_NAME_PATTERNS = {
    '^NFST-[[:digit:]]+'
}

def squeeze(string):
    """Replace any runs of whitespace in string with a single space"""
    return " ".join(string.split())

def tokenize(string):
    return re.findall(r'\s|[\w\'.]+|[^\w\'.]+', string)

# ALLOWED_TERRA_USE values
HIKER_PEDESTRIAN = 1
PACK_AND_SADDLE = 2
BICYCLE = 3
MOTORCYCLE = 4
ATV = 5
FOUR_WHEEL_DRIVE_GT_50 = 6

def allowed_terra_use(props):
    val = props.get("ALLOWED_TERRA_USE")
    if val and val.isnumeric():
        return [int(digit) for digit in val]
    else:
        return None
    

def highway(props):
    if props.get("TRAIL_TYPE") == "TERRA":
        allowed = allowed_terra_use(props)
        if allowed != None and (ATV in allowed or FOUR_WHEEL_DRIVE_GT_50 in allowed):
            return "track"
        else:
            return "path"
    else:
        return None


def name(props):
    name = props["TRAIL_NAME"]
    id = props["TRAIL_NO"]
    
    if not name or id in name or name in BAD_NAMES:
        return None

    if any(re.match(regex, name) for regex in BAD_NAME_PATTERNS):
        return None

    name = squeeze(name.replace("/", " / ")).strip()

    if name.isnumeric():
        return None

    words = []
    for token in tokenize(name):
        if token.isspace() or re.match('^[()-/]$', token):
            words.append(token)
            continue

        word = token.upper()
        if word in BAD_WORDS:
            continue

        if word == "-":
            words.append(word)
            continue

        abbr = ABBREVIATIONS.get(word) or ABBREVIATIONS.get(word.replace(".", ""))
        if abbr:
            word = abbr
        elif word in SPECIAL_CASES:
            word = SPECIAL_CASES[word]
        elif re.match('[\w\']+', word):
            word = word.capitalize()
        
        words.append(word)

    if not words:
        return None

    if not any(val in words for val in ["Road", "Trail", "Connector", "Tie", "Loop", "Spur"]):
        words += [" ", "Trail"]

    if words[0].islower():
        words[0] = words[0].capitalize()
    if words[-1].islower():
        words[-1] = words[-1].capitalize()

    return "".join(words)

def ref(props):
    ref = props["TRAIL_NO"]

    if ref.startswith("T"):
        ref = ref[1:]
    if ref.startswith("O-"):
        ref = ref[2:]
    
    return ref

ACCESS_TAG_TO_COLUMN_MAP = {
    "foot": "HIKER_PEDESTRIAN",
    "horse": "PACK_SADDLE",
    "bicycle": "BICYCLE",
}

def access_tags_for_mode(mode, props):
    # TODO: this ignores ALLOWED_TERRA_USE - is that okay?
    prefix = ACCESS_TAG_TO_COLUMN_MAP[mode]
    managed = props.get(prefix + "_MANAGED")
    accepted_or_discouraged = props.get(prefix + "_ACCPT_DISC")
    restricted = props.get(prefix + "_RESTRICTED")

    tags = {}

    if managed == "01/01-12/31":
        # allowed all year
        tags[mode] = "designated"
        return tags
    elif accepted_or_discouraged == "01/01-12/31":
        tags[mode] = "yes"
        return tags
    elif restricted == "01/01-12/31":
        tags[mode] = "no"
        return tags

    # TODO: conditional restrictions
    return tags
    

def access_tags(props):
    tags = {}

    tags |= access_tags_for_mode("foot", props)
    tags |= access_tags_for_mode("bicycle", props)
    tags |= access_tags_for_mode("horse", props)

    return tags


def operator(props):
    return "US Forest Service"


def properties_to_osm(props):
    """Converts a feature properties dict to OSM tags"""
    tags = {}
    # tags = {**props}
    tags["TRAIL_NAME"] = props["TRAIL_NAME"]
    tags["TRAIL_NO"] = props["TRAIL_NO"]

    tags["highway"] = highway(props)
    tags["name"] = name(props)
    tags["ref"] = ref(props)
    tags["operator"] = operator(props)

    tags |= access_tags(props)
  
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
