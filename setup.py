from setuptools import setup, find_namespace_packages


requirments_package = [
    'PySide6',
]

setup(
    name="gui_ex",
    version="0.0.1",
    description="",
    url="https://github.com/SEOULTECH-AIS-gyounghun6612/pyqt5_ex_module.git",
    author="Choi_keonghun & Jun_eins",
    author_email="dev.gyounghun6612@gmail.com",
    packages=find_namespace_packages(),
    zip_safe=False,
    python_requires=">= 3.7.0",
    install_requires=[
        "python_ex",
    ]
)
