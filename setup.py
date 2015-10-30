from setuptools import setup, find_packages

setup(
    name='hq-worker',
    version='1.0.1',
    url='',
    include_package_data=True,
    license='',
    author='Ryan Belgrave',
    author_email='rbelgrave@covermymeds.com',
    description='Herqles Worker',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=[
        'hq-lib==1.0.0',
        'pika==0.9.14',
        'pyyaml==3.11',
        'schematics==1.0.4'
    ],
    dependency_links=[
        'git+https://github.com/herqles-io/hq-lib.git#egg=hq-lib-1.0.0',
    ],
    scripts=['bin/hq-worker']
)
