import sys
from setuptools import setup, find_packages


required_packages = ['Flask>=0.10,<0.11', 'SQLAlchemy>=1.0',
                     'btctxstore', 'file_encryptor']
if sys.version_info.major == 2:
    required_packages.insert(0, 'mock')


setup(
    include_package_data=True,
    name='metacore',
    version='1.0',
    packages=find_packages(),
    install_requires=required_packages,
    test_suite='metacore.tests',
    entry_points={
        'console_scripts':
            ['metacore = metacore.storj:main']
    }
)
