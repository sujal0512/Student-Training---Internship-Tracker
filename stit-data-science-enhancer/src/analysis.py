from scipy import stats
import pandas as pd

def perform_statistical_tests(data, group_col, value_col):
    groups = data.groupby(group_col)[value_col].apply(list)
    return stats.f_oneway(*groups)

def summarize_data(data):
    summary = {
        'mean': data.mean(),
        'median': data.median(),
        'std_dev': data.std(),
        'min': data.min(),
        'max': data.max(),
        'count': data.count()
    }
    return pd.DataFrame(summary)