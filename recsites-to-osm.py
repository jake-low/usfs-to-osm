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
    "I.T.": "Interpretive Trail",  # include only I.T., not IT (the word 'it')
    "LK": "Lake",
    "LKS": "Lakes",
    "PK": "Park",
    "RD": "Road",
    "ST": "Saint",
    "TH": "Trailhead",
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
    "HUC",  # some roads near Rainier, meaning unknown
    "(FDR)",  # Forest Development Road
    "MRS",  # Minimum Road System
    "2B DECOMM'D",  # to be decommissioned
}

BAD_NAME_PATTERNS = {"^NFST-[[:digit:]]+"}


def squeeze(string):
    """Replace any runs of whitespace in string with a single space"""
    return " ".join(string.split())


def tokenize(string):
    return re.findall(r"\s|[A-Za-z\'.]+|[^A-Za-z\'.]+", string)


def name(props):
    name = props["RECAREANAME"]

    if not name or name in BAD_NAMES:
        return None

    if any(re.match(regex, name) for regex in BAD_NAME_PATTERNS):
        return None

    name = squeeze(name.replace("/", " / ")).strip()

    if name.isnumeric():
        return None

    words = []
    for token in tokenize(name):
        if token.isspace() or re.match("^[()-/]$", token):
            words.append(token)
            continue

        if re.match("^#\d+$", token):
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
        elif re.match("[\w']+", word):
            word = word.capitalize()

        words.append(word)

    if not words:
        return None

    if not "Trailhead" in words:
        words += [" ", "Trailhead"]

    if words[0].islower():
        words[0] = words[0].capitalize()
    if words[-1].islower():
        words[-1] = words[-1].capitalize()

    return "".join(words)


def website(props):
    return props.get("RECAREAURL")


def reservation_website(props):
    # TODO parse https://www.recreation.gov/camping/campgrounds/[[:digit:]]+ URLs out of FEEDESCRIPTION field
    return None


def trailhead_to_osm(props):
    tags = {}

    tags["highway"] = "trailhead"
    # tags["RECAREANAME"] = props["RECAREANAME"]
    tags["name"] = name(props)
    tags["website"] = website(props)

    return tags


def properties_to_osm(props):
    """Converts a feature properties dict to OSM tags"""
    tags = None

    match props.get("MARKERACTIVITY"):
        case "Trailhead":
            tags = trailhead_to_osm(props)
        case "Viewing Scenery":
            # TODO: tourism=viewpoint
            pass
        case (
            "Campground Camping"
            | "Group Camping"
            | "Dispersed Camping"
        ):  # or OHV Camping or Horse Camping or ...
            # TODO: tourism=camp_site
            pass
        case "Picnicking":
            # TODO: tourism=picnic_site
            pass
        case "Visitor Centers":
            # TODO: tourism=information + information=visitor_centre ... or amenity=ranger_station?
            pass

    if tags:
        tags["operator"] = "US Forest Service"

    return tags


def feature_to_osm(feature):
    """Converts a single GeoJSON feature to OSM-compatible form"""
    if tags := properties_to_osm(feature["properties"]):
        feature["properties"] = tags
        return feature
    else:
        return None


if __name__ == "__main__":
    for line in sys.stdin:
        feature = json.loads(line)
        try:
            result = feature_to_osm(feature)
        except Exception as e:
            print(feature["properties"])
            raise e

        if result:
            print(json.dumps(result))
