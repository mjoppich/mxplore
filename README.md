# mxplore

Micro-RNAs (miRNAs) are potent disease modulators due to their distinct interactions
with specific genes in diseases and cell types. Most of these interactions are
post-transcriptional regulations: miRNAs bind to the mRNA of genes and induce their
degradation, thereby reducing the gene expression of target genes.
While there are many databases listing miRNA-gene interactions, retrieved from
computational predictions or imputed from specific high-throughput data, most
confirmation low-throughput experiments are published in text form. Hence, retrieving
experimentally verified miRNA-gene interactions from literature, abstracts or full-texts
is an extremely important and useful task for assessing the actual miRNA-gene
interaction landscape.
To derive the mx-plore database, a newly developed text mining strategy combining
dependency graph analysis and rule-based systems has been used. Identified
interactions are stored in a database along the terms that describe the context of the
miRNA-gene interaction in the respective document. Our mx-plore platform makes such
identified miRNA-gene interactions accessible and searchable on various levels, such as
by cell type, disease or involved processes. The platform is available at
[https://rest.bio.ifi.lmu.de/mxplore](https://rest.bio.ifi.lmu.de/mxplore) and corresponding source code is deposited
on GitHub.

If you want to run parts of the pipeline yourself, check the [commands.md](https://github.com/mjoppich/mxplore/blob/main/commands.md).

## Platform

![screenshot of mxplore platform](./mxplore/img/mxplore_platform_snapshot.png)