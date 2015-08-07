import argparse
import hqworker

description = """Some description here"""

epilog = """Some epilog here"""

parser = argparse.ArgumentParser(
    description=description,
    epilog=epilog)

parser.add_argument('-c', '--config', required=True, help='Config file to use')
parser.set_defaults(func=hqworker.main)
args = parser.parse_args()
