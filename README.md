Python scripts to convert USFS road and trail data to an OSM-compatible schema.

Status:
- **Roads**: mostly feature complete
- **Trails**: WIP; incomplete support for snow trails, motorized trails, and seasonal access restrictions

## Data sources

You can download the required datasets from the [FS Data Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php). The specific datasets are "National Forest System Roads" (`S_USA.RoadCore`) and "National Forest System Trails" (`S_USA.TrailNFS_Publish`). You should download them in Geodatabase format (Shapefiles won't work with these scripts since the column names are truncated).

## Running

The `justfile` in this repo can be used to run the conversion using the [`just`](https://github.com/casey/just) command runner. Or you can just paste the same series of commands into your shell.

The input files are assumed to be in `~/Downloads`; edit the script to change this path if required.

The code requires a fairly recent version of Python (3.9+ I think?).

## Documentation

The conversion applied by this tool is based on the interpretation of the USFS data described on the [US Forest Service Data](https://wiki.openstreetmap.org/wiki/US_Forest_Service_Data) page on the OSM wiki.

## License

This code is available under the ISC license. See the LICENSE file for details.
