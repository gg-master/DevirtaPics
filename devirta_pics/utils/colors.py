from matplotlib.colors import cnames, to_rgb


class Color:
    @classmethod
    def c(cls, cname):
        return tuple(map(lambda x: int(x * 255), to_rgb(cnames[cname])))
