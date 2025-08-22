#!/usr/bin/env python3
"""simplify-ni: apply a set network aggregation algorithms to a base roadmap of Northern Ireland"""
"""Copyright (C) 2025 Will Deakin"""

import os
from collections import defaultdict

import geopandas as gp
import networkx as nx
import numpy as np
import pandas as pd
from momepy import close_gaps, remove_false_nodes
from neatnet import neatify
from parenx import get_primal, skeletonize_frame, voronoi_frame
from parenx.shared import get_source_target

CRS = "EPSG:27700"
pd.set_option("display.max_columns", None)


def get_component(gf):
    """get_component:"""
    r = gf.copy()
    nx_network = nx.from_pandas_edgelist(r, edge_attr="length", edge_key="edge")
    print(f"components: {nx.number_connected_components(nx_network)}")
    r["cluster"] = -1
    for n, c in enumerate(nx.connected_components(nx_network)):
        s = nx_network.subgraph(c).copy()
        ix = nx.to_pandas_edgelist(s)
        ix = np.sort(ix[["source", "target"]].values, axis=1)
        ix = pd.MultiIndex.from_arrays(ix.T)
        r.loc[ix, "cluster"] = n
        print(f"{str(n).zfill(3)}\t{len(ix):>4}", end="\t")
    print()
    return r


def get_edge(gf):
    """get_edge: get edge model from GeoPandas geometry"""
    r, _ = get_source_target(gf)
    r["length"] = r.length
    ix = np.sort(r[["source", "target"]].values)
    r = r.set_index(pd.MultiIndex.from_arrays(ix.T))
    return r


def close_gap(gf, gap=5.0):
    """close_gap:"""
    print(f"close gap {gap}")
    r = gf.copy()
    group = r.groupby("cluster").groups
    for k, v in group.items():
        print(k, end=" ")
        r.loc[v, "geometry"] = close_gaps(r.loc[v, "geometry"], gap).values
    print()
    return r


def set_base(gf):
    """set_base:"""
    print("base")
    r = gf.copy()
    group = r.groupby("cluster").groups
    for k, v in group.items():
        print(k, end=" ")
        s = r.loc[v]
        s["geometry"] = s.simplify(1.0)
        s.to_file(f"output/base-{str(k).zfill(2)}.gpkg", layer="base")
    print()


def set_skeltonize(gf):
    """skeltonize:"""
    print("skeltonize")
    r = gf.copy()
    group = r.groupby("cluster").groups
    parameter = {
        "simplify": 0.0,
        "buffer": 8.0,
        "scale": 1.0,
        "knot": False,
        "segment": False,
    }
    for k, v in group.items():
        print(k, end=" ")
        s = skeletonize_frame(r.loc[v, "geometry"], parameter)
        s["geometry"] = s.simplify(1.0)
        s = remove_false_nodes(s)
        s.to_file(f"output/skeltonize-{str(k).zfill(2)}.gpkg", layer="skeltonize")
        try:
            s = get_primal(s["geometry"])
            s.to_file(f"output/primal-{str(k).zfill(2)}.gpkg", layer="primal")
        except ValueError:
            pass
    print()


def set_netify(gf):
    """neatify:"""
    print("neatify")
    r = gf.copy()
    group = r.groupby("cluster").groups
    for k, v in group.items():
        print(k, end=" ")
        try:
            s = neatify(r.loc[v]).fillna("")
            s.to_file(f"output/neatnet-{str(k).zfill(2)}.gpkg", layer="neatnet")
        except KeyError:
            pass
    print()


def set_voronoid(gf):
    """set_voronoid:"""
    print("voronoid")
    r = gf.copy()
    group = r.groupby("cluster").groups
    parameter = {"simplify": 0.0, "scale": 5.0, "buffer": 8.0, "tolerance": 1.0}
    for k, v in group.items():
        print(k, end=" ")
        try:
            s = voronoi_frame(r.loc[v, "geometry"], parameter)
            s = r.to_frame("geometry")
            s["geometry"] = r.simplify(1.0)
            s = remove_false_nodes(r)
            s.to_file(f"output/voronoi-{str(k).zfill(2)}.gpkg", layer="voronoi")
        except AttributeError:
            pass
    print()


def output_ni_file():
    """output_ni_file:"""
    data = defaultdict(list)
    for dirpath, _, filelist in os.walk("output"):
        for filename in sorted(filelist):
            filestub = filename.replace(".gpkg", "")
            layer, cluster = filestub.split("-")
            r = gp.read_file(f"{dirpath}/{filename}", layer=layer)
            if r.empty:
                continue
            r["length"] = r.length
            r["cluster"] = cluster
            r = r.fillna("")
            data[layer].append(r)
    for k, v in data.items():
        r = pd.concat(v)
        r.to_file(f"ni-{k}.gpkg", layer=k)


def main():
    """main: execution function"""
    layer = "route_network_fastest"
    network = gp.read_file(f"data/{layer}.gpkg", layer=layer)
    network = network.to_crs(CRS)
    nx_model = remove_false_nodes(network["geometry"])
    edge = get_edge(nx_model)
    nx_model = remove_false_nodes(edge["geometry"])
    edge = get_edge(nx_model)
    edge = get_component(edge)

    nx_model = close_gap(edge)
    nx_model = remove_false_nodes(nx_model["geometry"])
    edge = get_edge(nx_model)
    edge = get_component(edge)

    set_base(edge)
    set_skeltonize(edge)
    set_netify(edge)
    set_voronoid(edge)

    output_ni_file()

if __name__ == "__main__":
    main()
