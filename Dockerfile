FROM mambaorg/micromamba:0.20.0

COPY --chown=micromamba:micromamba env.yaml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# For debugging without Nextflow
COPY bin/* /usr/local/bin/

USER root
