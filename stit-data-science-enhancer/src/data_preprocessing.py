from pandas import read_csv, DataFrame
from sklearn.model_selection import train_test_split

def load_data(file_path: str) -> DataFrame:
    """Load data from a CSV file."""
    data = read_csv(file_path)
    return data

def clean_data(data: DataFrame) -> DataFrame:
    """Clean the data by handling missing values and duplicates."""
    data = data.drop_duplicates()
    data = data.fillna(method='ffill')  # Forward fill for missing values
    return data

def split_data(data: DataFrame, target_column: str, test_size: float = 0.2) -> tuple:
    """Split the data into training and testing sets."""
    X = data.drop(columns=[target_column])
    y = data[target_column]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
    return X_train, X_test, y_train, y_test