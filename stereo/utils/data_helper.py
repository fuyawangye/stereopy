#!/usr/bin/env python3
# coding: utf-8
"""
@author: Ping Qiu  qiuping1@genomics.cn
@last modified by: Ping Qiu
@file: data_helper.py
@time: 2021/3/14 16:11
"""
from scipy.sparse import issparse
import pandas as pd
import numpy as np


def select_group(st_data, groups, cluster):
    all_groups = set(cluster['group'].values)
    groups = [groups] if isinstance(groups, str) else groups
    for g in groups:
        if g not in all_groups:
            raise ValueError(f"cluster {g} is not in all cluster.")
    # cluster = cluster.set_index(['bins'])
    # st_data.cells['cluster'] = cluster['cluster']
    # print(andata.obs)
    group_index = cluster['group'].isin(groups)
    exp_matrix = st_data.exp_matrix.toarray() if issparse(st_data.exp_matrix) else st_data.exp_matrix
    group_sub = exp_matrix[group_index, :]
    obs = st_data.cell_names[group_index]
    return pd.DataFrame(group_sub, index=obs, columns=list(st_data.gene_names))


def get_cluster_res(adata, data_key='clustering'):
    cluster_data = adata.uns[data_key].cluster
    cluster = cluster_data['cluster'].astype(str).astype('category').values
    return cluster


def get_position_array(data, obs_key='spatial'):
    return np.array(data.obsm[obs_key])[:, 0: 2]


# def select_group(andata, groups, clust_key):
#     if clust_key not in andata.obs_keys():
#         raise ValueError(f" '{clust_key}' is not in andata.")
#     all_groups = set(andata.obs[clust_key].values)
#     groups = [groups] if isinstance(groups, str) else groups
#     for g in groups:
#         if g not in all_groups:
#             raise ValueError(f"cluster {g} is not in all cluster.")
#     group_index = andata.obs[clust_key].isin(groups)
#     exp_matrix = andata.X.toarray() if issparse(andata.X) else andata.X
#     group_sub = exp_matrix[group_index, :]
#     obs = andata.obs_names[group_index]
#     return pd.DataFrame(group_sub, index=obs, columns=list(andata.var_names))

