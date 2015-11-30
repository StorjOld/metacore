from setuptools import setup, find_packages

setup(
    include_package_data = True,
    name='metacore',
    version='1.0',

    packages=find_packages(),

    install_requires=[
        'mock',git 
        'Flask>=0.10,<0.11',
        'SQLAlchemy>=1.0',
        'btctxstore',
        'file_encryptor',
    ],
    test_suite='metacore.tests',
    entry_points={
        'console_scripts':
            ['metacore = metacore.storj:main']
    }
)
