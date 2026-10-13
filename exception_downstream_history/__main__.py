from exception_study_support.runner import main as study_main

from . import analysis, core


def main(argv=None):
    """Run the shared CLI, including the installed console entry point."""
    return study_main(core, analysis, argv)


if __name__ == '__main__':
    raise SystemExit(main())
