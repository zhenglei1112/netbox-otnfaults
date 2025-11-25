from setuptools import find_packages, setup

setup(
    name='netbox-otnfaults',
    version='0.1',
    description='A NetBox plugin for OTN fault registration',
    install_requires=[],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.8',
    classifiers=[
        'Framework :: Django',
        'Programming Language :: Python :: 3',
    ],
