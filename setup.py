from setuptools import setup, find_packages

setup(
    name='cwtvla',
    version='0.1.0',
    description='ChipWhisperer Test Vector Leakage Assessment Library',
    author='Alex Dewar',
    author_email='adewar@newae.com',
    license='GPLv2+',
    packages=find_packages("cwtvla"),
    install_requires=[
        'scipy',
        'numpy',
        #cw not really necessary, but cw convenience functions obviously require CW to be installed
        #'chipwhisperer' 
    ]
)
