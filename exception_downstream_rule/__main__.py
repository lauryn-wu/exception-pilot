from exception_study_support.runner import main as study_main

from . import analysis, core


def main(argv=None):
    """Run the frozen study through the shared execution and resume CLI."""
    return study_main(core, analysis, argv)


if __name__ == '__main__':
    raise SystemExit(main())
