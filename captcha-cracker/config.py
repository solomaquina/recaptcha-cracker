import os

config = {
    "captcha_test_url": "https://nocturnaltortoise.github.io/captcha",
    "labels_path": "captcha-dataset-labels.txt",
    "image_size": "93x93",
    "image_size_tuple": (93,93),
    "weights_path": "../weights/xception-less-data-weights.h5",
    "log_path": "./logs/xception-captcha-dataset",
    "dataset_path": os.path.join('E:\\', 'datasets', 'captcha-dataset'),
    "categories_path": "captcha-dataset-categories.txt",
    "num_classes": 71
}
