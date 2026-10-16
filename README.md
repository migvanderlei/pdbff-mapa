# PDBFF study-area map

Map for the methods slide of the Gymnotiformes project at the ARIE Projeto Dinâmica Biológica de Fragmentos Florestais (PDBFF), north of Manaus.

The figure shows Amazonas with Manaus and the reserve, and satellite imagery of the ranches Dimona, Porto Alegre, and Esteio.

Ranch outlines are from [OpenDataBio-INPA](https://opendb.inpa.gov.br/), traced on the PDBFF base map of Venticinque and Fernandes (1998). They are the farm boundaries, not the legal ARIE polygon. Imagery is Esri World Imagery. The state outline is the public Brazil-states GeoJSON used by Click That Hood.

## Rebuild

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build_map.py
```

Output: `output/area_de_estudo.png` and `output/area_de_estudo.pdf`.

## Add the 14 igarapés

Edit `data/sites.csv`. Coordinates are WGS 84 decimal degrees (longitude west of Greenwich is negative). `matriz` is one of `floresta_continua`, `fragmento`, `capoeira`, `pasto`.

```text
id,fazenda,matriz,anos,lon,lat
IG01,Dimona,floresta_continua,2013;2023;2025,-60.10,-2.34
```

Then run `build_map.py` again. Points are drawn only from this file.
