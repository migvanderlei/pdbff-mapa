#!/usr/bin/env python3
"""Study-area map for the PDBFF / ARIE methods slide.

Ranch polygons come from OpenDataBio-INPA (drawn on the Venticinque &
Fernandes 1998 PDBFF base map). Sample points are read from data/sites.csv
(WGS 84, decimal degrees). The file ships with a header only: the 14
igarapé coordinates are not in the presentation, and this script does not
invent them.
"""

from __future__ import annotations

import json
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from shapely import wkt
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

FAZENDA_EDGE = {
    "Fazenda Dimona": "#f4d35e",
    "Fazenda Esteio": "#f4a261",
    "Fazenda Porto Alegre": "#e9c46a",
}
MATRIZ_COLOR = {
    "floresta_continua": "#d8f3dc",
    "fragmento": "#95d5b2",
    "capoeira": "#52b788",
    "pasto": "#f4a261",
}


def load_fazendas() -> gpd.GeoDataFrame:
    raw = json.loads((DATA / "fazendas_wkt.json").read_text())
    rows = []
    for feat in raw:
        geom = wkt.loads(feat["wkt"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        rows.append({"nome": feat["properties"]["nome"], "geometry": geom})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def load_sites() -> gpd.GeoDataFrame | None:
    path = DATA / "sites.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, comment="#")
    df = df.dropna(subset=["lon", "lat"])
    if df.empty:
        return None
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326",
    )


def scale_bar(ax, length_m: float, location: tuple[float, float], label: str) -> None:
    """Draw a scale bar in Web Mercator metres (true scale is ~1:1 at 2°S)."""
    x0, y0 = location
    ax.plot([x0, x0 + length_m], [y0, y0], color="white", lw=3.2, solid_capstyle="butt", zorder=6)
    ax.plot([x0, x0 + length_m], [y0, y0], color="black", lw=1.2, solid_capstyle="butt", zorder=7)
    for x in (x0, x0 + length_m):
        ax.plot([x, x], [y0 - 250, y0 + 250], color="black", lw=1.0, zorder=7)
    ax.text(
        x0 + length_m / 2,
        y0 + 700,
        label,
        ha="center",
        va="bottom",
        fontsize=8,
        color="white",
        zorder=7,
        path_effects=halo(),
    )


def halo():
    from matplotlib import patheffects

    return [patheffects.withStroke(linewidth=3, foreground="black")]


def north_arrow(ax, x: float, y: float) -> None:
    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - 4500),
        ha="center",
        va="center",
        fontsize=9,
        color="white",
        fontweight="bold",
        arrowprops=dict(arrowstyle="-|>", color="white", lw=1.2),
        zorder=7,
        path_effects=halo(),
    )


