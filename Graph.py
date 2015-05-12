#!/usr/bin/env python

import numpy
import SOM
import scipy.spatial.distance
import itertools


class Graph:
    def __init__(self, adjacency_matrix=None, smap=None):
        self.adjacency_matrix = adjacency_matrix
        self.smap = smap
        self.is_complex = False
        self.metric = lambda u, v: scipy.spatial.distance.euclidean(u, v)
        if self.smap != None:
            if self.smap[0, 0].dtype == numpy.asarray(numpy.complex(1, 1)).dtype:
                self.is_complex = True
                print "Complex numbers space"
                self.metric = lambda u, v: numpy.sqrt(( numpy.abs(u - v) ** 2 ).sum())  # metric for complex numbers
        if self.adjacency_matrix is None:
            self.get_adjacency_matrix()

    def get_adjacency_matrix(self):
        """

        return the adjacency matrix for the given SOM map (self.smap)
        """
        nx, ny, nz = self.smap.shape
        adjacency_matrix = numpy.ones((nx * ny, nx * ny)) * numpy.inf
        for i in range(nx):
            for j in range(ny):
                ravel_index = numpy.ravel_multi_index((i, j), (nx, ny))
                neighbor_indices = self.neighbor_dim2_toric((i, j), (nx, ny))
                for neighbor_index in neighbor_indices:
                    ravel_index_2 = numpy.ravel_multi_index(neighbor_index, (nx, ny))
                    distance = self.metric(self.smap[i, j], self.smap[neighbor_index])
                    adjacency_matrix[ravel_index, ravel_index_2] = distance
        self.adjacency_matrix = adjacency_matrix

    def neighbor_dim2_toric(self, p, s):
        """Efficient toric neighborhood function for 2D SOM.
        """
        x, y = p
        X, Y = s
        xm = (x - 1) % X
        ym = (y - 1) % Y
        xp = (x + 1) % X
        yp = (y + 1) % Y
        return [(xm, ym), (xm, y), (xm, yp), (x, ym), (x, yp), (xp, ym), (xp, y), (xp, yp)]

    def add_edge(self, graph, n1, n2, w):
        try:
            graph[n1].update({n2: w})
        except KeyError:
            graph[n1] = {n2: w}
        try:
            graph[n2].update({n1: w})
        except KeyError:
            graph[n2] = {n1: w}

    def get_graph(self, adjacency_matrix = None):
        graph = {}
        if adjacency_matrix is None:
            adjacency_matrix = self.adjacency_matrix
        assert isinstance(adjacency_matrix, numpy.ndarray)
        nx, ny = adjacency_matrix.shape
        for index in itertools.combinations(range(nx), 2):
            (i, j) = index
            weight = adjacency_matrix[i, j]
            if weight != numpy.inf:
                self.add_edge(graph, i, j, weight)
        return graph

    def make_sets(self):
        self.sets = []
        for v in range(len(self.adjacency_matrix)):
            self.sets.append({v})

    def find_set(self, u):
        for index, s in enumerate(self.sets):
            if u in s:
                break
        return index

    def union(self, index_set1, index_set2):
        indices = [index_set1, index_set2]
        indices.sort(reverse=True)
        sets = []
        for index in indices:
            sets.append(self.sets.pop(index))
        self.sets.append(sets[0].union(sets[1]))

    @property
    def minimum_spanning_tree(self):
        """
        Kruskal's algorithm
        """
        self.make_sets()
        minimum_spanning_tree = numpy.ones(self.adjacency_matrix.shape) * numpy.inf
        sorter = self.adjacency_matrix.flatten().argsort()
        nx, ny = self.adjacency_matrix.shape
        sorter = sorter[self.adjacency_matrix.flatten()[sorter] != numpy.inf]
        for i in sorter:
            (u, v) = numpy.unravel_index(i, (nx, ny))
            index_set1 = self.find_set(u)
            index_set2 = self.find_set(v)
            if index_set1 != index_set2:
                self.union(index_set1, index_set2)
                minimum_spanning_tree[u,v] = self.adjacency_matrix[u,v]
                minimum_spanning_tree[v,u] = self.adjacency_matrix[u,v]
        return minimum_spanning_tree

    def write_GML(self, outfilename, graph = None, directed_graph = False, **kwargs):
        """
        Write gml file for ugraph.

        - isomap_layout: embed isomap coordinates of the 2D embedded space in the gml output file

        **kwargs: data to write for each node.  Typically, these data are
        obtained from the self.project function. The keys of the kwargs are
        used as keys in the GML file
        """
        if graph is None:
            ms_tree = self.minimum_spanning_tree
            graph = self.get_graph(ms_tree)
        outfile = open(outfilename, 'w')
        outfile.write('graph [\n')
        if directed_graph:
            outfile.write('directed 1\n')
        else:
            outfile.write('directed 0\n')
        nodes = graph.keys()
        for n in nodes:
            outfile.write('node [ id %d\n'%n)
            for key in kwargs.keys():
                try:
                    outfile.write('%s %.4f\n'%(key, kwargs[key][n]))
                except KeyError:
                    print "no %s for node %d"%(key, n)
                    pass
            outfile.write(']\n')
        for n1 in graph.keys():
            for n2 in graph[n1].keys():
                d = graph[n1][n2]
                outfile.write('edge [ source %d target %d weight %.4f\n'%(n1, n2, d))
                outfile.write(']\n')
        outfile.write(']')
        outfile.close()
