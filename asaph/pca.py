"""
Copyright 2017 Ronald J. Nowling

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
from itertools import tee, izip
import os
import sys

import matplotlib
matplotlib.use("PDF")
import matplotlib.pyplot as plt
import numpy as np
import seaborn

from asaph.ml import PCA
from asaph.newioutils import read_features
from asaph.newioutils import deserialize
from asaph.newioutils import PROJECT_SUMMARY_FLNAME

from sklearn.preprocessing import binarize

def explained_variance_analysis(args):
    workdir = args.workdir

    figures_dir = os.path.join(workdir, "figures")
    if not os.path.exists(figures_dir):
        os.makedirs(figures_dir)

    features = read_features(workdir)

    pca = PCA(args.n_components)
    explained_variance_ratios = pca.explained_variance(features.feature_matrix)

    fig_flname = os.path.join(figures_dir,
                              "pca_explained_variance_ratios.png")

    plt.clf()
    plt.grid(True)
    plt.plot(explained_variance_ratios, "m.-")
    plt.xlabel("Principal Component", fontsize=16)
    plt.ylabel("Explained Variance Ratio", fontsize=16)
    plt.ylim([0., 1.])
    plt.savefig(fig_flname,
                DPI=300)

def min_components_explained_variance(args):
    workdir = args.workdir

    features = read_features(workdir)

    n_components = args.init_n_components
    while True:
        print "Computing PCA with %s components" % n_components
        pca = PCA(n_components)
        explained_variance_ratios = pca.explained_variance(features.feature_matrix)
        sorted_ratios = np.sort(explained_variance_ratios)[::-1]
        cum_ratios = np.cumsum(sorted_ratios)
        total_explained_variance = cum_ratios[-1]
        if total_explained_variance >= args.explained_variance_threshold:
            break
        n_components *= 2

    needed_components = 0
    achieved_ev_ratio = 0.0
    for i, ev_ratio in enumerate(cum_ratios):
        if ev_ratio >= args.explained_variance_threshold:
            needed_components = i + 1
            achieved_ev_ratio = ev_ratio
            break

    print "Explained-variance threshold of %s surpassed at %s with %s components" % \
        (args.explained_variance_threshold,
         achieved_ev_ratio,
         needed_components)

def pairwise(iterable):
    iterable = iter(iterable)
    try:
        while True:
            a = next(iterable)
            b = next(iterable)
            yield a, b
    except StopIteration:
        pass
    
def plot_projections(args):
    if len(args.pairs) % 2 != 0:
        print "Error: PCs must be provided in pairs of 2"
        sys.exit(1)

    workdir = args.workdir

    figures_dir = os.path.join(workdir, "figures")
    if not os.path.exists(figures_dir):
        os.makedirs(figures_dir)
    
    features = read_features(workdir)
    project_summary = deserialize(os.path.join(workdir,
                                               PROJECT_SUMMARY_FLNAME))
    
    pca = PCA(args.n_components)
    projected = pca.transform(features.feature_matrix)

    all_labels = set(features.class_labels)
    labels = np.array(features.class_labels, dtype=np.int32)
    populations = []
    for l in all_labels:
        pop = labels == l
        pop_name = project_summary.population_names[l]
        populations.append((pop, pop_name))

    for p1, p2 in pairwise(args.pairs):
        fig_flname = os.path.join(figures_dir,
                                  "pca_projection_%s_%s.png" % (str(p1), str(p2)))
        plt.clf()
        plt.grid(True)
        colors = ["m", "c", "k", "r", "g", "b"]
        markers = ["o"] * len(colors) + \
                  ["s"] * len(colors) + \
                  ["+"] * len(colors)
        for idx, (pop_idx, pop_name) in enumerate(populations):
            plt.scatter(projected[pop_idx, p1],
                        projected[pop_idx, p2],
                        color=colors[idx % len(colors)],
                        marker=markers[idx % len(markers)],
                        edgecolor="k",
                        alpha=0.7,
                        label=pop_name)
        plt.xlabel("Principal Component %s" % p1, fontsize=16)
        plt.ylabel("Principal Component %s" % p2, fontsize=16)
        plt.legend()
        plt.savefig(fig_flname,
                    DPI=300)

def output_coordinates(args):
    workdir = args.workdir

    features = read_features(workdir)
    project_summary = deserialize(os.path.join(workdir,
                                               PROJECT_SUMMARY_FLNAME))


    pca = PCA(args.n_components)
    projected = pca.transform(features.feature_matrix)
    selected = projected[:, args.selected_components]

    with open(args.output_fl, "w") as fl:
        headers = ["sample", "population_index", "population_name"]
        headers.extend(map(str, args.selected_components))
        fl.write("\t".join(headers))
        fl.write("\n")

        for i in xrange(len(features.sample_labels)):
            sample = features.sample_labels[i]
            pop_idx = features.class_labels[i]
            pop_name = project_summary.population_names[pop_idx]
            line = [sample, str(pop_idx), pop_name]
            line.extend(map(str, selected[i, :]))
            fl.write("\t".join(line))
            fl.write("\n")


def analyze_weights(args):
    workdir = args.workdir

    figures_dir = os.path.join(workdir, "figures")
    if not os.path.exists(figures_dir):
        os.makedirs(figures_dir)
    
    features = read_features(workdir)
    project_summary = deserialize(os.path.join(workdir,
                                               PROJECT_SUMMARY_FLNAME))
    
    pca = PCA(args.n_components)
    projected = pca.transform(features.feature_matrix)

    for i, w in enumerate(args.weights):
        plt.clf()
        seaborn.distplot(w * pca.components_[i, :],
                         kde=False)
        plt.xlabel("Feature Weights", fontsize=16)
        plt.ylabel("Count(Features)", fontsize=16)
        plot_fl = os.path.join(figures_dir,
                               "pca_feature_weights_pc%s.png" % i)
        plt.savefig(plot_fl,
                    DPI=300)

def extract_genotypes(args):
    workdir = args.workdir

    analysis_dir = os.path.join(workdir, "analysis")
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)

    features = read_features(workdir)
    project_summary = deserialize(os.path.join(workdir,
                                               PROJECT_SUMMARY_FLNAME))
    
    pca = PCA(args.n_components)
    projected = pca.transform(features.feature_matrix)

    binary_vectors = []
    for i, (w, t) in enumerate(zip(args.weights, args.thresholds)):
        scaled = w * pca.components_[i, :].reshape(1, -1)
        binary = binarize(scaled, threshold=t)[0, :]
        for j, other in enumerate(binary_vectors):
            dp = binary.dot(other)
            print "Dot product of vectors %s and %s: %s" % (i, j, dp)
        binary_vectors.append(binary)

    binary_features = np.array(binary_vectors)

    feature_genotypes = features.snp_feature_genotypes
    n_components = binary_features.shape[0]
    snp_component_gts = dict()
    for snp_label, feature_idx in features.snp_feature_map.iteritems():
            component_gts = []
            total_gts = 0
            for i in xrange(n_components):
                gts = []
                for idx in feature_idx:
                    if binary_features[i, idx] == 1.0:
                        gts.append(feature_genotypes[snp_label][idx])
                total_gts += len(gts)
                component_gts.append(gts)
                
            if total_gts > 0:
                snp_component_gts[snp_label] = component_gts

    output_fl = os.path.join(analysis_dir, "component_genotypes.tsv")
    with open(output_fl, "w") as fl:
        header = ["chrom", "pos"]
        for i in xrange(n_components):
            header.append("component_%s" % i)
        fl.write("\t".join(header))
        fl.write("\n")
        for (chrom, pos), component_gts in snp_component_gts.iteritems():
            fl.write(chrom)
            fl.write("\t")
            fl.write(pos)
            for gts in component_gts:
                fl.write("\t")
                fl.write(",".join(gts))
            fl.write("\n")
    
def parseargs():
    parser = argparse.ArgumentParser(description="Asaph - PCA")

    parser.add_argument("--workdir",
                        type=str,
                        required=True,
                        help="Work directory")

    subparsers = parser.add_subparsers(dest="mode")
    eva_parser = subparsers.add_parser("explained-variance-analysis",
                                       help="Compute explained variances of PCs")
    eva_parser.add_argument("--n-components",
                            type=int,
                            required=True,
                            help="Number of PCs to compute")

    output_parser = subparsers.add_parser("output-coordinates",
                                      help="Output PC projected coordinates")
    
    output_parser.add_argument("--n-components",
                               type=int,
                               required=True,
                               help="Number of PCs to compute")
    
    output_parser.add_argument("--selected-components",
                               type=int,
                               nargs="+",
                               help="Components to output")

    output_parser.add_argument("--output-fl",
                               type=str,
                               required=True,
                               help="Output file")
    
    plot_parser = subparsers.add_parser("plot-projections",
                                        help="Plot samples on principal coordinates")

    plot_parser.add_argument("--n-components",
                             type=int,
                             required=True,
                             help="Number of PCs to compute")

    plot_parser.add_argument("--pairs",
                             type=int,
                             nargs="+",
                             required=True,
                             help="Pairs of PCs to plot")

    count_parser = subparsers.add_parser("min-components-explained-variance",
                                         help="Find number of components to explain specified percentage of variance")

    count_parser.add_argument("--init-n-components",
                              type=int,
                              required=True,
                              help="Initial number of components to compute")

    count_parser.add_argument("--explained-variance-threshold",
                              type=float,
                              required=True,
                              help="Minimum explained variance")

    weight_analysis_parser = subparsers.add_parser("analyze-weights",
                                                   help="Plot component weight distributions")

    weight_analysis_parser.add_argument("--n-components",
                                        type=int,
                                        required=True,
                                        help="Number of PCs to compute")

    weight_analysis_parser.add_argument("--weights",
                                        type=float,
                                        nargs="+",
                                        required=True,
                                        help="Component weights")

    extract_genotypes_parser = subparsers.add_parser("extract-genotypes",
                                                     help="Extract genotypes from PCs")
    extract_genotypes_parser.add_argument("--n-components",
                                          type=int,
                                          required=True,
                                          help="Number of PCs to compute")
    
    extract_genotypes_parser.add_argument("--weights",
                                          type=float,
                                          nargs="+",
                                          required=True,
                                          help="Component scaling factors")

    extract_genotypes_parser.add_argument("--thresholds",
                                          type=float,
                                          nargs="+",
                                          required=True,
                                          help="Thresholds for binarizing")

    return parser.parse_args()

if __name__ == "__main__":
    args = parseargs()

    if args.mode == "explained-variance-analysis":
        explained_variance_analysis(args)
    elif args.mode == "plot-projections":
        plot_projections(args)
    elif args.mode == "output-coordinates":
        output_coordinates(args)
    elif args.mode == "min-components-explained-variance":
        min_components_explained_variance(args)
    elif args.mode == "analyze-weights":
        analyze_weights(args)
    elif args.mode == "extract-genotypes":
        extract_genotypes(args)
    else:
        print "Unknown mode '%s'" % args.mode
        sys.exit(1)
