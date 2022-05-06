from setuptools import setup, find_packages

setup(
    name='cwtvla',
    version='0.1.1',
    description='ChipWhisperer Test Vector Leakage Assessment Library',
    author='Alex Dewar',
    author_email='adewar@newae.com',
    license='GPLv2+',
    packages=['cwtvla'],
    install_requires=[
        'scipy',
        'numpy',
        'zarr',
        'tqdm'
        #cw not really necessary, but cw convenience functions obviously require CW to be installed
        #'chipwhisperer' 
    ]
)
