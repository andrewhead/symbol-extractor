import logging
import os
import os.path
import tarfile
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("symbol-extractor-client")


Path = str


class ServerConnectionException(Exception):
    pass


@dataclass
class Location:
    left: int
    top: int
    width: int
    height: int
    page: int


SymbolId = int


@dataclass
class Symbol:
    id_: SymbolId
    mathml: str
    tex: str
    location: Location
    parent: Optional["Symbol"]


def extract_symbols(
    sources_dir: Path, host: str = "http://127.0.0.1", port: int = 8001,
) -> List[Symbol]:

    with tempfile.TemporaryDirectory() as temp_dir:
        # Prepare a gzipped tarball file containing the sources.
        archive_filename = os.path.join(temp_dir, "archive.tgz")
        with tarfile.open(archive_filename, "w:gz") as archive:
            archive.add(sources_dir, arcname=os.path.sep)

        # Prepare query parameters.
        with open(archive_filename, "rb") as archive_file:
            files = {"sources": ("archive.tgz", archive_file, "multipart/form-data")}

            # Make request to service.
            endpoint = f"{host}:{port}/"
            try:
                response = requests.post(endpoint, files=files)
            except requests.exceptions.RequestException as e:
                raise ServerConnectionException(
                    f"Request to server {endpoint} failed.", e
                )

    # Get result
    data = response.json()

    # Create symbols from JSON.
    symbols: Dict[SymbolId, Symbol] = {}
    parents: Dict[SymbolId, SymbolId] = {}
    for item in data:
        symbol = Symbol(
            id_=item["id"],
            mathml=item["mathml"],
            tex=item["tex"],
            location=Location(
                item["location"]["left"],
                item["location"]["top"],
                item["location"]["width"],
                item["location"]["height"],
                item["location"]["page"],
            ),
            parent=None,
        )
        symbols[symbol.id_] = symbol
        parents[symbol.id_] = item["parent"]

    # Resolve parents of symbols.
    for id_, symbol in symbols.items():
        if parents[id_]:
            symbol.parent = symbols[parents[id_]]

    return [s for s in symbols.values()]
