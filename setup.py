from setuptools import setup, find_packages

setup(
    name='cwtvla',
    version='0.0.1',
    description='ChipWhisperer Test Vector Leakage Assessment Library',
    author='Alex Dewar',
    author_email='adewar@newae.com',
    license='GPLv3',
    packages=find_packages("cwtvla"),
    install_requires=[
        'scipy',
        'chipwhisperer' #need this right now, but not too hard to decouple+make optional
    ]
)
