#!/usr/bin/env python3
# coding: utf-8
"""
@author: Yiran Wu  wuyiran@genomics.cn
@last modified by: Yiran Wu
@file:neighbors.py
@time:2021/09/07
"""
from ..log_manager import logger
import numpy as np
import pandas as pd
from types import MappingProxyType
from typing import Optional, Type, Mapping, Any, Union
from natsort import natsorted
from scipy.sparse import spmatrix
from packaging import version
from sklearn.utils import check_random_state
from numpy import random
AnyRandom = Union[None, int, random.RandomState]
from typing_extensions import Literal

try:
    from louvain.VertexPartition import MutableVertexPartition
except ImportError:

    class MutableVertexPartition:
        pass

    MutableVertexPartition.__module__ = 'louvain.VertexPartition'


def louvain(
    neighbor,
    resolution: float = None,
    random_state: AnyRandom = 0,
    adjacency=None,
    flavor: Literal['vtraag', 'igraph', 'rapids'] = 'vtraag',
    directed: bool = True,
    use_weights: bool = False,
    partition_type: Optional[Type[MutableVertexPartition]] = None,
    partition_kwargs: Mapping[str, Any] = MappingProxyType({}),
):

    partition_kwargs = dict(partition_kwargs)

    if (flavor != 'vtraag') and (partition_type is not None):
        raise ValueError(
            '`partition_type` is only a valid argument ' 'when `flavour` is "vtraag"'
        )

    if flavor in {'vtraag', 'igraph'}:
        if directed and flavor == 'igraph':
            directed = False
        g = neighbor.get_igraph_from_adjacency(adjacency, directed=directed)
        if use_weights:
            weights = np.array(g.es["weight"]).astype(np.float64)
        else:
            weights = None
        if flavor == 'vtraag':
            import louvain
            if partition_type is None:
                partition_type = louvain.RBConfigurationVertexPartition
            if resolution is not None:
                partition_kwargs["resolution_parameter"] = resolution
            if use_weights:
                partition_kwargs["weights"] = weights
            if version.parse(louvain.__version__) < version.parse("0.7.0"):
                louvain.set_rng_seed(random_state)
            else:
                partition_kwargs["seed"] = random_state
            logger.info('    using the "louvain" package of Traag (2017)')
            part = louvain.find_partition(
                g,
                partition_type,
                **partition_kwargs,
            )
        else:
            part = g.community_multilevel(weights=weights)
        groups = np.array(part.membership)
    elif flavor == 'rapids':
        # nvLouvain only works with undirected graphs,
        # and `adjacency` must have a directed edge in both directions
        import cudf
        import cugraph

        offsets = cudf.Series(adjacency.indptr)
        indices = cudf.Series(adjacency.indices)
        if use_weights:
            sources, targets = adjacency.nonzero()
            weights = adjacency[sources, targets]
            if isinstance(weights, np.matrix):
                weights = weights.A1
            weights = cudf.Series(weights)
        else:
            weights = None
        g = cugraph.Graph()

        if hasattr(g, 'add_adj_list'):
            g.add_adj_list(offsets, indices, weights)
        else:
            g.from_cudf_adjlist(offsets, indices, weights)

        # logg.info('    using the "louvain" package of rapids')
        louvain_parts, _ = cugraph.louvain(g)
        groups = (
            louvain_parts.to_pandas()
            .sort_values('vertex')[['partition']]
            .to_numpy()
            .ravel()
        )
    elif flavor == 'taynaud':
        # this is deprecated
        import networkx as nx
        import community

        g = nx.Graph(adjacency)
        partition = community.best_partition(g)
        groups = np.zeros(len(partition), dtype=int)
        for k, v in partition.items():
            groups[k] = v
    else:
        raise ValueError('`flavor` needs to be "vtraag" or "igraph" or "taynaud".')

    cluster = pd.Categorical(
        values=groups.astype('U'),
        categories=natsorted(map(str, np.unique(groups))),
    )

    return cluster
