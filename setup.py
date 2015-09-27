from setuptools import setup, find_packages

setup(
    name='hq-worker',
    version='2.0.0.dev1',
    url='https://github.com/herqles-io/hq-worker',
    include_package_data=True,
    license='',
    author='Ryan Belgrave',
    author_email='rbelgrave@covermymeds.com',
    description='Herqles Worker',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=[
        'hq-lib==2.0.0.dev1',
        'pika==0.9.14',
        'pyyaml==3.11',
        'schematics==1.1.0'
    ],
    scripts=['bin/hq-worker']
)
