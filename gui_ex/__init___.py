if __package__ == "":
    # if this module call to local for another project
    import sys
    from os import path

    # add file dir
    if path.dirname(path.abspath(__file__)) not in sys.path:
        sys.path.append(path.dirname(path.abspath(__file__)))