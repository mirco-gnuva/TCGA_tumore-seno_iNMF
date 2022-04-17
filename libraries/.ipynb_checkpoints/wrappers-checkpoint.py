import numpy as np
from sklearn.metrics import silhouette_score
from pandas import Series, DataFrame
from tqdm.notebook import tqdm
from .dataset_helper import DatasetHelper
from halo import HaloNotebook as Halo
import pandas
import pickle
import os
from sklearn.metrics.cluster import homogeneity_score


def get_silhouette(df, labels):
    silhouette = silhouette_score(df, labels)

    return silhouette


# Return a pandas index containing all patients
def get_patients(datasets: dict):
    first_df = list(datasets.values())[0]
    return first_df.index


# Counts decimals positions of the given number
def count_decimals(number) -> int:
    if isinstance(number, int):
        return 0

    string = str(number)

    if '.' in string:
        decimals = string.split('.')[1]
        return len(decimals)
    else:
        return int(string.split('e-')[1])


# Applies Min-Max normalization to the passed pandas Series
def min_max_norm(column: Series):
    col_min = min(column)
    col_max = max(column)

    col_range = col_max - col_min

    if col_range == 0:
        return column

    return column.apply(lambda x: (x - col_min) / col_range)


# Applies column-based Min-Max normalization to the passed pandas DataFrame
def df_min_max_norm(df: DataFrame) -> DataFrame:
    df_ = df.copy()
    for col_name in df_.columns:
        df_[col_name] = df_[col_name].apply(min_max_norm)

    return df_


def load_datasets(root: str, filenames: list, pd_library, show_bar: bool, leave_bar: bool = True) -> dict:
    datasets = {}

    helpers = [DatasetHelper(root, filename, pd_library) for filename in filenames]

    iterator = tqdm(helpers, leave=leave_bar) if show_bar else helpers

    helper: DatasetHelper
    for helper in iterator:
        if show_bar:
            iterator.set_description(f'Loading "{helper.name}" from "{helper.path}"')

        datasets[helper.name] = helper.dataset

        if show_bar:
            iterator.set_description(f'{helper.name} loaded.')

    return datasets


def load_labels(root: str, filename: str, log: bool) -> DataFrame:
    if log:
        spinner = Halo(text=f'Loading labels dataset...', spinner='dots')
        spinner.start()

    helper = DatasetHelper(root, filename, pandas)
    labels = helper.dataset

    if log:
        spinner.stop()
        print('Loaded')

    return labels


def load_PCAs(root: str, filename: str, log: bool) -> dict:
    path = os.path.join(root, filename)
    if log:
        spinner = Halo(text=f'Loading buffered PCAs...', spinner='dots')
        spinner.start()

    with open(path, 'rb') as file:
        buffer = pickle.load(file)

    if log:
        spinner.stop()
        print('Loaded.')

    return buffer


def result_filename(pipeline: str, datasets: dict) -> str:
    datasets_string = ','.join(datasets.keys())
    filename = f'{pipeline}_[{datasets_string}]'

    return filename


def results_subfolder(method: str, pipeline: str):
    return os.path.join(method, 'RAW', pipeline)


def concatenate(datasets: dict, library) -> DataFrame:
    return library.concat(datasets.values(), axis=1)


# Returns:
#  - method: "phase-phase..."
#  - method_param: "phase<param>-phase<param>..."
#  - description: "phase<param> -> phase<param>..."
def pipeline_str(pipeline: list):
    method = '-'.join(phase for phase, _ in pipeline)
    method_param = '-'.join(f'{phase}{str(param).replace(".", "")}' for phase, param in pipeline)
    description = ' -> '.join(f'{phase}{param}' for phase, param in pipeline)

    return method, method_param, description


def get_homogeneity(labels: np.ndarray, clusters: np.ndarray):
    return homogeneity_score(labels, clusters)


def get_clusters_homogeneity(labels: np.ndarray, clusters: np.ndarray):
    classes = np.unique(clusters)

    df = pandas.DataFrame(np.column_stack((labels, clusters)))

    scores = {}
    for cls in classes:
        sub_df = df[df['clusters'] == cls]

        scores[cls] = get_homogeneity(sub_df['labels'], sub_df['clusters'])

    return scores


def cluster_purity(values) -> float:
    classes = np.unique(values)

    abs_freqs = {cls: 0 for cls in classes}

    for value in values:
        abs_freqs[value] += 1

    diffs = [freq for freq in abs_freqs.values() if freq != max(abs_freqs.values())]

    if max(abs_freqs.values()) == 0 or len(classes) == 1:
        return 1
    if len(diffs) == 0:
        return 1 - 1 / len(classes)

    return 1 - sum(diffs) / sum(abs_freqs.values())


def clusters_purity(dataset: pandas.DataFrame, labels, clusters):
    df = dataset.copy()
    df['cluster'] = clusters
    df['label'] = labels

    classes = np.unique(clusters)

    scores = {cls: cluster_purity(df[df['cluster'] == cls]['label']) for cls in classes}

    return scores


