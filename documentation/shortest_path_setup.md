### Setup Guide for Jupyter Notebook to calculate Shortest Path
- Pre-requisites:
    - Python 3.7

- The Jupyter Notebook was created using [Anaconda](https://www.anaconda.com/distribution/) for Windows
- After the installation of Anaconda create a new virtual environment by using the following command in an Anaconda Terminal:
    ```
    conda create -n yourenvname python=3.7 anaconda
    ```
- To activate the new environment use the following command:
    ```
    activate yourenvname
    ```
- After the activation of the environment follow the installation instructions on the [course website](https://automating-gis-processes.github.io/2017/course-info/Installing_Anacondas_GIS.html) of the University of Helsinki to install all relevant packages regarding Geoinformation Systems.

- After testing the installation of the packages, install the `mlrose` package ([additional information](https://mlrose.readthedocs.io/en/stable/source/intro.html)) to calculate the shortest path between several bins by using the following command:
    ```
    pip install mlrose
    ```
- Now the [Jupyter Notebook](code/bin_routing/moers_bins.ipynb) can be executed.