def main() -> None:
    states = gpd.read_file(DATA / "br_states.geojson").to_crs(3857)
    faz = load_fazendas().to_crs(3857)
    sites = load_sites()
    if sites is not None:
        sites = sites.to_crs(3857)

    amazonas = states[states["name"] == "Amazonas"]
    # Pad the three ranches so Dimona (west) and Esteio (east) both fit.
    minx, miny, maxx, maxy = faz.total_bounds
    pad_x = (maxx - minx) * 0.08
    pad_y = (maxy - miny) * 0.12
    extent = (minx - pad_x, maxx + pad_x, miny - pad_y, maxy + pad_y)

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.linewidth": 0.4,
    })
    fig = plt.figure(figsize=(13.4, 7.15), facecolor="white")
    ax = fig.add_axes([0.30, 0.10, 0.67, 0.82])
    axin = fig.add_axes([0.025, 0.16, 0.26, 0.70])

    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    cx.add_basemap(
        ax,
        source=cx.providers.Esri.WorldImagery,
        zoom=12,
        attribution=False,
    )
    faz.plot(ax=ax, facecolor="none", edgecolor="#ffe66d", linewidth=1.6, zorder=4)

    centroids = faz.copy()
    centroids["geometry"] = faz.geometry.representative_point()
    for _, row in centroids.iterrows():
        short = row["nome"].replace("Fazenda ", "")
        ax.annotate(
            short,
            xy=(row.geometry.x, row.geometry.y),
            ha="center",
            va="center",
            fontsize=9,
            color="white",
            fontweight="bold",
            zorder=5,
            path_effects=halo(),
        )

    if sites is not None:
        for matriz, group in sites.groupby(sites["matriz"].fillna("não informada")):
            color = MATRIZ_COLOR.get(str(matriz), "#ff006e")
            group.plot(ax=ax, color=color, markersize=28, edgecolor="black", linewidth=0.4, zorder=6)
        handles = [
            Line2D([0], [0], marker="o", color="none", markerfacecolor=c, markeredgecolor="black",
                   markersize=7, label=name.replace("_", " "))
            for name, c in MATRIZ_COLOR.items()
            if name in set(sites["matriz"].dropna())
        ]
        if handles:
            leg = ax.legend(handles=handles, title="Matriz", loc="lower right", frameon=True, fontsize=8)
            leg.get_frame().set_alpha(0.9)

    # 10 km scale bar, lower left of the imagery.
    scale_bar(ax, 10_000, (extent[0] + 2500, extent[2] + 3500), "10 km")
    north_arrow(ax, extent[1] - 6000, extent[3] - 2500)
    ax.set_axis_off()

    # Locator: Amazonas only, so the ~80 km between Manaus and the reserve is visible.
    amazonas.plot(ax=axin, color="#d7e4d4", edgecolor="#4d4d4d", linewidth=0.5)
    am_bounds = amazonas.total_bounds
    axin.set_xlim(am_bounds[0], am_bounds[2])
    axin.set_ylim(am_bounds[1], am_bounds[3])
    box_ll = gpd.GeoSeries([box(*faz.to_crs(4326).total_bounds)], crs=4326).to_crs(3857)
    box_ll.boundary.plot(ax=axin, color="#9b2226", linewidth=1.0)
    manaus = gpd.GeoSeries(gpd.points_from_xy([-60.0217], [-3.1190]), crs=4326).to_crs(3857)
    manaus.plot(ax=axin, color="#9b2226", markersize=16, zorder=5)
    mx, my = float(manaus.iloc[0].x), float(manaus.iloc[0].y)
    axin.annotate(
        "Manaus",
        xy=(mx, my),
        xytext=(0, -11),
        textcoords="offset points",
        ha="center",
        fontsize=7,
        color="#333333",
    )
    bx = box_ll.iloc[0]
    axin.annotate(
        "PDBFF",
        xy=(bx.centroid.x, bx.centroid.y),
        xytext=(10, 8),
        textcoords="offset points",
        fontsize=7,
        color="#9b2226",
    )
    axin.set_axis_off()
    axin.set_title("Amazonas", fontsize=9, color="#333333", pad=2)

    fig.text(
        0.30, 0.955,
        "Área de estudo — ARIE PDBFF",
        fontsize=14, fontweight="bold", color="#1d1d1d", ha="left",
    )
    fig.text(
        0.30, 0.915,
        "Fazendas Dimona, Esteio e Porto Alegre  ·  cerca de 80 km ao norte de Manaus, BR-174",
        fontsize=8.5, color="#444444", ha="left",
    )
    fig.text(
        0.30, 0.028,
        "Polígonos das fazendas: OpenDataBio-INPA, traçados sobre o mapa-base do PDBFF "
        "(Venticinque e Fernandes, 1998).  Imagem: Esri World Imagery.  Datum WGS 84.",
        fontsize=6.5, color="#555555", ha="left", va="bottom",
    )

    png = OUT / "area_de_estudo.png"
    pdf = OUT / "area_de_estudo.pdf"
    fig.savefig(png, dpi=220)
    fig.savefig(pdf)
    plt.close(fig)
    print(png)
    print(pdf)


if __name__ == "__main__":
    main()
