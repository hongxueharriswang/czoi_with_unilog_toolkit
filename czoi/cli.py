import argparse
from . import __version__
def main():
    parser = argparse.ArgumentParser(prog='czoi', description='CZOI Toolkit CLI')
    parser.add_argument('-v', '--version', action='store_true', help='Show version')
    args = parser.parse_args()
    if args.version:
        print(__version__)
    else:
        parser.print_help()
