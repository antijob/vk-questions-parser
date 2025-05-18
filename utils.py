import os
import pandas as pd


def save_to_csv(data, filename):
    directory = os.path.dirname(filename)
    if directory:
        os.makedirs(directory, exist_ok=True)

    df = pd.DataFrame([item.__dict__ for item in data])
    # Замена NaN на "null" при сохранении
    df.to_csv(filename, index=False, encoding="utf-8", na_rep="null")
